package es.opoalert.app

import android.app.Activity
import android.content.Context
import com.google.android.play.core.review.ReviewManagerFactory
import java.time.LocalDate

/**
 * Valoración en Google Play sin salir de la app (1.57.0). Se pide solo a quien ya la usa:
 * al volver a la lista tras ver una ficha, si ha abierto al menos 5 fichas, ha usado la app
 * 3 días distintos y la instaló hace 3 días o más. Como mucho 3 veces y con 4 meses entre
 * una y otra. Google decide si muestra la ventana (tiene su propio límite) y no dice si
 * se ha valorado: por eso no se insiste.
 */
object ReviewPrompt {
    private const val PREFS = "opoalert_store"
    private const val OPENED = "review_opened_v1"
    private const val DAYS = "review_days_v1"
    private const val LAST = "review_last_v1"
    private const val COUNT = "review_count_v1"
    const val MIN_OPENED = 5
    const val MIN_DAYS = 3
    const val MIN_INSTALLED_DAYS = 3L
    const val MAX_TIMES = 3
    const val GAP_DAYS = 120L

    /** Se llama al abrir una ficha. */
    fun noticeOpened(context: Context) {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val days = prefs.getStringSet(DAYS, emptySet()).orEmpty().toMutableSet()
        days.add(LocalDate.now().toString())
        // Basta saber si llega a MIN_DAYS: no hace falta guardar más días.
        val kept = days.sortedDescending().take(10).toSet()
        prefs.edit().putInt(OPENED, prefs.getInt(OPENED, 0) + 1).putStringSet(DAYS, kept).apply()
    }

    fun shouldAsk(opened: Int, days: Int, installedDays: Long, times: Int, daysSinceLast: Long): Boolean =
        opened >= MIN_OPENED && days >= MIN_DAYS && installedDays >= MIN_INSTALLED_DAYS &&
            times < MAX_TIMES && (times == 0 || daysSinceLast >= GAP_DAYS)

    fun maybeAsk(activity: Activity) {
        if (!BuildConfig.BILLING) return  // la valoración es de Google Play; la APK de la web no está allí
        val prefs = activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val today = LocalDate.now().toEpochDay()
        val installed = try {
            activity.packageManager.getPackageInfo(activity.packageName, 0).firstInstallTime
        } catch (_: Exception) {
            return
        }
        val installedDays = (System.currentTimeMillis() - installed) / 86_400_000L
        val times = prefs.getInt(COUNT, 0)
        if (!shouldAsk(prefs.getInt(OPENED, 0), prefs.getStringSet(DAYS, emptySet()).orEmpty().size,
                installedDays, times, today - prefs.getLong(LAST, 0L))) return
        prefs.edit().putInt(COUNT, times + 1).putLong(LAST, today).apply()
        val manager = ReviewManagerFactory.create(activity)
        manager.requestReviewFlow().addOnCompleteListener { request ->
            if (request.isSuccessful && !activity.isFinishing && !activity.isDestroyed) {
                manager.launchReviewFlow(activity, request.result)
            }
        }
    }
}
