package es.opoalert.app

import android.content.Context
import android.content.pm.ApplicationInfo

/**
 * OpoAlert Premium: sin publicidad y con las alertas desbloqueadas.
 *
 * Todavía no hay pago: Google Play Billing solo funciona con la app publicada en
 * Google Play. Mientras BILLING_READY sea false, las alertas siguen siendo gratis
 * para todos y Premium solo se puede activar en compilaciones de prueba.
 */
object Premium {
    /** Pasar a true cuando la compra funcione en Google Play: entonces las alertas pasan a Premium. */
    const val BILLING_READY = false

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
