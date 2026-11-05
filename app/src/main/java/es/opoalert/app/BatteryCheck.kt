package es.opoalert.app

import android.app.ActivityManager
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import android.provider.Settings

/**
 * Las alertas se revisan en segundo plano y Android las retrasa o las para si
 * limita la batería de la app (sobre todo en Xiaomi, Samsung, Huawei…). Una app
 * no puede quitarse ese límite sola: se le pide al usuario y se le lleva a la
 * pantalla de ajustes. No usa REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, que Google
 * Play solo admite en algunos tipos de app.
 */
object BatteryCheck {
    private const val PREFS = "opoalert_store"
    private const val ASKED = "battery_prompt_shown_v1"
    private const val DISMISSED = "battery_warning_dismissed_v1"

    /** «Restringida» en los ajustes: Android no deja ejecutar nada en segundo plano. */
    fun restricted(ctx: Context): Boolean =
        Build.VERSION.SDK_INT >= 28 &&
            (ctx.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager).isBackgroundRestricted

    /** «Optimizada» (lo normal al instalar): Android puede retrasar las revisiones. */
    fun optimized(ctx: Context): Boolean =
        !(ctx.getSystemService(Context.POWER_SERVICE) as PowerManager)
            .isIgnoringBatteryOptimizations(ctx.packageName)

    /** El aviso de «Mis alertas»: siempre si está restringida; si solo está optimizada, hasta que lo descarte. */
    fun shouldWarn(ctx: Context): Boolean =
        restricted(ctx) || (optimized(ctx) && !prefs(ctx).getBoolean(DISMISSED, false))

    fun dismiss(ctx: Context) = prefs(ctx).edit().putBoolean(DISMISSED, true).apply()

    /** Pantalla de la app en los ajustes de Android, donde está «Batería». */
    fun openSettings(ctx: Context) {
        ctx.startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
            Uri.fromParts("package", ctx.packageName, null)))
    }

    /** Tras guardar la primera alerta, se explica una sola vez. */
    fun askOnce(ctx: Context) {
        val p = prefs(ctx)
        if (p.getBoolean(ASKED, false) || !(restricted(ctx) || optimized(ctx))) return
        p.edit().putBoolean(ASKED, true).apply()
        AlertDialog.Builder(ctx)
            .setTitle("Para que las alertas te avisen")
            .setMessage(
                "OpoAlert revisa tus alertas en segundo plano. Si Android limita su batería, " +
                    "los avisos pueden llegar tarde o solo al abrir la app.\n\n" +
                    "En Ajustes, entra en «Batería» y elige «Sin restricciones»."
            )
            .setPositiveButton("Abrir ajustes") { _, _ -> openSettings(ctx) }
            .setNegativeButton("Ahora no", null)
            .show()
    }

    private fun prefs(ctx: Context) = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
}
