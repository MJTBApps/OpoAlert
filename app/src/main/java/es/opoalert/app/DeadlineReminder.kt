package es.opoalert.app

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.TaskStackBuilder
import androidx.core.content.ContextCompat
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import java.time.LocalDate
import java.time.ZoneId
import java.util.concurrent.TimeUnit

/**
 * Recordatorio de fin de plazo de una favorita (Premium, 1.57.0). Se programa para las 9:00
 * dos días antes de la fecha orientativa (o ese mismo día si ya queda menos). La fecha es
 * «como pronto»: el aviso nunca llega tarde, como mucho antes de tiempo.
 */
object DeadlineReminder {
    const val CHANNEL = "recordatorios_plazo"
    private const val DAYS_BEFORE = 2L
    private const val HOUR = 9

    private fun work(id: String) = "plazo_" + id

    /** Cuándo avisar, o null si ya no tiene sentido (plazo pasado). Separado para las pruebas. */
    fun remindDay(until: LocalDate, today: LocalDate): LocalDate? = when {
        until.isBefore(today) -> null
        until.minusDays(DAYS_BEFORE).isAfter(today) -> until.minusDays(DAYS_BEFORE)
        else -> today
    }

    fun eligible(context: Context, entry: AgendaEntry): Boolean =
        entry.until != null && !entry.submitted && Premium.alertsUnlocked(context)

    /** Programa o anula el aviso según el estado actual de la favorita. */
    fun sync(context: Context, notice: Notice) {
        val entry = FavoriteAgenda.get(context, notice.id)
        val manager = WorkManager.getInstance(context)
        val until = entry.until
        if (!FavoritesStore.contains(context, notice.id) || !eligible(context, entry) || until == null) {
            manager.cancelUniqueWork(work(notice.id))
            return
        }
        val zone = ZoneId.of("Europe/Madrid")
        val day = remindDay(until, LocalDate.now(zone))
        if (day == null) {
            manager.cancelUniqueWork(work(notice.id))
            return
        }
        val at = day.atTime(HOUR, 0).atZone(zone).toInstant().toEpochMilli()
        val delay = (at - System.currentTimeMillis()).coerceAtLeast(0L)
        val request = OneTimeWorkRequestBuilder<ReminderWorker>()
            .setInitialDelay(delay, TimeUnit.MILLISECONDS)
            .setInputData(workDataOf("notice" to notice.toJson().toString()))
            .build()
        manager.enqueueUniqueWork(work(notice.id), ExistingWorkPolicy.REPLACE, request)
    }

    fun cancel(context: Context, id: String) {
        WorkManager.getInstance(context).cancelUniqueWork(work(id))
    }

    /** Día en que llegará el aviso, para enseñarlo en la ficha (null si no hay aviso). */
    fun plannedDay(context: Context, notice: Notice): LocalDate? {
        val entry = FavoriteAgenda.get(context, notice.id)
        if (!FavoritesStore.contains(context, notice.id) || !eligible(context, entry)) return null
        return remindDay(entry.until ?: return null, LocalDate.now(ZoneId.of("Europe/Madrid")))
    }

    fun show(context: Context, notice: Notice) {
        val entry = FavoriteAgenda.get(context, notice.id)
        val until = entry.until ?: return
        if (!FavoritesStore.contains(context, notice.id) || !eligible(context, entry)) return
        if (Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(
                context, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(NotificationChannel(
            CHANNEL, "Recordatorios de plazo", NotificationManager.IMPORTANCE_HIGH
        ).apply { description = "Aviso antes de que acabe el plazo de una favorita" })
        val id = Notifications.notificationId("plazo-" + notice.id)
        val list = Intent(context, MainActivity::class.java).addFlags(
            Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        val detail = Intent(context, NoticeDetailActivity::class.java)
            .putExtra(NoticeDetailActivity.EXTRA_NOTICE, notice.toJson().toString())
        val pending = TaskStackBuilder.create(context).addNextIntent(list).addNextIntent(detail)
            .getPendingIntent(id, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val body = "Según el anuncio, el plazo acaba como pronto el " + FavoriteAgenda.longDay(until) +
            ". Compruébalo en el anuncio oficial."
        val notification = NotificationCompat.Builder(context, CHANNEL)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle("⏱ Se acaba el plazo: " + NoticeText.headline(notice.title).take(60))
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(
                NoticeText.headline(notice.title) + "\n" + body))
            .setContentIntent(pending)
            .setAutoCancel(true)
            .build()
        try {
            NotificationManagerCompat.from(context).notify(id, notification)
        } catch (_: SecurityException) {
        }
    }
}

class ReminderWorker(context: Context, params: WorkerParameters) : Worker(context, params) {
    override fun doWork(): Result {
        val raw = inputData.getString("notice") ?: return Result.success()
        val notice = try { Notice.fromJson(org.json.JSONObject(raw)) } catch (_: Exception) { return Result.success() }
        DeadlineReminder.show(applicationContext, notice)
        return Result.success()
    }
}
