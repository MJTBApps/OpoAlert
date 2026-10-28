package es.opoalert.app

import org.json.JSONObject

data class Notice(
    val id: String,
    val title: String,
    val entity: String,
    val date: String,
    val bulletin: String,
    val type: String,
    val url: String,
    // Old favorites (v0.9 and earlier) do not have this field: default Valencia.
    val province: String = Province.fromNoticeId(id).label,
) {
    fun toJson(): JSONObject = JSONObject().apply {
        put("id", id)
        put("title", title)
        put("entity", entity)
        put("date", date)
        put("bulletin", bulletin)
        put("type", type)
        put("url", url)
        put("province", province)
    }

    companion object {
        fun fromJson(json: JSONObject): Notice {
            val id = json.getString("id")
            return Notice(
                id = id,
                title = json.getString("title"),
                entity = json.optString("entity", "Administración pública"),
                date = json.getString("date"),
                bulletin = json.optString("bulletin", ""),
                type = json.optString("type", "Plaza"),
                url = json.getString("url"),
                province = json.optString("province", Province.fromNoticeId(id).label),
            )
        }
    }
}
