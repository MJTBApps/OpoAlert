package es.opoalert.app

import android.app.Activity
import android.app.AlertDialog
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast

/**
 * Gestión de alertas: sin registro, sin permisos de ubicación y sin ocupar
 * espacio en la portada de convocatorias.
 */
class AlertsActivity : Activity() {
    private lateinit var list: LinearLayout
    private lateinit var count: TextView
    private lateinit var addButton: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = GradientDrawable().apply { setColor(Color.parseColor("#F6F8FC")) }
        }
        val top = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(14), dp(9), dp(18), dp(10))
        }
        val back = text("‹", 34f, "#1E4FD5").apply {
            gravity = Gravity.CENTER
            minWidth = dp(45)
            minHeight = dp(46)
            isClickable = true
            isFocusable = true
            contentDescription = "Volver a convocatorias"
            setOnClickListener { finish() }
        }
        top.addView(back)
        val heading = text("Mis alertas", 23f, "#101D36", bold = true)
        top.addView(heading, LinearLayout.LayoutParams(0, -2, 1f))
        count = text("", 12f, "#64748B")
        top.addView(count)
        root.addView(top)

        val scroll = ScrollView(this).apply { isFillViewport = true }
        val body = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(7), dp(18), dp(24))
        }
        body.addView(text(
            "Recibe avisos únicamente cuando aparezcan anuncios nuevos que coincidan " +
                "con tus puestos o palabras clave. Las tildes y mayúsculas no importan.",
            13f, "#45546C"
        ).apply { setPadding(0, 0, 0, dp(15)) })

        addButton = text("＋  Crear nueva alerta", 15f, "#FFFFFF", true).apply {
            gravity = Gravity.CENTER
            minHeight = dp(48)
            background = rounded("#1E4FD5", 13)
            isClickable = true
            isFocusable = true
            setOnClickListener {
                if (AlertRuleStore.list(this@AlertsActivity).size >= AlertRuleStore.MAX_RULES)
                    Toast.makeText(this@AlertsActivity, "Puedes guardar hasta 20 alertas.", Toast.LENGTH_LONG).show()
                else editRule(null)
            }
        }
        body.addView(addButton, LinearLayout.LayoutParams(-1, dp(48)).apply {
            bottomMargin = dp(15)
        })

        list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        body.addView(list)
        body.addView(text(
            "Las alertas se guardan en este móvil. Si dejas de seguir un boletín " +
                "en la pantalla principal, no recibirás avisos de esa fuente. " +
                "Solo se avisa de anuncios nuevos detectados después de configurar la alerta.",
            11f, "#64748B"
        ).apply { setPadding(dp(3), dp(16), dp(3), 0) })
        scroll.addView(body)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
        render()
    }

    private fun render() {
        list.removeAllViews()
        val rules = AlertRuleStore.list(this)
        count.text = rules.count { it.enabled }.toString() + " activas"
        if (rules.isEmpty()) {
            val empty = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                background = rounded("#FFFFFF", 15, "#DEE5EF")
                setPadding(dp(17), dp(24), dp(17), dp(24))
            }
            empty.addView(text("Todavía no tienes alertas", 16f, "#1C2A43", true))
            empty.addView(text(
                "Pulsa «Crear nueva alerta» y escribe, por ejemplo, policía local, " +
                    "auxiliar administrativo o enfermería. Sin alertas guardadas no " +
                    "se enviarán avisos de convocatorias.",
                13f, "#64748B"
            ).apply { setPadding(0, dp(8), 0, 0) })
            list.addView(empty)
            return
        }
        for (rule in rules) {
            val card = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(15), dp(13), dp(15), dp(12))
                background = rounded("#FFFFFF", 14, "#DEE5EF")
            }
            val first = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }
            first.addView(text(rule.phrase, 16f, "#17243C", true),
                LinearLayout.LayoutParams(0, -2, 1f))
            val toggle = Switch(this).apply {
                isChecked = rule.enabled
                text = ""
                contentDescription = "Activar o pausar " + rule.phrase
                setOnCheckedChangeListener { _, enabled ->
                    try {
                        AlertRuleStore.enable(this@AlertsActivity, rule.id, enabled)
                        render()
                    } catch (error: Exception) {
                        Toast.makeText(this@AlertsActivity, "No se pudo cambiar la alerta.", Toast.LENGTH_LONG).show()
                        render()
                    }
                }
            }
            first.addView(toggle)
            card.addView(first)
            card.addView(text(
                Province.entries.filter { it in rule.provinces }
                    .joinToString(" · ") { it.label },
                12f, "#64748B"
            ).apply { setPadding(0, dp(6), 0, dp(8)) })
            val actions = LinearLayout(this).apply {
                gravity = Gravity.END or Gravity.CENTER_VERTICAL
                orientation = LinearLayout.HORIZONTAL
            }
            actions.addView(action("Editar") { editRule(rule) })
            actions.addView(action("Eliminar") { confirmDelete(rule) }.apply {
                setTextColor(Color.parseColor("#B42318"))
            }, LinearLayout.LayoutParams(-2, dp(36)).apply { leftMargin = dp(10) })
            card.addView(actions)
            list.addView(card, LinearLayout.LayoutParams(-1, -2).apply {
                bottomMargin = dp(10)
            })
        }
    }

    private fun editRule(existing: AlertRule?) {
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(22), dp(10), dp(22), dp(4))
        }
        content.addView(text("Palabra clave o puesto", 13f, "#34435B", true))
        val input = EditText(this).apply {
            setSingleLine(true)
            textSize = 15f
            hint = "Ej.: policía local"
            setText(existing?.phrase ?: "")
            selectAll()
        }
        content.addView(input, LinearLayout.LayoutParams(-1, dp(52)))
        content.addView(text("Boletines para esta alerta", 13f, "#34435B", true).apply {
            setPadding(0, dp(13), 0, dp(4))
        })
        val initial = existing?.provinces ?: ProvinceSettings.selected(this)
        val checks = SourceCatalog.availableSources.map { province ->
            CheckBox(this).apply {
                text = province.label
                textSize = 14f
                isChecked = province in initial
                setTextColor(Color.parseColor("#17243C"))
            }.also { content.addView(it) }
        }
        content.addView(text(
            "Solo recibirás avisos de los boletines que también hayas seleccionado en Explorar.",
            11f, "#64748B"
        ).apply { setPadding(0, dp(12), 0, 0) })
        val dialog = AlertDialog.Builder(this)
            .setTitle(if (existing == null) "Nueva alerta" else "Editar alerta")
            .setView(content)
            .setPositiveButton("Guardar", null)
            .setNegativeButton("Cancelar", null)
            .create()
        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val selected = SourceCatalog.availableSources.filterIndexed { i, _ -> checks[i].isChecked }.toSet()
                try {
                    AlertRuleStore.upsert(this, existing?.id, input.text.toString(), selected)
                    dialog.dismiss()
                    render()
                } catch (error: IllegalArgumentException) {
                    Toast.makeText(this, error.message ?: "Revisa los datos.", Toast.LENGTH_LONG).show()
                } catch (error: Exception) {
                    Toast.makeText(this, "No se pudo guardar la alerta.", Toast.LENGTH_LONG).show()
                }
            }
        }
        dialog.show()
    }

    private fun confirmDelete(rule: AlertRule) {
        AlertDialog.Builder(this)
            .setTitle("Eliminar alerta")
            .setMessage("¿Eliminar la alerta «" + rule.phrase + "»?")
            .setPositiveButton("Eliminar") { _, _ ->
                try {
                    AlertRuleStore.remove(this, rule.id)
                    render()
                } catch (error: Exception) {
                    Toast.makeText(this, "No se pudo eliminar.", Toast.LENGTH_LONG).show()
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun action(label: String, callback: () -> Unit): TextView =
        text(label, 13f, "#1E4FD5", true).apply {
            gravity = Gravity.CENTER
            setPadding(dp(9), 0, dp(9), 0)
            minHeight = dp(36)
            isClickable = true
            isFocusable = true
            setOnClickListener { callback() }
        }

    private fun text(value: String, size: Float, color: String, bold: Boolean = false): TextView =
        TextView(this).apply {
            text = value
            textSize = size
            includeFontPadding = false
            setTextColor(Color.parseColor(color))
            if (bold) typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
        }

    private fun rounded(color: String, radius: Int, stroke: String? = null) =
        GradientDrawable().apply {
            cornerRadius = dp(radius).toFloat()
            setColor(Color.parseColor(color))
            if (stroke != null) setStroke(dp(1), Color.parseColor(stroke))
        }

    private fun dp(v: Int): Int = (v * resources.displayMetrics.density + 0.5f).toInt()
}
