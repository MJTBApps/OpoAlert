package es.opoalert.app

import android.animation.ValueAnimator
import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.pdf.PdfRenderer
import android.os.Handler
import android.os.Looper
import android.util.LruCache
import android.view.GestureDetector
import android.view.MotionEvent
import android.view.ScaleGestureDetector
import android.view.View
import android.view.animation.DecelerateInterpolator
import android.widget.OverScroller
import java.util.concurrent.ExecutorService

/**
 * Documento PDF con zoom continuo como el de una foto: pellizcar amplía desde el
 * punto entre los dedos, se desplaza en cualquier dirección (con inercia) y el
 * doble toque amplía o vuelve al ancho de la pantalla.
 *
 * Dos capas: cada página se dibuja una vez al ancho de la pantalla (capa base) y,
 * al soltar el zoom, la zona visible se vuelve a dibujar a la resolución exacta
 * para que el texto se vea nítido. `PdfRenderer` solo admite una página abierta a
 * la vez, así que todo se dibuja en un único hilo (`worker`).
 */
@SuppressLint("ViewConstructor")
class PdfDocumentView(
    context: Context,
    private val pdf: PdfRenderer,
    private val ratios: List<Float>,
    private val worker: ExecutorService,
    private var startPage: Int,
) : View(context) {
    companion object {
        const val MAX_SCALE = 5f
        private const val DOUBLE_TAP_SCALE = 2.5f
        private const val MAX_BASE_WIDTH = 1400
    }

    var onPageChanged: ((page: Int, total: Int) -> Unit)? = null

    @Volatile var closed = false
    private val main = Handler(Looper.getMainLooper())
    private val density = resources.displayMetrics.density
    private val gap = 8 * density
    private val side = 6 * density

    // Transformación: pantalla = contenido * scale + (tx, ty).
    private var scale = 1f
    private var tx = 0f
    private var ty = 0f

    private var tops = FloatArray(0)
    private var pageWidth = 0f
    private var contentHeight = 0f
    private var currentPage = -1

    private val base = object : LruCache<Int, Bitmap>((Runtime.getRuntime().maxMemory() / 4).toInt()) {
        override fun sizeOf(key: Int, value: Bitmap) = value.byteCount
    }
    private val pendingBase = HashSet<Int>()
    private var baseWidth = 0
    @Volatile private var nearFirst = 0
    @Volatile private var nearLast = 0

    /** Trozo nítido de una página, colocado en coordenadas del contenido. */
    private class Detail(val bitmap: Bitmap, val rect: RectF)
    private var details: List<Detail> = emptyList()
    private var detailGeneration = 0
    private val detailTask = Runnable { renderDetails() }

    private val pagePaint = Paint().apply { color = Color.WHITE }
    private val bitmapPaint = Paint(Paint.FILTER_BITMAP_FLAG or Paint.ANTI_ALIAS_FLAG)
    private val scroller = OverScroller(context)
    private var flinging = false
    private var zoomAnimator: ValueAnimator? = null

    private val scaleDetector = ScaleGestureDetector(context, object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
        override fun onScale(detector: ScaleGestureDetector): Boolean {
            zoomAt(scale * detector.scaleFactor, detector.focusX, detector.focusY)
            return true
        }
        override fun onScaleEnd(detector: ScaleGestureDetector) = scheduleDetails()
    })

    private val gestures = GestureDetector(context, object : GestureDetector.SimpleOnGestureListener() {
        override fun onDown(e: MotionEvent) = true
        override fun onScroll(e1: MotionEvent?, e2: MotionEvent, dx: Float, dy: Float): Boolean {
            tx -= dx
            ty -= dy
            clamp()
            invalidate()
            return true
        }
        override fun onFling(e1: MotionEvent?, e2: MotionEvent, vx: Float, vy: Float): Boolean {
            scroller.fling(tx.toInt(), ty.toInt(), vx.toInt(), vy.toInt(),
                minTx().toInt(), 0, minTy().toInt(), 0)
            flinging = true
            postInvalidateOnAnimation()
            return true
        }
        override fun onDoubleTap(e: MotionEvent): Boolean {
            animateZoom(if (scale < 1.6f) DOUBLE_TAP_SCALE else 1f, e.x, e.y)
            return true
        }
    })

    init {
        contentDescription = "Documento PDF"
        setBackgroundColor(Color.parseColor("#E9EEF5"))
    }

    /** Botones + y −: zoom animado desde el centro de la pantalla. */
    fun zoomBy(factor: Float) = animateZoom(scale * factor, width / 2f, height / 2f)

    fun release() {
        closed = true
        main.removeCallbacks(detailTask)
        zoomAnimator?.cancel()
        details = emptyList()
        base.evictAll()
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        if (w <= 0 || h <= 0) return
        pageWidth = w - 2 * side
        tops = FloatArray(ratios.size)
        var y = gap
        ratios.forEachIndexed { index, ratio ->
            tops[index] = y
            y += pageWidth * ratio + gap
        }
        contentHeight = y
        val newBaseWidth = pageWidth.toInt().coerceIn(1, MAX_BASE_WIDTH)
        if (newBaseWidth != baseWidth) {
            baseWidth = newBaseWidth
            base.evictAll()
        }
        details = emptyList()
        if (startPage > 1 && startPage <= tops.size) {
            ty = -(tops[startPage - 1] - gap) * scale
            startPage = 1
        }
        clamp()
        scheduleDetails()
    }

    private fun pageHeight(index: Int) = pageWidth * ratios[index]
    private fun minTx() = width - width * scale
    private fun minTy() = minOf(0f, height - contentHeight * scale)

    private fun clamp() {
        tx = tx.coerceIn(minTx(), 0f)
        ty = ty.coerceIn(minTy(), 0f)
    }

    private fun zoomAt(target: Float, fx: Float, fy: Float) {
        val next = target.coerceIn(1f, MAX_SCALE)
        tx = fx - (fx - tx) * next / scale
        ty = fy - (fy - ty) * next / scale
        scale = next
        clamp()
        invalidate()
    }

    private fun animateZoom(target: Float, fx: Float, fy: Float) {
        zoomAnimator?.cancel()
        scroller.forceFinished(true)
        val to = target.coerceIn(1f, MAX_SCALE)
        zoomAnimator = ValueAnimator.ofFloat(scale, to).apply {
            duration = 220
            interpolator = DecelerateInterpolator()
            addUpdateListener { zoomAt(it.animatedValue as Float, fx, fy) }
            addListener(object : android.animation.AnimatorListenerAdapter() {
                override fun onAnimationEnd(animation: android.animation.Animator) = scheduleDetails()
            })
            start()
        }
    }

    @SuppressLint("ClickableViewAccessibility")
    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (event.actionMasked == MotionEvent.ACTION_DOWN) {
            scroller.forceFinished(true)
            flinging = false
            zoomAnimator?.cancel()
            main.removeCallbacks(detailTask)
        }
        scaleDetector.onTouchEvent(event)
        if (!scaleDetector.isInProgress) gestures.onTouchEvent(event)
        if ((event.actionMasked == MotionEvent.ACTION_UP || event.actionMasked == MotionEvent.ACTION_CANCEL) && !flinging) {
            scheduleDetails()
        }
        return true
    }

    override fun computeScroll() {
        if (!flinging) return
        if (scroller.computeScrollOffset()) {
            tx = scroller.currX.toFloat()
            ty = scroller.currY.toFloat()
            clamp()
            postInvalidateOnAnimation()
        } else {
            flinging = false
            scheduleDetails()
        }
    }

    override fun onDraw(canvas: Canvas) {
        if (tops.isEmpty()) return
        val visibleTop = -ty / scale
        val visibleBottom = (height - ty) / scale
        canvas.save()
        canvas.translate(tx, ty)
        canvas.scale(scale, scale)
        var first = -1
        var last = -1
        for (index in tops.indices) {
            val top = tops[index]
            val bottom = top + pageHeight(index)
            if (bottom < visibleTop || top > visibleBottom) continue
            if (first < 0) first = index
            last = index
            val rect = RectF(side, top, side + pageWidth, bottom)
            canvas.drawRect(rect, pagePaint)
            val bitmap = base.get(index)
            if (bitmap != null) canvas.drawBitmap(bitmap, null, rect, bitmapPaint) else requestBase(index)
        }
        if (first >= 0) {
            nearFirst = (first - 1).coerceAtLeast(0)
            nearLast = (last + 1).coerceAtMost(tops.size - 1)
            // Se prepara la página anterior y la siguiente para que no aparezcan en blanco.
            if (base.get(nearFirst) == null) requestBase(nearFirst)
            if (base.get(nearLast) == null) requestBase(nearLast)
        }
        for (detail in details) canvas.drawBitmap(detail.bitmap, null, detail.rect, bitmapPaint)
        canvas.restore()
        reportPage()
    }

    private fun reportPage() {
        val center = (height / 2f - ty) / scale
        var page = 0
        while (page + 1 < tops.size && tops[page + 1] <= center) page++
        if (page != currentPage) {
            currentPage = page
            onPageChanged?.invoke(page + 1, tops.size)
        }
    }

    private fun requestBase(index: Int) {
        if (closed || !pendingBase.add(index)) return
        val width = baseWidth
        worker.execute {
            // Si ya no está cerca de la pantalla (desplazamiento rápido), no se dibuja.
            val bitmap = if (closed || index < nearFirst - 2 || index > nearLast + 2) null else try {
                pdf.openPage(index).use { page ->
                    val height = (width * page.height.toFloat() / page.width).toInt().coerceAtLeast(1)
                    Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888).also {
                        it.eraseColor(Color.WHITE)
                        page.render(it, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    }
                }
            } catch (_: Exception) {
                null
            }
            main.post {
                pendingBase.remove(index)
                if (bitmap != null && !closed && width == baseWidth) {
                    base.put(index, bitmap)
                    invalidate()
                }
            }
        }
    }

    private fun scheduleDetails() {
        main.removeCallbacks(detailTask)
        if (!closed) main.postDelayed(detailTask, 120)
    }

    /** Vuelve a dibujar, a la resolución exacta de la pantalla, la parte visible de cada página. */
    private fun renderDetails() {
        val generation = ++detailGeneration
        if (closed || tops.isEmpty() || width <= 0) return
        if (scale < 1.05f) {
            details = emptyList()
            invalidate()
            return
        }
        val view = RectF(0f, 0f, width.toFloat(), height.toFloat())
        val jobs = ArrayList<Triple<Int, RectF, Rect>>()
        for (index in tops.indices) {
            val onScreen = RectF(tx + side * scale, ty + tops[index] * scale,
                tx + (side + pageWidth) * scale, ty + (tops[index] + pageHeight(index)) * scale)
            val visible = RectF(onScreen)
            if (!visible.intersect(view)) continue
            val area = Rect(visible.left.toInt(), visible.top.toInt(),
                kotlin.math.ceil(visible.right).toInt(), kotlin.math.ceil(visible.bottom).toInt())
            if (area.width() > 0 && area.height() > 0) jobs.add(Triple(index, onScreen, area))
        }
        val atScale = scale
        val atTx = tx
        val atTy = ty
        worker.execute {
            val ready = ArrayList<Detail>()
            for ((index, onScreen, area) in jobs) {
                if (closed || generation != detailGeneration) return@execute
                try {
                    val bitmap = Bitmap.createBitmap(area.width(), area.height(), Bitmap.Config.ARGB_8888)
                    bitmap.eraseColor(Color.WHITE)
                    pdf.openPage(index).use { page ->
                        val k = onScreen.width() / page.width
                        val matrix = Matrix().apply {
                            setScale(k, k)
                            postTranslate(onScreen.left - area.left, onScreen.top - area.top)
                        }
                        page.render(bitmap, null, matrix, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    }
                    // De pantalla a contenido, con la transformación de cuando se pidió.
                    ready.add(Detail(bitmap, RectF((area.left - atTx) / atScale, (area.top - atTy) / atScale,
                        (area.right - atTx) / atScale, (area.bottom - atTy) / atScale)))
                } catch (_: Exception) {
                    return@execute
                }
            }
            main.post {
                if (!closed && generation == detailGeneration) {
                    details = ready
                    invalidate()
                }
            }
        }
    }
}
