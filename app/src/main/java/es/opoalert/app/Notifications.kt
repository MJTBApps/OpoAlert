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
    // Canal de importancia alta (sonido y ventana emergente). Android no deja subir
    // la importancia de un canal ya creado, así que el antiguo (normal: sin ventana
    // y, en algunas marcas, sin sonido) se sustituye por uno nuevo (1.50.0).
    const val CHANNEL = "alertas_convocatorias"
    private const val OLD_CHANNEL = "bop_new_jobs"

    fun createChannel(context: Context) {
        val channel = NotificationChannel(
            CHANNEL, "Alertas de convocatorias", NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Avisos de nuevos anuncios que coincidan con tus alertas"
        }
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.deleteNotificationChannel(OLD_CHANNEL)
        manager.createNotificationChannel(channel)
    }

    fun show(context: Context, notices: List<Notice>) {
        if (notices.isEmpty() || !Repository.alertsEnabled(context) || !Premium.alertsUnlocked(context)) return
        // Segunda comprobacion: si el usuario pausa o elimina una regla durante
        // la sincronizacion, no debe llegar una notificacion de ella.
        val matching = SmartAlertMatcher.matching(
            notices, AlertRuleStore.list(context), Repository.watched(context)
        )
        if (matching.isEmpty()) return
        if (Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(
                context, Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED
        ) return
        createChannel(context)
        // Un identificador por aviso: con uno fijo, el aviso siguiente borraba el anterior
        // sin que se hubiera leído (1.54.1). También distingue los PendingIntent.
        val id = notificationId(matching.first().id)
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            // La lista se abre con el filtro «Avisos»: ahí están todas las del aviso.
            putExtra(MainActivity.EXTRA_OPEN_FILTER, MainActivity.FILTER_ALERTS)
        }
        // Con un solo anuncio, el aviso abre su ficha; «atrás» vuelve a la lista.
        val pending = if (matching.size == 1) {
            val detail = Intent(context, NoticeDetailActivity::class.java)
                .putExtra(NoticeDetailActivity.EXTRA_NOTICE, matching.first().toJson().toString())
            TaskStackBuilder.create(context).addNextIntent(intent).addNextIntent(detail)
                .getPendingIntent(id, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        } else PendingIntent.getActivity(
            context, id, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
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
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()
        NotificationManagerCompat.from(context).notify(id, notification)
    }

    /**
     * «Posible novedad en tu favorita» (seguimiento, 1.59.0, Premium). Un aviso por favorita,
     * con su propio identificador; tocarlo abre la ficha de la favorita con la línea de tiempo.
     */
    fun showFollowUps(context: Context, followUps: List<Pair<Notice, FollowUpItem>>) {
        if (followUps.isEmpty() || !Premium.alertsUnlocked(context)) return
        if (Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(
                context, Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED
        ) return
        createChannel(context)
        // Se vuelve a mirar: si se quitó la favorita o se contestó «No» mientras se buscaba, no se avisa.
        val favorites = FavoritesStore.list(context).associateBy { it.id }
        for ((favoriteId, items) in followUps.groupBy({ it.first.id }, { it.second })) {
            val favorite = favorites[favoriteId] ?: continue
            val state = FollowUps.state(context, favoriteId)
            val live = items.filter { item -> state.items.any { it.notice.id == item.notice.id && it.state != FollowUpItem.NO } }
            if (live.isEmpty()) continue
            val id = followUpNotificationId(favoriteId)
            val main = Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                putExtra(MainActivity.EXTRA_OPEN_TAB, MainActivity.TAB_FAVORITES)
            }
            val detail = Intent(context, NoticeDetailActivity::class.java)
                .putExtra(NoticeDetailActivity.EXTRA_NOTICE, favorite.toJson().toString())
            val pending = TaskStackBuilder.create(context).addNextIntent(main).addNextIntent(detail)
                .getPendingIntent(id, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val step = live.first().step + " · " + live.first().notice.date
            val body = if (live.size == 1) step else "${live.size} posibles novedades · $step"
            val notification = NotificationCompat.Builder(context, CHANNEL)
                .setSmallIcon(R.drawable.ic_notification)
                .setContentTitle("Posible novedad en tu favorita")
                .setContentText(body)
                .setStyle(NotificationCompat.BigTextStyle().bigText(
                    body + "\n" + NoticeText.headline(favorite.title).take(140) +
                        "\nComprueba siempre el anuncio oficial."))
                .setAutoCancel(true)
                .setContentIntent(pending)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .build()
            NotificationManagerCompat.from(context).notify(id, notification)
        }
    }

    /** Distinto de los de las alertas: un aviso por favorita, que se actualiza si llega otra novedad. */
    fun followUpNotificationId(favoriteId: String): Int = notificationId("seguimiento:$favoriteId")

    /** Entre 1001 y 1 001 000, estable para el mismo anuncio. */
    fun notificationId(noticeId: String): Int = 1001 + (noticeId.hashCode() and 0x7fffffff) % 1_000_000
}
