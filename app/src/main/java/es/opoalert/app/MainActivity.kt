package es.opoalert.app

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.Switch
import java.util.Calendar
import java.text.SimpleDateFormat
import java.util.Locale
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast

class MainActivity : Activity() {
    private lateinit var list: LinearLayout
    private lateinit var countText: TextView
    private lateinit var favoritesCountText: TextView
    private lateinit var statusText: TextView
    private lateinit var progressBar: ProgressBar
    private lateinit var refreshButton: Button
    private lateinit var alertsSwitch: Switch
    private lateinit var recentOnlySwitch: Switch
    private lateinit var feedSettingsButton: Button
    private lateinit var sourceInfoText: TextView
    private lateinit var searchInput: EditText
    private lateinit var tabsRow: LinearLayout
    private lateinit var filterRow: LinearLayout
    private lateinit var scroll: ScrollView
    private lateinit var resultsText: TextView

    private var selectedTab = TAB_ALL
    private var selectedFilter = FILTER_ALL
    private var notices: List<Notice> = emptyList()
    private var loading = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        list = findViewById(R.id.listContainer)
        countText = findViewById(R.id.countText)
        favoritesCountText = findViewById(R.id.favoritesCountText)
        statusText = findViewById(R.id.statusText)
        progressBar = findViewById(R.id.progressBar)
        refreshButton = findViewById(R.id.refreshButton)
        alertsSwitch = findViewById(R.id.alertsSwitch)
        recentOnlySwitch = findViewById(R.id.recentOnlySwitch)
        feedSettingsButton = findViewById(R.id.feedSettingsButton)
        sourceInfoText = findViewById(R.id.sourceInfoText)
        searchInput = findViewById(R.id.searchInput)
        tabsRow = findViewById(R.id.tabsRow)
        filterRow = findViewById(R.id.filterRow)
        scroll = findViewById(R.id.resultsScroll)
        resultsText = findViewById(R.id.resultsText)

        selectedTab = savedInstanceState?.getString("selectedTab") ?: TAB_ALL
        selectedFilter = savedInstanceState?.getString("selectedFilter") ?: FILTER_ALL

        Notifications.createChannel(this)
        BopWorker.schedule(this)
        alertsSwitch.isChecked = Repository.alertsEnabled(this)
        alertsSwitch.setOnCheckedChangeListener { _, enabled ->
            Repository.setAlertsEnabled(this, enabled)
            if (enabled && Build.VERSION.SDK_INT >= 33 &&
                checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
            ) {
                requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 333)
            } else if (enabled) {
                Toast.makeText(this, "Avisos activados; Android programa las comprobaciones", Toast.LENGTH_LONG).show()
            }
        }
        refreshButton.setOnClickListener { refresh() }
        feedSettingsButton.setOnClickListener { configureFeed() }
        recentOnlySwitch.setOnCheckedChangeListener { _, _ -> render() }
        searchInput.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) { render() }
            override fun afterTextChanged(s: Editable?) {}
        })
        notices = Repository.cached(this)
        updateHeader()
        buildTabs()
        buildFilters()
        render()
        refresh()
    }

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putString("selectedTab", selectedTab)
        outState.putString("selectedFilter", selectedFilter)
        super.onSaveInstanceState(outState)
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<out String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 333 && grantResults.firstOrNull() != PackageManager.PERMISSION_GRANTED) {
            Repository.setAlertsEnabled(this, false)
            alertsSwitch.isChecked = false
            Toast.makeText(this, "Sin permiso de notificaciones; puedes activarlo después", Toast.LENGTH_LONG).show()
        }
    }

    private fun refresh() {
        if (loading) return
        loading = true
        progressBar.visibility = View.VISIBLE
        refreshButton.isEnabled = false
        statusText.text = if (Repository.feedUrl(this).isBlank())
            "Consultando la portada del BOP (parcial)…" else "Consultando el lector central…"
        Thread {
            try {
                val result = Repository.sync(applicationContext)
                runOnUiThread {
                    notices = result.all
                    updateHeader()
                    buildTabs()
                    render()
                    statusText.text = "Consulta: ${Repository.lastSync(this)} · ${result.scanned} convocatorias recibidas"
                    sourceInfoText.text = "${result.sourceMessage}\n${result.historyMessage}"
                    Notifications.show(this, result.newOnes)
                    finishRefresh()
                }
            } catch (error: Exception) {
                runOnUiThread {
                    statusText.text = "Sin actualizar: ${error.message ?: "Error de conexión"}. Datos guardados disponibles."
                    sourceInfoText.text = Repository.lastSource(this) + "\n" + Repository.lastHistory(this)
                    finishRefresh()
                }
            }
        }.start()
    }

    /** Permite configurar GitHub Pages sin recompilar; no toca los favoritos. */
    private fun configureFeed() {
        val field = EditText(this).apply {
            setSingleLine(true)
            setText(Repository.feedUrl(this@MainActivity))
            hint = "https://usuario.github.io/OpoAlert/convocatorias.json"
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_URI
            textSize = 14f
        }
        val wrapper = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(8), dp(20), 0)
            addView(field)
        }
        AlertDialog.Builder(this)
            .setTitle("Fuente de convocatorias")
            .setMessage("Pega aqui la URL publica HTTPS del feed generado por OpoAlert. Si no tienes servidor, puedes continuar con la portada parcial.")
            .setView(wrapper)
            .setPositiveButton("Guardar") { _, _ ->
                try {
                    val address = field.text.toString().trim()
                    if (address.isBlank()) {
                        Toast.makeText(this, "Introduce la URL o elige Solo portada", Toast.LENGTH_LONG).show()
                    } else {
                        Repository.setFeedUrl(this, address)
                        updateHeader()
                        refresh()
                    }
                } catch (error: IllegalArgumentException) {
                    Toast.makeText(this, error.message ?: "URL no valida", Toast.LENGTH_LONG).show()
                }
            }
            .setNeutralButton("Solo portada") { _, _ ->
                Repository.setFeedUrl(this, "")
                updateHeader()
                refresh()
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun isRecent(date: String): Boolean {
        return try {
            val format = SimpleDateFormat("dd/MM/yyyy", Locale("es", "ES")).apply { isLenient = false }
            val published = format.parse(date) ?: return false
            val today = Calendar.getInstance().apply {
                set(Calendar.HOUR_OF_DAY, 23)
                set(Calendar.MINUTE, 59)
                set(Calendar.SECOND, 59)
                set(Calendar.MILLISECOND, 999)
            }
            val earliest = (today.clone() as Calendar).apply { add(Calendar.DAY_OF_YEAR, -29) }
            val dateOnly = Calendar.getInstance().apply { time = published }
            dateOnly.set(Calendar.HOUR_OF_DAY, 23)
            dateOnly.set(Calendar.MINUTE, 59)
            dateOnly.set(Calendar.SECOND, 59)
            dateOnly.set(Calendar.MILLISECOND, 999)
            !dateOnly.before(earliest) && !dateOnly.after(today)
        } catch (_: Exception) { false }
    }

    private fun finishRefresh() {
        loading = false
        progressBar.visibility = View.GONE
        refreshButton.isEnabled = true
    }

    private fun updateHeader() {
        countText.text = "${notices.size} convocatorias guardadas"
        favoritesCountText.text = "★ ${FavoritesStore.list(this).size} favoritas"
        val previous = Repository.lastSync(this)
        statusText.text = if (previous.isBlank())
            "Primera conexión pendiente · Fuente: BOP Valencia" else
            "Última consulta: $previous"
        sourceInfoText.text = if (Repository.feedUrl(this).isBlank())
            "Fuente: solo portada del BOP. Pulsa FUENTE para usar el lector completo."
        else Repository.lastSource(this) + "\n" + Repository.lastHistory(this)
    }

    private fun buildTabs() {
        tabsRow.removeAllViews()
        val favoritesCount = FavoritesStore.list(this).size
        for ((tab, label) in listOf(TAB_ALL to "Explorar", TAB_FAVORITES to "★ Favoritas ($favoritesCount)")) {
            val selected = tab == selectedTab
            val item = TextView(this).apply {
                text = label
                textSize = 15f
                typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
                gravity = Gravity.CENTER
                setTextColor(Color.parseColor(if (selected) "#FFFFFF" else "#334155"))
                background = rounded(if (selected) "#1D4ED8" else "#E8EEF6", 14)
                setPadding(dp(12), dp(13), dp(12), dp(13))
                isClickable = true
                isFocusable = true
                contentDescription = if (tab == TAB_ALL) "Ver todas las convocatorias" else "Ver mis favoritos"
                setOnClickListener {
                    selectedTab = tab
                    buildTabs()
                    render()
                    scroll.scrollTo(0, 0)
                }
            }
            tabsRow.addView(item, LinearLayout.LayoutParams(0, dp(48), 1f).apply {
                if (tab == TAB_ALL) marginEnd = dp(7)
            })
        }
    }

    private fun buildFilters() {
        filterRow.removeAllViews()
        for (name in listOf(FILTER_ALL, FILTER_POOLS, FILTER_POSITIONS)) {
            val selected = name == selectedFilter
            val chip = TextView(this).apply {
                text = name
                textSize = 13f
                setTextColor(if (selected) Color.WHITE else Color.rgb(51, 65, 85))
                typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
                gravity = Gravity.CENTER
                setPadding(dp(16), dp(10), dp(16), dp(10))
                background = rounded(if (selected) "#1D4ED8" else "#E8EEF6", 30)
                isClickable = true
                isFocusable = true
                setOnClickListener {
                    selectedFilter = name
                    buildFilters()
                    render()
                    scroll.scrollTo(0, 0)
                }
            }
            filterRow.addView(chip, LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { marginEnd = dp(8) })
        }
    }

    private fun render(keepScroll: Boolean = false) {
        val oldScroll = if (keepScroll) scroll.scrollY else 0
        list.removeAllViews()
        val term = searchInput.text.toString().trim()
        val favorites = FavoritesStore.list(this)
        val favoriteIds = favorites.map { it.id }.toHashSet()
        val source = if (selectedTab == TAB_FAVORITES) favorites else notices
        val shown = source.filter { notice ->
            val matchesFilter = selectedFilter == FILTER_ALL ||
                (selectedFilter == FILTER_POOLS && notice.type.startsWith("Bolsa")) ||
                (selectedFilter == FILTER_POSITIONS && notice.type.startsWith("Plaza"))
            val matchesDate = selectedTab == TAB_FAVORITES || !recentOnlySwitch.isChecked || isRecent(notice.date)
            matchesFilter && matchesDate && (term.isEmpty() || notice.title.contains(term, ignoreCase = true) ||
                notice.entity.contains(term, ignoreCase = true) ||
                notice.id.contains(term, ignoreCase = true))
        }
        resultsText.text = if (selectedTab == TAB_FAVORITES)
            "MIS FAVORITAS · ${shown.size}" else "CONVOCATORIAS · ${shown.size}"
        if (shown.isEmpty()) {
            val label = when {
                selectedTab == TAB_FAVORITES && favorites.isEmpty() ->
                    "Todavía no has guardado ninguna convocatoria.\n\nEn Explorar, toca la estrella ☆ de una plaza o bolsa para añadirla aquí."
                source.isEmpty() -> "Todavía no hay datos. Pulsa ↻ para consultar el BOP."
                else -> "No hay convocatorias que coincidan con la búsqueda o el filtro."
            }
            val empty = text(label, 14, "#64748B")
            empty.gravity = Gravity.CENTER
            empty.setPadding(dp(18), dp(45), dp(18), dp(45))
            list.addView(empty)
        } else {
            for (item in shown) addCard(item, item.id in favoriteIds)
        }
        if (keepScroll) scroll.post { scroll.scrollTo(0, oldScroll) }
    }

    private fun addCard(item: Notice, isFavorite: Boolean) {
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(15), dp(16), dp(14))
            background = rounded("#FFFFFF", 17, if (isFavorite) "#FCD34D" else "#E2E8F0")
            elevation = dp(1).toFloat()
            isClickable = true
            isFocusable = true
            setOnClickListener { showDetail(item) }
        }
        val meta = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        meta.addView(text(item.type.uppercase(), 11, "#1D4ED8", true),
            LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        meta.addView(text(item.date, 11, "#64748B"))
        val star = text(if (isFavorite) "★" else "☆", 26, if (isFavorite) "#B45309" else "#64748B", true).apply {
            gravity = Gravity.CENTER
            setPadding(dp(12), dp(3), dp(2), dp(3))
            isClickable = true
            isFocusable = true
            contentDescription = if (isFavorite) "Quitar de favoritos" else "Añadir a favoritos"
            setOnClickListener { toggleFavorite(item) }
        }
        meta.addView(star)
        card.addView(meta)
        card.addView(text(item.title, 14, "#0F172A", true).apply {
            maxLines = 4
            setPadding(0, dp(10), 0, dp(7))
        })
        card.addView(text(item.entity, 12, "#64748B"))
        val footer = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(13), 0, 0)
        }
        footer.addView(text("BOP ${item.bulletin} · ${item.id}    ›", 12, "#2563EB").apply {
            isClickable = true
            isFocusable = true
            contentDescription = "Abrir detalles de la convocatoria"
            setOnClickListener { showDetail(item) }
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        footer.addView(text("Compartir ↗", 12, "#1D4ED8", true).apply {
            isClickable = true
            isFocusable = true
            setPadding(dp(12), dp(5), 0, dp(5))
            setOnClickListener { share(item) }
        })
        card.addView(footer)
        list.addView(card, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { bottomMargin = dp(11) })
    }

    private fun toggleFavorite(item: Notice) {
        try {
            val saved = FavoritesStore.toggle(this, item)
            Toast.makeText(this, if (saved) "Añadida a favoritas ★" else "Eliminada de favoritas", Toast.LENGTH_SHORT).show()
            updateHeader()
            buildTabs()
            render(keepScroll = true)
        } catch (_: Exception) {
            Toast.makeText(this, "No se pudo guardar el cambio", Toast.LENGTH_LONG).show()
        }
    }

    private fun showDetail(item: Notice) {
        val message = "${item.entity}\n\n" +
            "Tipo: ${item.type}\n" +
            "Publicación: ${item.date}\n" +
            "Boletín: ${item.bulletin}\n" +
            "Registro: ${item.id}\n\n" +
            "IMPORTANTE: publicar las bases no implica necesariamente que el plazo de solicitudes esté abierto. Comprueba el anuncio oficial y, cuando proceda, el BOE."
        val favoriteAction = if (FavoritesStore.contains(this, item.id)) "★ Quitar favorita" else "☆ Guardar favorita"
        AlertDialog.Builder(this)
            .setTitle(item.title)
            .setMessage(message)
            .setPositiveButton("PDF oficial") { _, _ -> openUrl(item.url) }
            .setNeutralButton(favoriteAction) { _, _ -> toggleFavorite(item) }
            .setNegativeButton("Cerrar", null)
            .show()
    }

    private fun share(item: Notice) {
        val message = "${item.title}\n${item.entity}\nBOP Valencia · ${item.date} · Registro ${item.id}\n${item.url}\n\nConsulta siempre el anuncio oficial y los plazos."
        try {
            startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_SUBJECT, "Convocatoria de empleo público · OpoAlert")
                putExtra(Intent.EXTRA_TEXT, message)
            }, "Compartir convocatoria"))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, "No hay aplicaciones disponibles para compartir", Toast.LENGTH_LONG).show()
        }
    }

    private fun openUrl(url: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, "No hay navegador o visor para abrir el enlace", Toast.LENGTH_LONG).show()
        }
    }

    private fun text(value: String, sp: Int, color: String, bold: Boolean = false): TextView =
        TextView(this).apply {
            text = value
            textSize = sp.toFloat()
            setTextColor(Color.parseColor(color))
            if (bold) typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
        }

    private fun rounded(fill: String, radius: Int, stroke: String? = null): GradientDrawable =
        GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            cornerRadius = dp(radius).toFloat()
            setColor(Color.parseColor(fill))
            if (stroke != null) setStroke(dp(1), Color.parseColor(stroke))
        }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density + 0.5f).toInt()

    companion object {
        private const val TAB_ALL = "all"
        private const val TAB_FAVORITES = "favorites"
        private const val FILTER_ALL = "Todas"
        private const val FILTER_POOLS = "Bolsas"
        private const val FILTER_POSITIONS = "Plazas"
    }
}
