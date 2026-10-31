package es.opoalert.app

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.ParcelFileDescriptor
import android.util.LruCache
import android.view.Gravity
import android.view.MotionEvent
import android.view.ScaleGestureDetector
import android.view.View
import android.view.ViewGroup
import android.widget.AbsListView
import android.widget.BaseAdapter
import android.widget.FrameLayout
import android.widget.HorizontalScrollView
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ListView
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

/**
 * Muestra el PDF oficial dentro de la app. Se descarga a la caché privada (no a
 * «Descargas») y se borra al salir. Si el enlace no es un PDF o no se puede leer,
 * se abre fuera como antes. El enlace ya llega verificado desde la ficha.
 */
class PdfViewerActivity : Activity() {
    companion object {
        const val EXTRA_URL = "es.opoalert.app.pdf_url"
        const val EXTRA_TITLE = "es.opoalert.app.pdf_title"
        private const val MAX_BYTES = 60L * 1024 * 1024
        private const val MAX_ZOOM = 4f

        fun open(context: Context, url: String, title: String) {
            context.startActivity(Intent(context, PdfViewerActivity::class.java)
                .putExtra(EXTRA_URL, url)
                .putExtra(EXTRA_TITLE, title))
        }

        /** «…/boletin.pdf#page=29»: página en la que empieza el anuncio (1 si no la indica). */
        fun startPage(url: String): Int =
            Regex("""#page=(\d{1,4})$""").find(url)?.groupValues?.get(1)?.toIntOrNull()?.coerceAtLeast(1) ?: 1

        fun looksLikePdf(head: ByteArray): Boolean =
            head.size >= 5 && String(head, 0, 5, Charsets.ISO_8859_1) == "%PDF-"
    }

    private val worker = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private lateinit var url: String
    private lateinit var file: File
    private lateinit var body: FrameLayout
    private lateinit var pageLabel: TextView
    private var renderer: PdfRenderer? = null
    private var descriptor: ParcelFileDescriptor? = null
    private var pageRatios: List<Float> = emptyList()
    private var list: ListView? = null
    private var zoom = 1f
    private var closed = false
    private val cache = object : LruCache<String, Bitmap>((Runtime.getRuntime().maxMemory() / 8).toInt()) {
        override fun sizeOf(key: String, value: Bitmap) = value.byteCount
    }
    private lateinit var scaleDetector: ScaleGestureDetector

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        url = intent.getStringExtra(EXTRA_URL).orEmpty()
        if (!url.startsWith("https://")) {
            finish()
            return
        }
        file = File(File(cacheDir, "pdf").apply { mkdirs() }, "anuncio.pdf")
        scaleDetector = ScaleGestureDetector(this, object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
            private var start = 1f
            override fun onScaleBegin(detector: ScaleGestureDetector): Boolean {
                start = zoom
                return true
            }
            override fun onScale(detector: ScaleGestureDetector): Boolean {
                start *= detector.scaleFactor
                return true
            }
            override fun onScaleEnd(detector: ScaleGestureDetector) = setZoom(start)
        })
        setContentView(createPage(intent.getStringExtra(EXTRA_TITLE).orEmpty()))
        showMessage("Cargando el PDF oficial…", loading = true)
        worker.execute { download() }
    }

    override fun onDestroy() {
        closed = true
        worker.execute {
            try { renderer?.close() } catch (_: Exception) {}
            try { descriptor?.close() } catch (_: Exception) {}
            file.delete()
        }
        worker.shutdown()
        cache.evictAll()
        super.onDestroy()
    }

    override fun dispatchTouchEvent(event: MotionEvent): Boolean {
        if (renderer != null) scaleDetector.onTouchEvent(event)
        return super.dispatchTouchEvent(event)
    }

    private fun createPage(title: String): LinearLayout {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#F8FAFD"))
        }
        val bar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(12), dp(6), dp(12), dp(6))
        }
        bar.addView(button("‹", 34f, "Volver a la ficha") { finish() }, LinearLayout.LayoutParams(dp(44), dp(44)))
        val heading = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(10), 0, dp(6), 0)
        }
        heading.addView(text(title.ifBlank { "Anuncio oficial" }, 14f, "#0E1C36", true).apply {
            maxLines = 1
            ellipsize = android.text.TextUtils.TruncateAt.END
        })
        pageLabel = text("PDF oficial", 11f, "#697C95")
        heading.addView(pageLabel)
        bar.addView(heading, LinearLayout.LayoutParams(0, -2, 1f))
        bar.addView(button("−", 24f, "Reducir") { setZoom(zoom / 1.5f) }, LinearLayout.LayoutParams(dp(40), dp(40)))
        bar.addView(button("+", 22f, "Ampliar") { setZoom(zoom * 1.5f) },
            LinearLayout.LayoutParams(dp(40), dp(40)).apply { marginStart = dp(6) })
        bar.addView(button("⇱", 20f, "Abrir en otra aplicación") { openOutside() },
            LinearLayout.LayoutParams(dp(40), dp(40)).apply { marginStart = dp(6) })
        root.addView(bar, LinearLayout.LayoutParams(-1, dp(60)))
        body = FrameLayout(this).apply { setBackgroundColor(Color.parseColor("#E9EEF5")) }
        root.addView(body, LinearLayout.LayoutParams(-1, 0, 1f))
        return root
    }

    private fun download() {
        try {
            var connection = URL(url.substringBefore('#')).openConnection() as HttpURLConnection
            connection.connectTimeout = 15_000
            connection.readTimeout = 30_000
            connection.setRequestProperty("User-Agent", "OpoAlert-Android/1.0")
            connection.instanceFollowRedirects = true
            try {
                if (connection.responseCode !in 200..299) throw IOException("HTTP " + connection.responseCode)
                // HttpURLConnection nunca pasa de https a http, pero comprobamos el destino final.
                if (connection.url.protocol != "https") throw IOException("Redirección no segura")
                connection.inputStream.use { input ->
                    file.outputStream().use { output ->
                        val buffer = ByteArray(64 * 1024)
                        var total = 0L
                        while (true) {
                            val read = input.read(buffer)
                            if (read < 0) break
                            total += read
                            if (total > MAX_BYTES || closed) throw IOException("PDF demasiado grande")
                            output.write(buffer, 0, read)
                        }
                    }
                }
            } finally {
                connection.disconnect()
            }
            val head = file.inputStream().use { input -> ByteArray(5).also { input.read(it) } }
            if (!looksLikePdf(head)) {
                main.post { if (!closed) { openOutside(); finish() } }
                return
            }
            val fd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
            val pdf = PdfRenderer(fd)
            val ratios = (0 until pdf.pageCount).map { index ->
                pdf.openPage(index).use { page -> page.height.toFloat() / page.width.coerceAtLeast(1) }
            }
            main.post {
                if (closed) {
                    worker.execute { pdf.close(); fd.close() }
                } else {
                    descriptor = fd
                    renderer = pdf
                    pageRatios = ratios
                    showPages()
                }
            }
        } catch (_: Exception) {
            file.delete()
            main.post {
                if (!closed) showMessage("No se ha podido cargar el PDF dentro de la app.", loading = false)
            }
        }
    }

    private fun showMessage(message: String, loading: Boolean) {
        body.removeAllViews()
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(dp(30), dp(30), dp(30), dp(30))
        }
        if (loading) box.addView(ProgressBar(this), LinearLayout.LayoutParams(dp(42), dp(42)))
        box.addView(text(message, 15f, "#35435C").apply {
            gravity = Gravity.CENTER
            setPadding(0, dp(14), 0, dp(16))
        })
        if (!loading) {
            box.addView(text("Abrir en el navegador", 15f, "#FFFFFF", true).apply {
                gravity = Gravity.CENTER
                background = rounded("#FE4559", 16)
                setPadding(dp(22), dp(14), dp(22), dp(14))
                setOnClickListener { openOutside() }
            })
        }
        body.addView(box, FrameLayout.LayoutParams(-1, -1))
    }

    private fun showPages() {
        val total = pageRatios.size
        val first = startPage(url).coerceAtMost(total)
        val pages = ListView(this).apply {
            divider = null
            dividerHeight = 0
            setBackgroundColor(Color.parseColor("#E9EEF5"))
            adapter = PageAdapter()
            setOnScrollListener(object : AbsListView.OnScrollListener {
                override fun onScrollStateChanged(view: AbsListView, state: Int) {}
                override fun onScroll(view: AbsListView, firstVisible: Int, visible: Int, count: Int) {
                    pageLabel.text = "Página " + (firstVisible + 1) + " de " + total
                }
            })
        }
        list = pages
        val horizontal = HorizontalScrollView(this).apply { isFillViewport = true }
        horizontal.addView(pages, FrameLayout.LayoutParams(pagesWidth(), -1))
        body.removeAllViews()
        body.addView(horizontal, FrameLayout.LayoutParams(-1, -1))
        pageLabel.text = "Página $first de $total"
        if (first > 1) pages.setSelection(first - 1)
    }

    private fun pagesWidth(): Int = (body.width.takeIf { it > 0 } ?: resources.displayMetrics.widthPixels).let {
        (it * zoom).toInt()
    }

    private fun setZoom(value: Float) {
        val next = value.coerceIn(1f, MAX_ZOOM)
        if (renderer == null || kotlin.math.abs(next - zoom) < 0.05f) return
        zoom = next
        val pages = list ?: return
        val position = pages.firstVisiblePosition
        pages.layoutParams = pages.layoutParams.apply { width = pagesWidth() }
        cache.evictAll()
        (pages.adapter as BaseAdapter).notifyDataSetChanged()
        pages.setSelection(position)
    }

    private inner class PageAdapter : BaseAdapter() {
        override fun getCount() = pageRatios.size
        override fun getItem(position: Int) = position
        override fun getItemId(position: Int) = position.toLong()

        override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
            // Cada página con un pequeño margen gris alrededor.
            val image = (convertView as? ImageView) ?: ImageView(this@PdfViewerActivity).apply {
                scaleType = ImageView.ScaleType.FIT_XY
                setPadding(dp(6), dp(5), dp(6), dp(5))
            }
            val width = pagesWidth() - dp(12)
            image.layoutParams = AbsListView.LayoutParams(-1, (width * pageRatios[position]).toInt() + dp(10))
            image.contentDescription = "Página " + (position + 1)
            val key = position.toString() + "@" + zoom
            image.tag = key
            val ready = cache.get(key)
            image.setImageBitmap(ready)
            if (ready == null) render(position, width, key, image)
            return image
        }
    }

    private fun render(position: Int, width: Int, key: String, target: ImageView) {
        // Más de 2.000 px de ancho no se nota en pantalla y gasta mucha memoria.
        val pixels = width.coerceAtMost(2000).coerceAtLeast(1)
        worker.execute {
            val pdf = renderer ?: return@execute
            if (closed || target.tag != key) return@execute
            val bitmap = try {
                pdf.openPage(position).use { page ->
                    Bitmap.createBitmap(pixels, (pixels * page.height.toFloat() / page.width).toInt().coerceAtLeast(1),
                        Bitmap.Config.ARGB_8888).also {
                        it.eraseColor(Color.WHITE)
                        page.render(it, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    }
                }
            } catch (_: Exception) {
                return@execute
            }
            main.post {
                if (closed) return@post
                cache.put(key, bitmap)
                if (target.tag == key) target.setImageBitmap(bitmap)
            }
        }
    }

    private fun openOutside() {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, "No hay aplicación para abrir la publicación.", Toast.LENGTH_LONG).show()
        }
    }

    private fun button(label: String, size: Float, description: String, click: () -> Unit): TextView =
        text(label, size, "#13294B").apply {
            gravity = Gravity.CENTER
            background = rounded("#FFFFFF", 22, "#E4EAF2")
            contentDescription = description
            isClickable = true
            isFocusable = true
            setOnClickListener { click() }
        }

    private fun text(s: String, size: Float, color: String, bold: Boolean = false): TextView =
        TextView(this).apply {
            text = s
            textSize = size
            includeFontPadding = false
            setTextColor(Color.parseColor(color))
            if (bold) typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
        }

    private fun rounded(fill: String, corner: Int, stroke: String? = null): GradientDrawable =
        GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            cornerRadius = dp(corner).toFloat()
            setColor(Color.parseColor(fill))
            if (stroke != null) setStroke(dp(1), Color.parseColor(stroke))
        }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density + 0.5f).toInt()
}
