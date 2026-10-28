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
import android.provider.Settings
import android.text.Editable
import android.text.TextUtils
import android.text.TextWatcher
import android.view.Gravity
import android.view.View
import android.widget.EditText
import android.widget.ImageButton
import android.widget.FrameLayout
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.PopupMenu
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

/**
 * OpoAlert 1.3.0: the notices are the main content. The compact header only presents
 * verified source metadata; all advanced settings are off the home screen.
 */
class MainActivity : Activity() {
    private lateinit var list: LinearLayout
    private lateinit var countText: TextView
    private lateinit var favoritesCountText: TextView
    private lateinit var statusText: TextView
    private lateinit var sourceInfoText: TextView
    private lateinit var historyInfoText: TextView
    private lateinit var progressBar: ProgressBar
    private lateinit var refreshButton: ImageButton
    private lateinit var menuButton: ImageButton
    private lateinit var provinceSelector: TextView
    private lateinit var searchInput: EditText
    private lateinit var tabsRow: LinearLayout
    private lateinit var filterRow: LinearLayout
    private lateinit var scroll: ScrollView
    private lateinit var resultsText: TextView

    private var selectedTab = TAB_ALL
    private var selectedFilter = FILTER_ALL
    private var notices: List<Notice> = emptyList()
    private var displayedLimit = PAGE_SIZE
    private var loading = false
    private var refreshPending = false
    private lateinit var demoAds: DemoAds


    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        list = findViewById(R.id.listContainer)
        countText = findViewById(R.id.countText)
        favoritesCountText = findViewById(R.id.favoritesCountText)
        statusText = findViewById(R.id.statusText)
        sourceInfoText = findViewById(R.id.sourceInfoText)
        historyInfoText = findViewById(R.id.historyInfoText)
        progressBar = findViewById(R.id.progressBar)
        refreshButton = findViewById(R.id.refreshButton)
        menuButton = findViewById(R.id.menuButton)
        provinceSelector = findViewById(R.id.provinceSelector)
        searchInput = findViewById(R.id.searchInput)
        tabsRow = findViewById(R.id.tabsRow)
        filterRow = findViewById(R.id.filterRow)
        scroll = findViewById(R.id.resultsScroll)
        resultsText = findViewById(R.id.resultsText)

        selectedTab = savedInstanceState?.getString("selectedTab")
            ?: intent.getStringExtra(EXTRA_OPEN_TAB) ?: TAB_ALL
        selectedFilter = savedInstanceState?.getString("selectedFilter") ?: FILTER_ALL

        demoAds = DemoAds(this) {
            if (!isFinishing && !isDestroyed) render(keepScroll = true)
        }
        Notifications.createChannel(this)
        BopWorker.schedule(this)
        refreshButton.setOnClickListener { refresh() }
        menuButton.setOnClickListener { showOptions() }
        provinceSelector.setOnClickListener { showProvinceChooser() }
        searchInput.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                render()
                scroll.scrollTo(0, 0)
            }
            override fun afterTextChanged(s: Editable?) {}
        })

        notices = Repository.cached(this)
        updateHeader()
        buildTabs()
        buildFilters()
        render()
        refresh()

        // Android 13+ requests the system notification permission once on first launch.
        // On earlier Android versions, notification channels are enabled by default.
        window.decorView.post {
            if (!requestNotificationsOnce()) showProvincePickerIfFirstLaunch()
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putString("selectedTab", selectedTab)
        outState.putString("selectedFilter", selectedFilter)
        super.onSaveInstanceState(outState)
    }

    /** Devuelve true cuando el sistema abre el dialogo de notificaciones. */
    private fun requestNotificationsOnce(): Boolean {
        val prefs = getSharedPreferences(UI_PREFS, MODE_PRIVATE)
        if (prefs.getBoolean(NOTIFICATIONS_PROMPTED, false)) return false
        prefs.edit().putBoolean(NOTIFICATIONS_PROMPTED, true).apply()
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), NOTIFICATION_PERMISSION_REQUEST)
            return true
        }
        Repository.setAlertsEnabled(this, true)
        return false
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<out String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == NOTIFICATION_PERMISSION_REQUEST) {
            val granted = grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED
            Repository.setAlertsEnabled(this, granted)
            if (!granted) {
                Toast.makeText(this, "Avisos desactivados. Puedes activarlos en Más opciones.", Toast.LENGTH_LONG).show()
            }
            showProvincePickerIfFirstLaunch()
        }
    }

    /** Keeps notification settings accessible without taking space from the feed. */
    private fun showOptions() {
        val menu = PopupMenu(this, menuButton)
        val enabled = Repository.alertsEnabled(this) && notificationPermissionGranted()
        menu.menu.add(0, 1, 0, if (enabled) "Desactivar avisos" else "Activar avisos")
        menu.menu.add(0, 2, 1, "Acerca de OpoAlert")
        menu.menu.add(0, 3, 2, "Privacidad y publicidad de prueba")
        menu.menu.add(0, 4, 3, "Elegir boletines")
        menu.menu.add(0, 5, 4, "Mis alertas personalizadas")
        menu.setOnMenuItemClickListener { item ->
            when (item.itemId) {
                1 -> {
                    if (enabled) {
                        Repository.setAlertsEnabled(this, false)
                        Toast.makeText(this, "Avisos desactivados", Toast.LENGTH_SHORT).show()
                    } else if (!notificationPermissionGranted() && Build.VERSION.SDK_INT >= 33) {
                        if (shouldShowRequestPermissionRationale(Manifest.permission.POST_NOTIFICATIONS)) {
                            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), NOTIFICATION_PERMISSION_REQUEST)
                        } else {
                            showNotificationSettingsHelp()
                        }
                    } else {
                        Repository.setAlertsEnabled(this, true)
                        Toast.makeText(this, "Avisos activados", Toast.LENGTH_SHORT).show()
                    }
                    true
                }
                2 -> {
                    AlertDialog.Builder(this)
                        .setTitle("OpoAlert 1.3.0")
                        .setMessage("Convocatorias de empleo público de los boletines seleccionados. " +
                            "Las novedades se consultan automáticamente. " +
                            "Comprueba siempre el anuncio y los plazos oficiales antes de presentar una solicitud.")
                        .setPositiveButton("Entendido", null)
                        .show()
                    true
                }
                3 -> {
                    demoAds.showPrivacyOptions()
                    true
                }
                4 -> {
                    showProvinceChooser()
                    true
                }
                5 -> {
                    openAlerts()
                    true
                }
                else -> false
            }
        }
        menu.show()
    }

    private fun openAlerts() {
        startActivity(Intent(this, AlertsActivity::class.java))
    }

    private fun showProvincePickerIfFirstLaunch() {
        if (ProvinceSettings.wasPickerShown(this)) {
            demoAds.start()
            return
        }
        ProvinceSettings.markPickerShown(this)
        showProvinceChooser { demoAds.start() }
    }

    private fun updateProvinceSelector() {
        provinceSelector.text = "Fuentes: ${ProvinceSettings.display(this)} ▾"
    }

    /** Multi-choice dialog without location permission. Favorites remain saved for all provinces. */
    private fun showProvinceChooser(onClosed: () -> Unit = {}) {
        val options = Province.entries
        val chosen = ProvinceSettings.selected(this).toMutableSet()
        val checked = options.map { it in chosen }.toBooleanArray()
        AlertDialog.Builder(this)
            .setTitle("Boletines que quieres seguir")
            .setMultiChoiceItems(options.map { when (it) {
                Province.BOE -> "BOE · toda España"
                Province.BARCELONA, Province.GIRONA, Province.LLEIDA, Province.TARRAGONA -> "CIDO · ${it.label}"
                else -> "BOP · ${it.label}"
            } }.toTypedArray(), checked) { _, index, enabled ->
                if (enabled) chosen.add(options[index]) else chosen.remove(options[index])
            }
            .setPositiveButton("Guardar") { _, _ ->
                if (chosen.isEmpty()) {
                    Toast.makeText(this, "Selecciona al menos un boletín", Toast.LENGTH_LONG).show()
                } else if (ProvinceSettings.save(this, chosen)) {
                    updateProvinceSelector()
                    updateHeader()
                    render()
                    scroll.scrollTo(0, 0)
                    refresh()
                } else {
                    Toast.makeText(this, "No se pudo guardar la selección", Toast.LENGTH_LONG).show()
                }
                onClosed()
            }
            .setNegativeButton("Cancelar") { _, _ -> onClosed() }
            .setOnCancelListener { onClosed() }
            .show()
    }

    private fun notificationPermissionGranted(): Boolean =
        Build.VERSION.SDK_INT < 33 ||
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    private fun showNotificationSettingsHelp() {
        AlertDialog.Builder(this)
            .setTitle("Permiso de notificaciones")
            .setMessage("Para recibir avisos, habilita las notificaciones de OpoAlert en los ajustes de Android.")
            .setPositiveButton("Abrir ajustes") { _, _ ->
                startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                    data = Uri.fromParts("package", packageName, null)
                })
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun refresh() {
        if (loading) {
            refreshPending = true
            return
        }
        loading = true
        progressBar.visibility = View.VISIBLE
        refreshButton.isEnabled = false
        refreshButton.alpha = 0.48f
        statusText.text = "Actualizando…"
        Thread {
            try {
                val result = Repository.sync(applicationContext)
                runOnUiThread {
                    notices = result.all
                    updateHeader()
                    buildTabs()
                    render(keepScroll = true)
                    Notifications.show(this, result.alertMatches)
                    finishRefresh()
                }
            } catch (error: Exception) {
                runOnUiThread {
                    updateHeader()
                    statusText.text = "Sin conexión"
                    Toast.makeText(this, "No se pudo actualizar: ${error.message ?: "Error de conexión"}", Toast.LENGTH_LONG).show()
                    finishRefresh()
                }
            }
        }.start()
    }

    private fun finishRefresh() {
        loading = false
        progressBar.visibility = View.GONE
        refreshButton.isEnabled = true
        refreshButton.alpha = 1f
        if (refreshPending) {
            refreshPending = false
            refresh()
        }
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
            val candidate = Calendar.getInstance().apply {
                time = published
                set(Calendar.HOUR_OF_DAY, 23)
                set(Calendar.MINUTE, 59)
                set(Calendar.SECOND, 59)
                set(Calendar.MILLISECOND, 999)
            }
            !candidate.before(earliest) && !candidate.after(today)
        } catch (_: Exception) { false }
    }

    private fun updateHeader() {
        // Repository retains old cache entries; the home count reflects this 30-day view.
        val selected = ProvinceSettings.selected(this).map { it.label }.toSet()
        countText.text = notices.count { isRecent(it.date) && it.province in selected }.toString()
        updateProvinceSelector()
        val favorites = FavoritesStore.list(this).size
        favoritesCountText.text = "★ $favorites favorita${if (favorites == 1) "" else "s"}"
        val lastSync = Repository.lastSync(this)
        statusText.text = if (lastSync.isBlank()) "Sin consultar" else compactUpdated(lastSync)
        sourceInfoText.text = compactSource(Repository.lastSource(this))
        historyInfoText.text = compactHistory(Repository.lastHistory(this))
    }

    private fun compactUpdated(raw: String): String {
        val match = Regex("""(\d{2})/(\d{2})/\d{4}\s+(\d{2}:\d{2})""").find(raw)
        return if (match == null) "Act. $raw" else
            "Act. ${match.groupValues[1]}/${match.groupValues[2]} ${match.groupValues[3]}"
    }

    private fun compactSource(raw: String): String {
        if (raw.isBlank()) return "Fuentes: ${ProvinceSettings.display(this)}"
        val previous = Regex("""BOP\s+(\d+):\s*(\d+)\s+anuncios\s+en\s+(\d+)\s+paginas""", RegexOption.IGNORE_CASE)
            .find(raw)
        if (previous != null) {
            return "BOP ${previous.groupValues[1]} · ${previous.groupValues[2]} anuncios · ${previous.groupValues[3]} pág."
        }
        return raw.ifBlank { "Fuentes: ${ProvinceSettings.display(this)}" }
    }

    private fun compactHistory(raw: String): String {
        if (!raw.contains("verificado", ignoreCase = true)) return "Histórico pendiente de comprobar"
        val dates = Regex("""(\d{4})-(\d{2})-(\d{2})""").findAll(raw).take(2).toList()
        if (dates.size != 2) return "Histórico verificado · Últimos 30 días"
        val a = dates[0].groupValues
        val b = dates[1].groupValues
        return if (a[1] == b[1]) {
            "Histórico verificado · ${a[3]}/${a[2]} – ${b[3]}/${b[2]}"
        } else {
            "Histórico verificado · ${a[3]}/${a[2]}/${a[1].takeLast(2)} – ${b[3]}/${b[2]}/${b[1].takeLast(2)}"
        }
    }

    /** Tres pestañas equivalentes, sin añadir una fila extra al listado. */
    private fun buildTabs() {
        tabsRow.removeAllViews()
        val choices = listOf(
            TAB_ALL to "Explorar",
            TAB_FAVORITES to "★ Favoritas",
            TAB_ALERTS to "♧ Alertas"
        )
        for ((index, choice) in choices.withIndex()) {
            val (tab, label) = choice
            val selected = selectedTab == tab
            val button = TextView(this).apply {
                text = label
                textSize = 12.5f
                typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
                gravity = Gravity.CENTER
                setTextColor(Color.parseColor(if (selected) "#FFFFFF" else "#34435B"))
                background = rounded(if (selected) "#1E4FD5" else "#E7EDF5", 13)
                isClickable = true
                isFocusable = true
                contentDescription = when (tab) {
                    TAB_ALL -> "Explorar convocatorias"
                    TAB_FAVORITES -> "Ver mis favoritas"
                    else -> "Gestionar mis alertas"
                }
                setOnClickListener {
                    if (tab == TAB_ALERTS) {
                        openAlerts()
                    } else {
                        selectedTab = tab
                        buildTabs()
                        render()
                        scroll.scrollTo(0, 0)
                    }
                }
            }
            tabsRow.addView(button, LinearLayout.LayoutParams(0, dp(44), 1f).apply {
                if (index < choices.lastIndex) marginEnd = dp(6)
            })
        }
    }

    private fun buildFilters() {
        filterRow.removeAllViews()
        for (filter in listOf(FILTER_ALL, FILTER_POOLS, FILTER_POSITIONS)) {
            val selected = selectedFilter == filter
            val chip = TextView(this).apply {
                text = filter
                textSize = 12.5f
                typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
                setTextColor(Color.parseColor(if (selected) "#FFFFFF" else "#34435B"))
                background = rounded(if (selected) "#1E4FD5" else "#E7EDF5", 30)
                gravity = Gravity.CENTER
                setPadding(dp(15), dp(7), dp(15), dp(7))
                minHeight = dp(34)
                isClickable = true
                isFocusable = true
                setOnClickListener {
                    selectedFilter = filter
                    buildFilters()
                    render()
                    scroll.scrollTo(0, 0)
                }
            }
            filterRow.addView(chip, LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { marginEnd = dp(7) })
        }
    }

    private fun render(keepScroll: Boolean = false) {
        if (!keepScroll) displayedLimit = PAGE_SIZE
        val oldScroll = if (keepScroll) scroll.scrollY else 0
        list.removeAllViews()
        val query = SearchText.normalize(searchInput.text.toString().trim())
        val favorites = FavoritesStore.list(this)
        val selectedProvinces = ProvinceSettings.selected(this).map { it.label }.toSet()
        val favoriteIds = favorites.map { it.id }.toHashSet()
        // Las favoritas guardadas en versiones anteriores pueden tener titulos en
        // valenciano; mostramos la ficha castellana actual cuando el feed la trae.
        val latestById = notices.associateBy { it.id }
        val from = if (selectedTab == TAB_FAVORITES)
            favorites.map { latestById[it.id] ?: it } else notices
        val shown = from.filter { item ->
            val correctType = selectedFilter == FILTER_ALL ||
                (selectedFilter == FILTER_POOLS && item.type.startsWith("Bolsa")) ||
                (selectedFilter == FILTER_POSITIONS && item.type.startsWith("Plaza"))
            val correctDate = selectedTab == TAB_FAVORITES || isRecent(item.date)
            // Favorites stay visible even when their province is deselected.
            val correctProvince = selectedTab == TAB_FAVORITES || item.province in selectedProvinces
            val matches = SearchText.matchesNormalized(query,
                item.title, NoticeText.headline(item.title), item.entity, item.id)
            correctType && correctDate && correctProvince && matches
        }
        resultsText.text = if (selectedTab == TAB_FAVORITES)
            "MIS FAVORITAS · ${shown.size}" else "CONVOCATORIAS · ${shown.size}"
        if (shown.isEmpty()) {
            val message = when {
                selectedTab == TAB_FAVORITES && favorites.isEmpty() ->
                    "Aún no tienes favoritas. Toca la estrella de una convocatoria para guardarla aquí."
                from.isEmpty() -> "Todavía no hay convocatorias. Pulsa actualizar para consultar los boletines."
                else -> "No hay convocatorias que coincidan con tu búsqueda."
            }
            list.addView(text(message, 13f, "#64748B").apply {
                gravity = Gravity.CENTER
                setPadding(dp(20), dp(34), dp(20), dp(34))
            })
        } else {
            for ((index, item) in shown.take(displayedLimit).withIndex()) {
                addCard(item, item.id in favoriteIds)
                if (selectedTab == TAB_ALL && index == 3) addDemoBannerIfAvailable()
            }
            if (shown.size > displayedLimit) {
                val pending = shown.size - displayedLimit
                val more = text("Ver ${minOf(PAGE_SIZE, pending)} más · ${shown.size} resultados", 14f, "#1E4FD5", true).apply {
                    gravity = Gravity.CENTER
                    background = rounded("#E7F1FF", 14)
                    minHeight = dp(49)
                    isClickable = true
                    isFocusable = true
                    contentDescription = "Mostrar más convocatorias"
                    setOnClickListener {
                        displayedLimit += PAGE_SIZE
                        render(keepScroll = true)
                    }
                }
                list.addView(more, LinearLayout.LayoutParams(-1, dp(49)).apply {
                    topMargin = dp(11)
                })
            }
            val note = text("Consulta siempre las bases oficiales y los plazos de inscripción.", 10.5f, "#94A3B8")
            note.gravity = Gravity.CENTER
            note.setPadding(dp(7), dp(15), dp(7), 0)
            list.addView(note)
        }
        if (keepScroll) scroll.post { scroll.scrollTo(0, oldScroll) }
    }

    private fun addDemoBannerIfAvailable() {
        val ad = demoAds.availableBanner() ?: return
        val block = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(6), dp(10), dp(6), dp(18))
        }
        block.addView(text("PUBLICIDAD · ANUNCIO DE PRUEBA", 10f, "#64748B").apply {
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(8))
        })
        val slot = FrameLayout(this).apply { minimumHeight = dp(50) }
        (ad.parent as? ViewGroup)?.removeView(ad)
        slot.addView(ad, FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.WRAP_CONTENT,
            FrameLayout.LayoutParams.WRAP_CONTENT,
            Gravity.CENTER
        ))
        block.addView(slot, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ))
        list.addView(block)
    }

    override fun onPause() {
        if (::demoAds.isInitialized) demoAds.pause()
        super.onPause()
    }

    override fun onResume() {
        super.onResume()
        if (::demoAds.isInitialized) demoAds.resume()
        if (::tabsRow.isInitialized) {
            // Las favoritas pueden haber cambiado desde la nueva ficha a pantalla completa.
            updateHeader()
            buildTabs()
            render(keepScroll = true)
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        when (intent.getStringExtra(EXTRA_OPEN_TAB)) {
            TAB_ALL -> selectedTab = TAB_ALL
            TAB_FAVORITES -> selectedTab = TAB_FAVORITES
        }
        if (::tabsRow.isInitialized) {
            buildTabs()
            render()
            scroll.scrollTo(0, 0)
        }
    }

    override fun onDestroy() {
        if (::demoAds.isInitialized) demoAds.destroy()
        super.onDestroy()
    }

    private fun addCard(item: Notice, favorite: Boolean) {
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(11), dp(14), dp(12))
            background = rounded("#FFFFFF", 16, if (favorite) "#EEC77A" else "#DEE5EF")
            elevation = dp(1).toFloat()
            isClickable = true
            isFocusable = true
            setOnClickListener { showDetail(item) }
        }

        val top = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val isPool = item.type.startsWith("Bolsa")
        val tag = text(if (isPool) "BOLSA" else "PLAZA", 10f,
            if (isPool) "#0F766E" else "#1E4FD5", true).apply {
            gravity = Gravity.CENTER
            setPadding(dp(9), dp(5), dp(9), dp(5))
            background = rounded(if (isPool) "#D9F5EB" else "#E4EDFF", 8)
        }
        top.addView(tag)
        if (NoticeText.isProcedureUpdate(item.title)) {
            val procedure = text("TRÁMITE", 9f, "#A16207", true).apply {
                setPadding(dp(8), dp(5), dp(8), dp(5))
                background = rounded("#FEF3C7", 8)
            }
            top.addView(procedure, LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { marginStart = dp(5) })
        }
        top.addView(text(item.date, 11f, "#718096").apply {
            gravity = Gravity.END or Gravity.CENTER_VERTICAL
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        val star = text(if (favorite) "★" else "☆", 25f,
            if (favorite) "#B7791F" else "#64748B").apply {
            gravity = Gravity.CENTER
            minWidth = dp(42)
            minHeight = dp(40)
            isClickable = true
            isFocusable = true
            contentDescription = if (favorite) "Quitar de favoritas" else "Añadir a favoritas"
            setOnClickListener { toggleFavorite(item) }
        }
        top.addView(star)
        card.addView(top)

        card.addView(text(NoticeText.headline(item.title), 15f, "#17243C", true).apply {
            maxLines = 3
            ellipsize = TextUtils.TruncateAt.END
            setLineSpacing(dp(2).toFloat(), 1f)
            setPadding(0, dp(5), 0, 0)
        })
        card.addView(text(item.entity, 12f, "#64748B").apply {
            maxLines = 2
            ellipsize = TextUtils.TruncateAt.END
            setPadding(0, dp(6), 0, 0)
        })

        val footer = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(8), 0, 0)
        }
        val origin = if (item.id.startsWith("CIDO")) "CIDO · ${item.province}"
            else if (item.id.startsWith("BOE-A-")) "BOE · España" else "BOP ${item.province} ${item.bulletin}"
        footer.addView(text("$origin · Ref. ${item.id}", 10.5f, "#64748B"),
            LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        footer.addView(text("Compartir ↗", 11f, "#2452A4", true).apply {
            gravity = Gravity.CENTER_VERTICAL
            minHeight = dp(32)
            setPadding(dp(10), 0, dp(1), 0)
            isClickable = true
            isFocusable = true
            contentDescription = "Compartir convocatoria"
            setOnClickListener { share(item) }
        })
        card.addView(footer)
        list.addView(card, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { bottomMargin = dp(9) })
    }

    private fun toggleFavorite(item: Notice) {
        try {
            val saved = FavoritesStore.toggle(this, item)
            Toast.makeText(this, if (saved) "Guardada en favoritas ★" else "Eliminada de favoritas", Toast.LENGTH_SHORT).show()
            updateHeader()
            buildTabs()
            render(keepScroll = true)
        } catch (_: Exception) {
            Toast.makeText(this, "No se pudo guardar el cambio", Toast.LENGTH_LONG).show()
        }
    }

    private fun showDetail(item: Notice) {
        startActivity(Intent(this, NoticeDetailActivity::class.java).apply {
            putExtra(NoticeDetailActivity.EXTRA_NOTICE, item.toJson().toString())
        })
    }

    private fun share(item: Notice) {
        val origin = if (item.id.startsWith("CIDO")) "CIDO" else if (item.id.startsWith("BOE-A-")) "BOE" else "BOP"
        val message = "${NoticeText.headline(item.title)}\n${item.entity}\n$origin ${item.province} · ${item.date} · Referencia ${item.id}\n" +
            "${item.url}\n\nComprueba siempre el anuncio oficial y los plazos."
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

    private fun text(value: String, sp: Float, color: String, bold: Boolean = false): TextView =
        TextView(this).apply {
            text = value
            textSize = sp
            includeFontPadding = false
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
        private const val PAGE_SIZE = 45
        private const val TAB_ALL = "all"
        private const val TAB_FAVORITES = "favorites"
        private const val TAB_ALERTS = "alerts"
        const val EXTRA_OPEN_TAB = "es.opoalert.app.open_tab"
        private const val FILTER_ALL = "Todas"
        private const val FILTER_POOLS = "Bolsas"
        private const val FILTER_POSITIONS = "Plazas"
        private const val UI_PREFS = "opoalert_ui"
        private const val NOTIFICATIONS_PROMPTED = "notifications_prompted_v08"
        private const val NOTIFICATION_PERMISSION_REQUEST = 333
    }
}
