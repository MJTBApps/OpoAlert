package es.opoalert.app

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/**
 * Un anuncio que puede ser otro paso de una favorita. [state]: «pending» (sin contestar),
 * «yes» (el usuario dice que es de la convocatoria) o «no» (se oculta para siempre).
 * [unread]: aún no se ha abierto la ficha de la favorita (etiqueta «NOVEDAD»).
 */
data class FollowUpItem(val notice: Notice, val step: String, val state: String = PENDING, val unread: Boolean = false) {
    companion object {
        const val PENDING = "pending"
        const val YES = "yes"
        const val NO = "no"
    }
}

/** Seguimiento de una favorita. [initialized]: ya se buscó una vez (lo que había entonces no avisa). */
data class FollowUpState(val initialized: Boolean = false, val items: List<FollowUpItem> = emptyList()) {
    /** Lo que se enseña: sin los descartados, del más reciente al más antiguo. */
    val visible: List<FollowUpItem>
        get() = items.filter { it.state != FollowUpItem.NO }
            .sortedByDescending { FollowUps.dayKey(it.notice.date) }
    val unreadCount: Int get() = items.count { it.unread && it.state != FollowUpItem.NO }
}

/**
 * Seguimiento de favoritas (1.59.0, Premium). Todo se queda en el móvil: el emparejamiento
 * se hace con los feeds públicos que ya descarga la app (ver [FollowUpMatcher]).
 */
object FollowUps {
    private const val PREFS = "opoalert_store"
    private const val KEY = "favorite_followups_v1"
    /** Los boletines de más se descargan como mucho cada 3 horas (o al guardar una favorita). */
    private const val EVERY_MS = 3 * 60 * 60 * 1000L
    private const val MAX_ITEMS = 40

    fun dayKey(date: String): String {
        val p = date.split('/')
        return if (p.size == 3) p[2] + p[1] + p[0] else date
    }

    // ---------- guardado ----------
    data class Stored(val lastCheck: Long, val favorites: Map<String, FollowUpState>)

    fun encode(stored: Stored): String {
        val favorites = JSONObject()
        for ((id, state) in stored.favorites) {
            favorites.put(id, JSONObject().apply {
                put("init", state.initialized)
                put("items", JSONArray().also { array ->
                    for (item in state.items) array.put(item.notice.toJson().apply {
                        put("step", item.step)
                        put("state", item.state)
                        put("unread", item.unread)
                    })
                })
            })
        }
        return JSONObject().put("v", 1).put("lastCheck", stored.lastCheck).put("favorites", favorites).toString()
    }

    fun parse(raw: String?): Stored {
        if (raw.isNullOrBlank()) return Stored(0, emptyMap())
        return try {
            val root = JSONObject(raw)
            val favorites = root.optJSONObject("favorites") ?: JSONObject()
            Stored(root.optLong("lastCheck"), favorites.keys().asSequence().associateWith { id ->
                val o = favorites.getJSONObject(id)
                val array = o.optJSONArray("items") ?: JSONArray()
                FollowUpState(o.optBoolean("init"), (0 until array.length()).mapNotNull { i ->
                    try {
                        val json = array.getJSONObject(i)
                        val state = json.optString("state", FollowUpItem.PENDING)
                        FollowUpItem(Notice.fromJson(json), json.optString("step", FollowUpMatcher.STEP_OTHER),
                            if (state in setOf(FollowUpItem.YES, FollowUpItem.NO)) state else FollowUpItem.PENDING,
                            json.optBoolean("unread"))
                    } catch (_: Exception) { null }
                })
            })
        } catch (_: Exception) {
            Stored(0, emptyMap())
        }
    }

    @Synchronized
    fun stored(context: Context): Stored =
        parse(context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY, null))

    @Synchronized
    private fun save(context: Context, stored: Stored) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY, encode(stored)).apply()
    }

    fun state(context: Context, favoriteId: String): FollowUpState = stored(context).favorites[favoriteId] ?: FollowUpState()

    @Synchronized
    private fun change(context: Context, favoriteId: String, transform: (FollowUpState) -> FollowUpState) {
        val current = stored(context)
        val next = current.favorites.toMutableMap()
        next[favoriteId] = transform(next[favoriteId] ?: FollowUpState())
        save(context, current.copy(favorites = next))
    }

    /** Al abrir la ficha de la favorita: las novedades dejan de serlo. */
    fun markRead(context: Context, favoriteId: String) {
        if (state(context, favoriteId).unreadCount == 0) return
        change(context, favoriteId) { s -> s.copy(items = s.items.map { it.copy(unread = false) }) }
    }

    /** «Sí» o «No» a «¿Es de esta convocatoria?». «No» la oculta para siempre. */
    fun answer(context: Context, favoriteId: String, noticeId: String, yes: Boolean) {
        change(context, favoriteId) { s ->
            s.copy(items = s.items.map {
                if (it.notice.id == noticeId) it.copy(state = if (yes) FollowUpItem.YES else FollowUpItem.NO, unread = false) else it
            })
        }
    }

    /** Se borra al quitar la favorita. */
    @Synchronized
    fun remove(context: Context, favoriteId: String) {
        val current = stored(context)
        if (favoriteId !in current.favorites) return
        save(context, current.copy(favorites = current.favorites - favoriteId))
    }

    // ---------- búsqueda (sin Android: se prueba en FollowUpsTest) ----------
    /** Origen de un anuncio para el emparejador. */
    fun itemFor(notice: Notice, extracts: Map<String, BoeExtract>): FollowUpMatcher.Item {
        val province = Province.fromLabel(notice.province) ?: Province.fromNoticeId(notice.id)
        return FollowUpMatcher.Item(
            url = notice.url, title = notice.title, entity = notice.entity, date = notice.date,
            source = province.code, cido = SourceCatalog.isCido(province), isBoe = province == Province.BOE,
            extract = extracts[notice.url],
        )
    }

    /**
     * Busca entre [candidates] los posibles pasos de cada favorita. Devuelve el estado nuevo y
     * las novedades que merecen aviso: las que aparecen después de la primera búsqueda.
     */
    fun update(
        favorites: List<Notice>, candidates: List<Notice>, extracts: Map<String, BoeExtract>,
        previous: Map<String, FollowUpState>,
    ): Pair<Map<String, FollowUpState>, List<Pair<Notice, FollowUpItem>>> {
        val byOrg = HashMap<String, MutableList<Pair<Notice, FollowUpMatcher.Item>>>()
        for (notice in candidates.distinctBy { it.id }) {
            val item = itemFor(notice, extracts)
            val org = item.org ?: continue
            byOrg.getOrPut(org.name) { mutableListOf() }.add(notice to item)
        }
        val result = LinkedHashMap<String, FollowUpState>()
        val fresh = mutableListOf<Pair<Notice, FollowUpItem>>()
        for (favorite in favorites) {
            val before = previous[favorite.id] ?: FollowUpState()
            val fav = itemFor(favorite, extracts)
            val org = fav.org
            if (org == null) {
                result[favorite.id] = before.copy(initialized = true)
                continue
            }
            val known = before.items.map { it.notice.id }.toHashSet()
            val added = byOrg[org.name].orEmpty()
                .filter { (notice, item) -> notice.id != favorite.id && notice.id !in known && FollowUpMatcher.isFollowUp(fav, item) }
                .map { (notice, item) -> FollowUpItem(notice, item.step, unread = before.initialized) }
            fresh += added.filter { it.unread }.map { favorite to it }
            val items = (before.items + added).sortedByDescending { dayKey(it.notice.date) }.take(MAX_ITEMS)
            result[favorite.id] = FollowUpState(true, items)
        }
        return result to fresh
    }

    // ---------- revisión periódica ----------
    /**
     * Se llama desde [Repository.sync] con los feeds ya descargados. Solo con Premium (o sin
     * cobro) y con favoritas de organismos locales. Descarga, como mucho cada 3 horas, los
     * boletines de la comunidad de cada favorita y el BOE. Devuelve las novedades para avisar.
     */
    fun check(context: Context, downloaded: Map<Province, List<Notice>>, now: Long = System.currentTimeMillis()):
        List<Pair<Notice, FollowUpItem>> {
        if (!Premium.alertsUnlocked(context)) return emptyList()
        val favorites = FavoritesStore.list(context)
        if (favorites.isEmpty()) return emptyList()
        val stored = stored(context)
        val pending = favorites.any { stored.favorites[it.id]?.initialized != true }
        val sources = favorites.flatMap { fav ->
            val province = Province.fromLabel(fav.province) ?: Province.fromNoticeId(fav.id)
            SourceCatalog.followUpSources(province)
        }.toSet()
        val feeds = downloaded.filterKeys { it in sources }.toMutableMap()
        if (pending || now - stored.lastCheck >= EVERY_MS) {
            for (province in sources - feeds.keys) {
                try {
                    feeds[province] = RemoteFeedReader.fetch(province.feedUrl, province, context).notices
                } catch (_: Exception) {
                    // Sin ese boletín esta vez: se busca en los demás y se vuelve a intentar.
                }
            }
        } else if (feeds.isEmpty()) return emptyList()
        val extracts = if (Province.BOE in feeds) DeadlineStore.boeExtracts(context) else emptyMap()
        val (next, fresh) = update(favorites, feeds.values.flatten(), extracts, stored.favorites)
        val checked = if (pending || now - stored.lastCheck >= EVERY_MS) now else stored.lastCheck
        synchronized(this) {
            // Lo que el usuario haya contestado o leído mientras se buscaba manda.
            save(context, Stored(checked, keepAnswers(next, stored(context).favorites)))
        }
        return fresh
    }

    /** Copia en [next] el estado y la lectura guardados en [latest] para los mismos anuncios. */
    fun keepAnswers(next: Map<String, FollowUpState>, latest: Map<String, FollowUpState>): Map<String, FollowUpState> =
        next.mapValues { (id, state) ->
            val saved = latest[id]?.items?.associateBy { it.notice.id }.orEmpty()
            state.copy(items = state.items.map { item ->
                saved[item.notice.id]?.let { item.copy(state = it.state, unread = it.unread) } ?: item
            })
        }
}
