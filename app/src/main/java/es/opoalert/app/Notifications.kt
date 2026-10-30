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

object Notifications {
    const val CHANNEL = "bop_new_jobs"

    fun createChannel(context: Context) {
        val channel = NotificationChannel(
            CHANNEL, "Nuevas convocatorias", NotificationManager.IMPORTANCE_DEFAULT
        ).apply {
            description = "Avisos de nuevos anuncios que coincidan con tus alertas y provincias"
        }
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(channel)
    }

    fun show(context: Context, notices: List<Notice>) {
        if (notices.isEmpty() || !Repository.alertsEnabled(context)) return
        // Segunda comprobacion: si el usuario pausa o elimina una regla durante
        // la sincronizacion, no debe llegar una notificacion de ella.
        val matching = SmartAlertMatcher.matching(
            notices, AlertRuleStore.list(context), ProvinceSettings.selected(context)
        )
        if (matching.isEmpty()) return
        if (Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(
                context, Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED
        ) return
        createChannel(context)
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        // Con un solo anuncio, el aviso abre su ficha; «atrás» vuelve a la lista.
        val pending = if (matching.size == 1) {
            val detail = Intent(context, NoticeDetailActivity::class.java)
                .putExtra(NoticeDetailActivity.EXTRA_NOTICE, matching.first().toJson().toString())
            TaskStackBuilder.create(context).addNextIntent(intent).addNextIntent(detail)
                .getPendingIntent(1, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        } else PendingIntent.getActivity(
            context, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val title = if (matching.size == 1) "Nueva convocatoria para tus alertas"
            else "${matching.size} convocatorias para tus alertas"
        val lines = matching.take(5).map {
            NoticeText.headline(it.title).take(76) + " · " + it.province
        }
        val body = lines.first()
        val inbox = NotificationCompat.InboxStyle()
        for (line in lines) inbox.addLine(line)
        if (matching.size > lines.size) {
            inbox.setSummaryText("+ " + (matching.size - lines.size) + " anuncios más")
        }
        val notification = NotificationCompat.Builder(context, CHANNEL)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(inbox)
            .setAutoCancel(true)
            .setContentIntent(pending)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .build()
        NotificationManagerCompat.from(context).notify(1001, notification)
    }
}
