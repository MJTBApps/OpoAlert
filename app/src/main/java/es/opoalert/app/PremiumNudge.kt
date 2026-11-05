package es.opoalert.app

import android.app.Activity
import android.app.AlertDialog
import android.content.Context

/**
 * Recordatorio de Premium al guardar favoritas (1.52.0): quien guarda varias es
 * quien más partido saca a las alertas. Sale como mucho dos veces: al guardar la
 * tercera favorita y, si sigue sin Premium, a partir de la décima y dos semanas
 * después. Nunca con Premium ni en la versión web (allí las alertas son gratis).
 */
object PremiumNudge {
    private const val PREFS = "opoalert_store"
    private const val SHOWN = "premium_nudge_shown_v1"
    private const val LAST = "premium_nudge_last_v1"
    const val FIRST_AT = 3
    const val SECOND_AT = 10
    const val MAX_TIMES = 2
    const val GAP_MILLIS = 14L * 24 * 60 * 60 * 1000

    fun shouldShow(favorites: Int, shown: Int, lastShown: Long, now: Long, locked: Boolean): Boolean {
        if (!locked || shown >= MAX_TIMES) return false
        return when (shown) {
            0 -> favorites >= FIRST_AT
            else -> favorites >= SECOND_AT && now - lastShown >= GAP_MILLIS
        }
    }

    /** Se llama justo después de guardar una favorita. */
    fun afterSaving(activity: Activity, changed: () -> Unit) {
        val prefs = activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val shown = prefs.getInt(SHOWN, 0)
        val now = System.currentTimeMillis()
        val locked = !Premium.alertsUnlocked(activity)
        if (!shouldShow(FavoritesStore.list(activity).size, shown, prefs.getLong(LAST, 0L), now, locked)) return
        prefs.edit().putInt(SHOWN, shown + 1).putLong(LAST, now).apply()
        AlertDialog.Builder(activity)
            .setTitle("¿Te avisamos cuando salga algo así?")
            .setMessage(MESSAGE)
            .setPositiveButton("Ver Premium") { _, _ -> PremiumDialog.show(activity, changed) }
            .setNegativeButton("Ahora no", null)
            .show()
    }

    const val MESSAGE =
        "Con OpoAlert Premium creas alertas por puesto y provincia, y te avisamos en cuanto se " +
            "publique una convocatoria que te interese. Además, quitas la publicidad.\n\n" +
            "Puedes probarlo gratis. Con tu suscripción ayudas a mantener OpoAlert, un proyecto " +
            "independiente, y a seguir añadiendo boletines."
}
