package es.opoalert.app

import android.app.Activity
import android.app.AlertDialog
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import com.google.android.play.core.appupdate.AppUpdateManagerFactory
import com.google.android.play.core.install.model.UpdateAvailability

/**
 * Aviso de versión nueva en la versión de Google Play (1.57.0). Antes no había ninguno:
 * la de la web avisa con `AppUpdate` (version.json), que Google Play no permite.
 * Pregunta a Google Play si hay una versión más nueva para este móvil y, si la hay,
 * ofrece abrir su ficha. «Más tarde» lo calla 3 días para esa versión.
 */
object PlayUpdate {
    private const val PREFS = "opoalert_store"
    private const val LATER_CODE = "play_update_later_code_v1"
    private const val LATER_AT = "play_update_later_at_v1"
    const val SNOOZE_MS = 3L * 24 * 60 * 60 * 1000

    fun shouldOffer(available: Int, current: Long, snoozedCode: Int, snoozedAt: Long, now: Long): Boolean =
        available > current && !(snoozedCode == available && now - snoozedAt < SNOOZE_MS)

    fun check(activity: Activity) {
        if (BuildConfig.SELF_UPDATE) return
        val manager = try { AppUpdateManagerFactory.create(activity) } catch (_: Exception) { return }
        manager.appUpdateInfo.addOnSuccessListener { info ->
            if (activity.isFinishing || activity.isDestroyed) return@addOnSuccessListener
            if (info.updateAvailability() != UpdateAvailability.UPDATE_AVAILABLE) return@addOnSuccessListener
            val prefs = activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            val current = try {
                activity.packageManager.getPackageInfo(activity.packageName, 0).longVersionCode
            } catch (_: Exception) { return@addOnSuccessListener }
            val available = info.availableVersionCode()
            val now = System.currentTimeMillis()
            if (!shouldOffer(available, current, prefs.getInt(LATER_CODE, 0), prefs.getLong(LATER_AT, 0L), now))
                return@addOnSuccessListener
            AlertDialog.Builder(activity)
                .setTitle("Hay una versión nueva de OpoAlert")
                .setMessage("Actualiza desde Google Play para tener las últimas mejoras y correcciones. " +
                    "Conservas tus favoritas y alertas.")
                .setPositiveButton("Actualizar") { _, _ -> openStore(activity) }
                .setNegativeButton("Más tarde") { _, _ ->
                    prefs.edit().putInt(LATER_CODE, available).putLong(LATER_AT, now).apply()
                }
                .show()
        }
    }

    fun openStore(activity: Activity) {
        val id = activity.packageName
        try {
            activity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$id")))
        } catch (_: ActivityNotFoundException) {
            try {
                activity.startActivity(Intent(Intent.ACTION_VIEW,
                    Uri.parse("https://play.google.com/store/apps/details?id=$id")))
            } catch (_: ActivityNotFoundException) {
            }
        }
    }
}
