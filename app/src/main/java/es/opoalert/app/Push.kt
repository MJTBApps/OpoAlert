package es.opoalert.app

import android.content.Context
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.google.firebase.messaging.FirebaseMessaging
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

/**
 * Aviso silencioso desde GitHub (1.54.0). Cuando se publican convocatorias nuevas,
 * `backend/aviso_fcm.py` manda un mensaje al tema «convocatorias» que solo dice
 * «hay datos nuevos». El móvil descarga los feeds y compara con sus alertas:
 * las alertas nunca salen del teléfono. Sin datos de Firebase no hace nada y
 * queda la revisión periódica de [BopWorker].
 */
object Push {
    const val TOPIC = "convocatorias"

    fun configured(): Boolean = listOf(
        BuildConfig.FCM_APP_ID, BuildConfig.FCM_API_KEY, BuildConfig.FCM_PROJECT_ID, BuildConfig.FCM_SENDER_ID
    ).none { it.isBlank() }

    fun start(context: Context) {
        if (!configured()) return
        try {
            ensureApp(context)
            FirebaseMessaging.getInstance().subscribeToTopic(TOPIC)
        } catch (_: Exception) {
            // Sin servicios de Google Play: sigue la revisión periódica.
        }
    }

    fun ensureApp(context: Context) {
        if (FirebaseApp.getApps(context).isNotEmpty()) return
        val options = FirebaseOptions.Builder()
            .setApplicationId(BuildConfig.FCM_APP_ID)
            .setApiKey(BuildConfig.FCM_API_KEY)
            .setProjectId(BuildConfig.FCM_PROJECT_ID)
            .setGcmSenderId(BuildConfig.FCM_SENDER_ID)
            .build()
        FirebaseApp.initializeApp(context.applicationContext, options)
    }
}

class OpoAlertMessagingService : FirebaseMessagingService() {
    override fun onCreate() {
        if (Push.configured()) Push.ensureApp(this)
        super.onCreate()
    }

    override fun onMessageReceived(message: RemoteMessage) {
        if (message.data["tipo"] == "feeds") BopWorker.runNow(applicationContext)
    }

    override fun onNewToken(token: String) {
        // Se usa un tema, no hace falta guardar el token en ningún servidor.
    }
}
