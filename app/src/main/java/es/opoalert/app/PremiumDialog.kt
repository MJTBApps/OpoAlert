package es.opoalert.app

import android.app.Activity
import android.app.AlertDialog
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.text.InputType
import android.widget.EditText
import android.widget.Toast

/** Pantalla de OpoAlert Premium: qué incluye, precio de Google Play y botón de compra. */
object PremiumDialog {
    private const val BENEFITS =
        "• Sin publicidad: ni al abrir la app ni entre las convocatorias.\n" +
            "• Alertas personalizadas: te avisamos cuando sale una convocatoria de tu puesto y provincia.\n" +
            "• Con tu suscripción ayudas a mantener OpoAlert, un proyecto independiente, y a seguir añadiendo boletines.\n\n"

    /** [changed] se llama si cambia el estado (para quitar anuncios o refrescar la pantalla). */
    fun show(activity: Activity, changed: () -> Unit) {
        if (!PlayBilling.enabled) return showWithoutBilling(activity, changed)
        if (Premium.isActive(activity)) {
            AlertDialog.Builder(activity)
                .setTitle("OpoAlert Premium ✓")
                .setMessage("Tienes OpoAlert Premium activo.\n\n" + BENEFITS +
                    "Puedes cancelar o cambiar la suscripción cuando quieras desde Google Play.")
                .setPositiveButton("Entendido", null)
                .setNeutralButton("Gestionar suscripción") { _, _ -> openSubscriptions(activity) }
                .show()
            return
        }
        val loading = Toast.makeText(activity, "Consultando Google Play…", Toast.LENGTH_SHORT)
        loading.show()
        PlayBilling.loadOffer(activity) { offer ->
            loading.cancel()
            if (activity.isFinishing || activity.isDestroyed) return@loadOffer
            if (offer == null) {
                AlertDialog.Builder(activity)
                    .setTitle("OpoAlert Premium")
                    .setMessage(BENEFITS + "Ahora no se puede consultar Google Play. Comprueba la conexión e inténtalo de nuevo.")
                    .setPositiveButton("Entendido", null)
                    .show()
                return@loadOffer
            }
            val trial = offer.trialDays?.let { "Pruébalo $it días gratis. Después, " } ?: ""
            AlertDialog.Builder(activity)
                .setTitle("OpoAlert Premium")
                .setMessage(BENEFITS + trial + offer.price + ". " +
                    "Se renueva automáticamente; puedes cancelarlo cuando quieras desde Google Play.")
                .setPositiveButton(if (offer.trialDays != null) "Probar gratis" else "Suscribirme") { _, _ ->
                    PlayBilling.refresh(activity, changed)
                    if (!PlayBilling.buy(activity, offer)) {
                        Toast.makeText(activity, "No se pudo abrir el pago de Google Play.", Toast.LENGTH_LONG).show()
                    }
                }
                .setNegativeButton("Ahora no", null)
                .setNeutralButton("Ya soy Premium") { _, _ -> showRestoreOptions(activity, changed) }
                .show()
        }
    }

    private fun showRestoreOptions(activity: Activity, changed: () -> Unit) {
        val restore = {
            PlayBilling.refresh(activity) {
                changed()
                Toast.makeText(activity, "Suscripción recuperada", Toast.LENGTH_SHORT).show()
            }
        }
        if (!Premium.acceptsReviewCode) return restore()
        AlertDialog.Builder(activity)
            .setTitle("Ya soy Premium")
            .setItems(arrayOf("Recuperar mi suscripción de Google Play", "Tengo un código")) { _, which ->
                if (which == 0) restore() else askReviewCode(activity, changed)
            }
            .show()
    }

    private fun askReviewCode(activity: Activity, changed: () -> Unit) {
        val input = EditText(activity).apply {
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS
            hint = "XXXXX-XXXXX-XXXXX-XXXXX"
        }
        AlertDialog.Builder(activity)
            .setTitle("Código de OpoAlert Premium")
            .setView(input)
            .setPositiveButton("Activar") { _, _ ->
                if (Premium.redeemReviewCode(activity, input.text.toString())) {
                    Toast.makeText(activity, "Premium activado", Toast.LENGTH_SHORT).show()
                    changed()
                } else {
                    Toast.makeText(activity, "El código no es válido", Toast.LENGTH_LONG).show()
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    /** Versión web (sin Google Play): Premium no se vende; en pruebas se puede simular. */
    private fun showWithoutBilling(activity: Activity, changed: () -> Unit) {
        val active = Premium.isActive(activity)
        val dialog = AlertDialog.Builder(activity)
            .setTitle("OpoAlert Premium")
            .setMessage((if (active) "Tienes OpoAlert Premium activo.\n\n" else "") + BENEFITS +
                "La suscripción se contrata en la versión de Google Play. En esta versión las alertas son gratuitas.")
            .setPositiveButton("Entendido", null)
        if (Premium.canSimulate(activity)) {
            dialog.setNeutralButton(if (active) "Desactivar (pruebas)" else "Activar (pruebas)") { _, _ ->
                Premium.setActive(activity, !active)
                Toast.makeText(activity, if (active) "Premium desactivado" else "Premium activado: sin anuncios",
                    Toast.LENGTH_SHORT).show()
                changed()
            }
        }
        dialog.show()
    }

    private fun openSubscriptions(activity: Activity) {
        val url = "https://play.google.com/store/account/subscriptions?sku=${PlayBilling.PRODUCT_ID}" +
            "&package=${activity.packageName}"
        try {
            activity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(activity, "Abre Google Play → Pagos y suscripciones.", Toast.LENGTH_LONG).show()
        }
    }
}
