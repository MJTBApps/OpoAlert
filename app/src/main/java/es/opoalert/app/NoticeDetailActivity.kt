package es.opoalert.app

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Bundle
import android.text.TextUtils
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import org.json.JSONObject

/**
 * Detalle nativo de las convocatorias. Los colores y tarjetas son visuales;
 * las cifras mostradas proceden del encabezado oficial, nunca de suposiciones.
 */
class NoticeDetailActivity : Activity() {
    companion object {
        const val EXTRA_NOTICE = "es.opoalert.app.notice_json"
    }

    private lateinit var notice: Notice
    private lateinit var topFavorite: TextView
    private lateinit var favoriteAction: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val raw = intent.getStringExtra(EXTRA_NOTICE)
        notice = try {
            require(!raw.isNullOrBlank())
            Notice.fromJson(JSONObject(raw))
        } catch (_: Exception) {
            Toast.makeText(this, "No se pudo abrir la convocatoria.", Toast.LENGTH_LONG).show()
            finish()
            return
        }
        setContentView(createPage())
        updateFavoriteState()
    }

    private fun createPage(): LinearLayout {
        val root = column().apply {
            setBackgroundColor(Color.parseColor("#F8FAFD"))
        }
        root.addView(topBar(), LinearLayout.LayoutParams(-1, dp(65)))
        val scroll = ScrollView(this).apply {
            isFillViewport = false
            clipToPadding = false
        }
        val content = column().apply {
            setPadding(dp(18), dp(8), dp(18), dp(25))
        }
        addHero(content)
        addMetrics(content)
        addSummary(content)
        addOfficialSource(content)
        addActions(content)
        scroll.addView(content)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        return root
    }

    private fun topBar(): LinearLayout {
        val bar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(16), dp(6), dp(16), dp(4))
        }
        val back = text("‹", 38f, "#13294B").apply {
            gravity = Gravity.CENTER
            background = rounded("#FFFFFF", 25, "#E4EAF2")
            contentDescription = "Volver al listado"
            isClickable = true
            isFocusable = true
            setOnClickListener { finish() }
        }
        bar.addView(back, LinearLayout.LayoutParams(dp(47), dp(47)))
        val brand = column().apply {
            gravity = Gravity.CENTER
        }
        brand.addView(text("OpoAlert", 21f, "#0E366C", true).apply {
            gravity = Gravity.CENTER
        })
        brand.addView(text("Empleo público a tu alcance", 10f, "#8390A4").apply {
            gravity = Gravity.CENTER
        })
        bar.addView(brand, LinearLayout.LayoutParams(0, -2, 1f))
        topFavorite = text("☆", 30f, "#147BD1").apply {
            gravity = Gravity.CENTER
            background = rounded("#FFFFFF", 24, "#E4EAF2")
            contentDescription = "Guardar o quitar de favoritas"
            isClickable = true
            isFocusable = true
            setOnClickListener { changeFavorite() }
        }
        bar.addView(topFavorite, LinearLayout.LayoutParams(dp(47), dp(47)))
        return bar
    }

    private fun addHero(content: LinearLayout) {
        val badgeRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(8), 0, dp(6))
        }
        val procedure = NoticeText.isProcedureUpdate(notice.title)
        val pool = notice.type.startsWith("Bolsa", true)
        val badgeLabel = when {
            procedure -> "TRÁMITE DEL PROCESO"
            pool -> "BOLSA DE TRABAJO"
            else -> "PLAZA / OPOSICIÓN"
        }
        val badgeColor = when {
            procedure -> "#B45309"
            pool -> "#0F766E"
            else -> "#1D4ED8"
        }
        val badgeBackground = when {
            procedure -> "#FEF3C7"
            pool -> "#DEF7EF"
            else -> "#E6EFFF"
        }
        badgeRow.addView(text(badgeLabel, 11f, badgeColor, true).apply {
            setPadding(dp(11), dp(7), dp(11), dp(7))
            background = rounded(badgeBackground, 10)
        })
        val group = NoticeDetails.groupInTitle(notice.title)
        if (group != null) {
            badgeRow.addView(text("Grupo " + group, 11f, "#28517E", true).apply {
                setPadding(dp(9), dp(7), dp(9), dp(7))
                background = rounded("#EDF3FB", 10)
            }, LinearLayout.LayoutParams(-2, -2).apply { marginStart = dp(8) })
        }
        content.addView(badgeRow)

        content.addView(text(NoticeText.headline(notice.title), 23f, "#0E1C36", true).apply {
            setLineSpacing(dp(3).toFloat(), 1.03f)
            setPadding(0, dp(3), 0, dp(8))
        })
        content.addView(text(notice.entity, 14f, "#5C6B80", true).apply {
            setLineSpacing(dp(2).toFloat(), 1f)
        })
        content.addView(text("⌖  " + notice.province + "     •     " + notice.date, 12f, "#697C95").apply {
            setPadding(0, dp(8), 0, dp(16))
        })
    }

    private fun addMetrics(content: LinearLayout) {
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        val explicitPlaces = NoticeDetails.placesInTitle(notice.title)
        row.addView(metric("♟  PLAZAS", explicitPlaces?.toString() ?: "Ver bases",
            "#FFF0E5", "#EA771D", "#13223C"),
            LinearLayout.LayoutParams(0, dp(108), 1f).apply { marginEnd = dp(10) })
        row.addView(metric("▦  PLAZO", NoticeDetails.deadlineLabel(),
            "#E4F8EC", "#199B58", "#13223C"),
            LinearLayout.LayoutParams(0, dp(108), 1f))
        content.addView(row)
        content.addView(text(
            "Plazas y plazos: consulta siempre las bases y, en su caso, la publicación de apertura del plazo.",
            10.5f, "#758399"
        ).apply { setPadding(dp(2), dp(8), dp(1), dp(5)) })
    }

    private fun metric(label: String, value: String, bg: String, labelColor: String, valueColor: String): LinearLayout =
        column().apply {
            gravity = Gravity.CENTER_VERTICAL
            background = rounded(bg, 17)
            setPadding(dp(14), dp(13), dp(9), dp(12))
            addView(text(label, 11f, labelColor, true))
            addView(text(value, if (value.length > 10) 15f else 24f, valueColor, true).apply {
                setPadding(0, dp(8), 0, 0)
                maxLines = 2
                ellipsize = TextUtils.TruncateAt.END
            })
        }

    private fun addSummary(content: LinearLayout) {
        content.addView(text("Resumen del anuncio", 18f, "#11213D", true).apply {
            setPadding(0, dp(21), 0, dp(9))
        })
        // Reproducimos el texto oficial: no inventamos requisitos, plazos ni modalidades.
        val card = column().apply {
            background = rounded("#FFFFFF", 16, "#E9EEF6")
            setPadding(dp(15), dp(15), dp(15), dp(15))
        }
        card.addView(text(notice.title.trim(), 14f, "#35435C").apply {
            setLineSpacing(dp(4).toFloat(), 1.06f)
        })
        content.addView(card)
    }

    private fun addOfficialSource(content: LinearLayout) {
        content.addView(text("Datos de la publicación", 18f, "#11213D", true).apply {
            setPadding(0, dp(20), 0, dp(9))
        })
        val card = column().apply {
            background = rounded("#EEF3FA", 16)
            setPadding(dp(14), dp(12), dp(14), dp(13))
        }
        val province = when (notice.province) {
            "Valencia" -> "Boletín Oficial de la Provincia de Valencia"
            "Alicante" -> "Boletín Oficial de la Provincia de Alicante"
            "Castellón" -> "Boletín Oficial de la Provincia de Castellón"
            "España (BOE)" -> "Boletín Oficial del Estado (BOE)"
            "Madrid" -> "Boletín Oficial de la Comunidad de Madrid (BOCM)"
            "Castilla-La Mancha (DOCM)" -> "Diario Oficial de Castilla-La Mancha (DOCM)"
            "Albacete" -> "Boletín Oficial de la Provincia de Albacete"
            "Ciudad Real" -> "Boletín Oficial de la Provincia de Ciudad Real"
            "Cuenca" -> "Boletín Oficial de la Provincia de Cuenca"
            "Guadalajara" -> "Boletín Oficial de la Provincia de Guadalajara"
            "Toledo" -> "Boletín Oficial de la Provincia de Toledo"
            "Huelva" -> "Boletín Oficial de la Provincia de Huelva"
            "Tarragona (BOP)" -> "Boletín Oficial de la Provincia de Tarragona"
            "Barcelona (BOP)" -> "Boletín Oficial de la Provincia de Barcelona"
            "Girona (BOP)" -> "Boletín Oficial de la Provincia de Girona"
            "Huesca" -> "Boletín Oficial de la Provincia de Huesca"
            "Teruel" -> "Boletín Oficial de la Provincia de Teruel"
            "Zaragoza" -> "Boletín Oficial de la Provincia de Zaragoza"
            "Almería" -> "Boletín Oficial de la Provincia de Almería"
            "Cádiz" -> "Boletín Oficial de la Provincia de Cádiz"
            "Barcelona", "Girona", "Lleida", "Tarragona" -> "CIDO · Diputació de Barcelona (procesos selectivos)"
            else -> "Boletín Oficial Provincial"
        }
        card.addView(text("▤  " + province, 13f, "#203856", true))
        val reference = if (notice.id.startsWith("CIDO"))
            "Actualización " + notice.date + "   ·   Ref. " + notice.id
        else if (notice.id.startsWith("BA-"))
            "BOP Barcelona · " + notice.date + "   ·   Registro " + notice.id
        else (when (notice.province) { Province.BOE.label -> "BOE n.º "; Province.MADRID.label -> "BOCM n.º "; Province.CLM_DOCM.label -> "DOCM n.º "; else -> "BOP n.º " }) +
            notice.bulletin + "   ·   Registro " + notice.id
        card.addView(text(reference, 11f, "#60748C").apply {
            setPadding(dp(2), dp(8), 0, 0)
        })
        content.addView(card)
    }

    private fun addActions(content: LinearLayout) {
        content.addView(action("↗   Compartir convocatoria", "#E2F1FF", "#0877C9") { share() },
            LinearLayout.LayoutParams(-1, dp(52)).apply { topMargin = dp(19) })
        favoriteAction = action("☆   Guardar en favoritas", "#FFF0E3", "#C96812") {
            changeFavorite()
        }
        content.addView(favoriteAction, LinearLayout.LayoutParams(-1, dp(52)).apply {
            topMargin = dp(9)
        })
        content.addView(action(when {
            notice.id.startsWith("CIDO") -> "▤   Ver convocatoria en CIDO"
            notice.province == "Teruel" -> "▤   Ver anuncio oficial"
            else -> "▤   Ver PDF oficial"
        }, "#FE4559", "#FFFFFF") { openOfficial() },
            LinearLayout.LayoutParams(-1, dp(54)).apply { topMargin = dp(9) })
        content.addView(text(
            "OpoAlert no es una aplicación oficial. Las bases, requisitos y plazos válidos son los publicados por la Administración competente.",
            10.5f, "#8190A5"
        ).apply { setPadding(dp(4), dp(14), dp(4), 0) })
    }

    private fun updateFavoriteState() {
        val saved = FavoritesStore.contains(this, notice.id)
        topFavorite.text = if (saved) "★" else "☆"
        favoriteAction.text = if (saved) "★   Quitar de favoritas" else "☆   Guardar en favoritas"
    }

    private fun changeFavorite() {
        try {
            val saved = FavoritesStore.toggle(this, notice)
            updateFavoriteState()
            Toast.makeText(this,
                if (saved) "Guardada en favoritas" else "Eliminada de favoritas",
                Toast.LENGTH_SHORT).show()
        } catch (_: Exception) {
            Toast.makeText(this, "No se pudo guardar el cambio", Toast.LENGTH_LONG).show()
        }
    }

    private fun share() {
        val message = NoticeText.headline(notice.title) + "\n" + notice.entity +
            "\n" + (if (notice.id.startsWith("CIDO")) "CIDO" else if (notice.id.startsWith("BOE-A-")) "BOE" else if (notice.id.startsWith("MD-")) "BOCM" else if (notice.id.startsWith("CM-")) "DOCM" else "BOP") + " " + notice.province + " · " + notice.date +
            " · Registro " + notice.id + "\n" + notice.url +
            "\n\nVerifica las bases y los plazos en el anuncio oficial."
        try {
            startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_SUBJECT, "Convocatoria de empleo público · OpoAlert")
                putExtra(Intent.EXTRA_TEXT, message)
            }, "Compartir convocatoria"))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, "No hay aplicaciones para compartir", Toast.LENGTH_LONG).show()
        }
    }

    private fun openOfficial() {
        val province = Province.fromLabel(notice.province) ?: Province.fromNoticeId(notice.id)
        val link = Uri.parse(notice.url)
        if (link.scheme != "https" ||
            link.host != province.pdfHost ||
            !province.allowsOfficialPath(link.path.orEmpty())) {
            Toast.makeText(this, "El enlace oficial no se ha podido verificar.", Toast.LENGTH_LONG).show()
            return
        }
        try {
            startActivity(Intent(Intent.ACTION_VIEW, link))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, "No hay aplicación para abrir la publicación.", Toast.LENGTH_LONG).show()
        }
    }

    private fun action(label: String, background: String, foreground: String, click: () -> Unit): TextView =
        text(label, 15f, foreground, true).apply {
            gravity = Gravity.CENTER
            this.background = rounded(background, 16)
            isClickable = true
            isFocusable = true
            minHeight = dp(48)
            setOnClickListener { click() }
        }

    private fun column(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
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
