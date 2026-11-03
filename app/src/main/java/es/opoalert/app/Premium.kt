package es.opoalert.app

import android.content.Context
import android.content.pm.ApplicationInfo
import java.security.MessageDigest

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
    /** Activado con el código de los revisores de Google Play; la compra no lo toca. */
    private const val REVIEWER = "premium_reviewer_v1"

    fun isActive(context: Context): Boolean {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return prefs.getBoolean(ACTIVE, false) || prefs.getBoolean(REVIEWER, false)
    }

    val acceptsReviewCode: Boolean get() = BuildConfig.REVIEW_CODE_SHA256.isNotEmpty()

    /** Código para que Google Play pueda revisar las alertas sin pagar (solo lo tiene Google). */
    fun redeemReviewCode(context: Context, code: String): Boolean {
        if (!reviewCodeMatches(code, BuildConfig.REVIEW_CODE_SHA256)) return false
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putBoolean(REVIEWER, true).apply()
        return true
    }

    /** Separado para poder probarlo sin Android. */
    fun reviewCodeMatches(code: String, expectedSha256: String): Boolean {
        if (expectedSha256.isEmpty()) return false
        val normalized = code.trim().uppercase().replace(" ", "")
        val digest = MessageDigest.getInstance("SHA-256").digest(normalized.toByteArray())
        val hex = digest.joinToString("") { "%02x".format(it) }
        return MessageDigest.isEqual(hex.toByteArray(), expectedSha256.lowercase().toByteArray())
    }

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
