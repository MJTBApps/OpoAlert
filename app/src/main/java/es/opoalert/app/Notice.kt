package es.opoalert.app

import org.json.JSONObject

data class Notice(
    val id: String,
    val title: String,
    val entity: String,
    val date: String,
    val bulletin: String,
    val type: String,
    val url: String
) {
    fun toJson(): JSONObject = JSONObject().apply {
        put("id", id)
        put("title", title)
        put("entity", entity)
        put("date", date)
        put("bulletin", bulletin)
        put("type", type)
        put("url", url)
    }

    companion object {
        fun fromJson(json: JSONObject) = Notice(
            id = json.getString("id"),
            title = json.getString("title"),
            entity = json.optString("entity", "Administración pública"),
            date = json.getString("date"),
            bulletin = json.optString("bulletin", ""),
            type = json.optString("type", "Plaza"),
            url = json.getString("url")
        )
    }
}
