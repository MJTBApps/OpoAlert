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
import androidx.core.content.ContextCompat

object Notifications {
    const val CHANNEL = "bop_new_jobs"

    fun createChannel(context: Context) {
        val channel = NotificationChannel(
            CHANNEL, "Nuevas convocatorias", NotificationManager.IMPORTANCE_DEFAULT
        ).apply {
            description = "Avisos cuando se detectan nuevas plazas o bolsas en el BOP de Valencia"
        }
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(channel)
    }

    fun show(context: Context, notices: List<Notice>) {
        if (notices.isEmpty() || !Repository.alertsEnabled(context)) return
        if (Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(
                context, Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED
        ) return
        createChannel(context)
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pending = PendingIntent.getActivity(
            context, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val title = if (notices.size == 1) "Nueva convocatoria en el BOP" else
            "${notices.size} nuevas convocatorias en el BOP"
        val body = if (notices.size == 1) notices[0].entity else
            notices.take(3).joinToString(" · ") { it.entity }
        val notification = NotificationCompat.Builder(context, CHANNEL)
            .setSmallIcon(R.drawable.ic_opoalert)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setAutoCancel(true)
            .setContentIntent(pending)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .build()
        NotificationManagerCompat.from(context).notify(1001, notification)
    }
}
