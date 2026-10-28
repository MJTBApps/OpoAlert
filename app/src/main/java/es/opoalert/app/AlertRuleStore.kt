package es.opoalert.app

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

/** Almacenamiento persistente privado; ni cuentas ni envíos de preferencias a terceros. */
object AlertRuleStore {
    const val MAX_RULES = 20
    private const val PREFS = "opoalert_store"
    private const val KEY = "keyword_alert_rules_v1"
    private val whitespace = Regex("\\s+")

    @Synchronized
    fun list(context: Context): List<AlertRule> {
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY, "[]") ?: "[]"
        return try {
            val array = JSONArray(raw)
            (0 until array.length()).mapNotNull { i ->
                try {
                    val item = array.getJSONObject(i)
                    val available = item.optJSONArray("provinces") ?: JSONArray()
                    val provinces = (0 until available.length())
                        .mapNotNull { j ->
                            Province.entries.find { it.code == available.optString(j) }
                        }.toSet()
                    val id = item.optString("id").trim()
                    val phrase = item.optString("phrase").trim()
                    if (id.isEmpty() || phrase.isEmpty() || provinces.isEmpty()) null
                    else AlertRule(id, phrase, provinces, item.optBoolean("enabled", true))
                } catch (_: Exception) {
                    null
                }
            }.distinctBy { it.id }.take(MAX_RULES)
        } catch (_: Exception) { emptyList() }
    }

    @Synchronized
    fun upsert(
        context: Context, id: String?, input: String, provinces: Set<Province>
    ): AlertRule {
        val phrase = input.trim().replace(whitespace, " ")
        require(phrase.length in 3..70) { "Escribe entre 3 y 70 caracteres." }
        require(provinces.isNotEmpty()) { "Selecciona al menos una provincia." }
        val current = list(context)
        require(id == null || current.any { it.id == id }) { "La alerta ya no existe." }
        require(id != null || current.size < MAX_RULES) { "Máximo de 20 alertas." }
        val key = SearchText.normalize(phrase)
        require(current.none {
            it.id != id && SearchText.normalize(it.phrase) == key && it.provinces == provinces
        }) { "Ya tienes esa alerta para las mismas provincias." }
        val old = current.find { it.id == id }
        val rule = AlertRule(id ?: UUID.randomUUID().toString(), phrase, provinces, old?.enabled ?: true)
        persist(context, if (old == null) listOf(rule) + current
            else current.map { if (it.id == id) rule else it })
        return rule
    }

    @Synchronized
    fun enable(context: Context, id: String, enabled: Boolean) {
        persist(context, list(context).map { if (it.id == id) it.copy(enabled = enabled) else it })
    }

    @Synchronized
    fun remove(context: Context, id: String) {
        persist(context, list(context).filterNot { it.id == id })
    }

    private fun persist(context: Context, rules: List<AlertRule>) {
        val array = JSONArray()
        for (rule in rules) {
            val provinces = JSONArray()
            Province.entries.filter { it in rule.provinces }.forEach { provinces.put(it.code) }
            array.put(JSONObject().apply {
                put("id", rule.id)
                put("phrase", rule.phrase)
                put("provinces", provinces)
                put("enabled", rule.enabled)
            })
        }
        val saved = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY, array.toString()).commit()
        if (!saved) throw IllegalStateException("No se pudieron guardar las alertas.")
    }
}
