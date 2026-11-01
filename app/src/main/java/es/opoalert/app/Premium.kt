package es.opoalert.app

import android.content.Context
import android.content.pm.ApplicationInfo

/**
 * OpoAlert Premium: sin publicidad y con las alertas desbloqueadas.
 *
 * El pago es con Google Play Billing (PlayBilling.kt) y solo existe en la versión de
 * Google Play. En la versión web no hay cobro: las alertas son gratis y Premium solo
 * se puede activar en compilaciones de prueba.
 */
object Premium {
    /** Con pago (versión de Google Play) las alertas son de Premium; sin pago, gratis. */
    val BILLING_READY: Boolean get() = BuildConfig.BILLING

    private const val PREFS = "opoalert_store"
    private const val ACTIVE = "premium_active_v1"

    fun isActive(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(ACTIVE, false)

    /** Sin pago todavía: solo lo usan las compilaciones de prueba y, más adelante, la compra. */
    fun setActive(context: Context, active: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putBoolean(ACTIVE, active).apply()
    }

    fun showsAds(context: Context): Boolean = !isActive(context)

    fun alertsUnlocked(context: Context): Boolean = unlocked(isActive(context), BILLING_READY)

    /** Separado para poder probarlo sin Android. */
    fun unlocked(premium: Boolean, billingReady: Boolean): Boolean = premium || !billingReady

    fun canSimulate(context: Context): Boolean =
        context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE != 0
}
