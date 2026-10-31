package es.opoalert.app

import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/**
 * Lista jerárquica de boletines: BOE y, debajo, comunidad autónoma > provincia > fuente.
 * Las comunidades se despliegan bajo demanda. La usan «Elegir boletines» y el editor
 * de alertas, para que las dos pantallas sean iguales. Modifica `selected` en el sitio;
 * quien la usa decide si guarda (Cancelar no guarda nada).
 */
object SourcePicker {
    fun build(context: Context, selected: MutableSet<Province>): LinearLayout {
        fun dp(value: Int) = (value * context.resources.displayMetrics.density + 0.5f).toInt()
        fun rounded(fill: String, corner: Int) = GradientDrawable().apply {
            cornerRadius = dp(corner).toFloat()
            setColor(Color.parseColor(fill))
        }

        val container = LinearLayout(context).apply { orientation = LinearLayout.VERTICAL }
        container.addView(CheckBox(context).apply {
            text = "BOE · Toda España"
            textSize = 14f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#183B85"))
            isChecked = Province.BOE in selected
            setOnCheckedChangeListener { _, checked ->
                if (checked) selected.add(Province.BOE) else selected.remove(Province.BOE)
            }
        })

        for (community in SourceCatalog.groups()) {
            val groupSources = community.territories.flatMap { it.sources }
            val section = LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(0, dp(6), 0, dp(3))
            }
            val head = LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                background = rounded("#EDF3FF", 12)
                setPadding(dp(9), dp(5), dp(7), dp(5))
            }
            val title = TextView(context).apply {
                textSize = 14f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.parseColor("#17439B"))
                setPadding(dp(4), dp(7), dp(3), dp(7))
                layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            }
            val allButton = TextView(context).apply {
                textSize = 11f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.parseColor("#2155BB"))
                gravity = Gravity.CENTER
                setPadding(dp(10), dp(10), dp(9), dp(10))
                contentDescription = "Seleccionar o desmarcar todas las fuentes de ${community.name}"
            }
            val inside = LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                visibility = if (groupSources.any { it in selected }) View.VISIBLE else View.GONE
                setPadding(dp(15), dp(6), dp(1), dp(4))
            }
            fun updateTitle() {
                val amount = groupSources.count { it in selected }
                title.text = "${if (inside.visibility == View.VISIBLE) "▾" else "▸"} ${community.name}  ·  $amount/${groupSources.size}"
                allButton.text = if (amount == groupSources.size) "Ninguna" else "Todas"
            }
            val checks = ArrayList<CheckBox>()
            for (territory in community.territories) {
                inside.addView(TextView(context).apply {
                    text = territory.name
                    textSize = 13f
                    typeface = Typeface.DEFAULT_BOLD
                    setTextColor(Color.parseColor("#334763"))
                    setPadding(dp(5), dp(7), 0, dp(2))
                })
                for (source in territory.sources) {
                    val option = CheckBox(context).apply {
                        text = SourceCatalog.sourceName(source)
                        textSize = 13f
                        setTextColor(Color.parseColor("#263A57"))
                        isChecked = source in selected
                        setPadding(dp(5), 0, dp(3), 0)
                        setOnCheckedChangeListener { _, checked ->
                            if (checked) selected.add(source) else selected.remove(source)
                            updateTitle()
                        }
                    }
                    checks.add(option)
                    inside.addView(option)
                }
            }
            title.setOnClickListener {
                inside.visibility = if (inside.visibility == View.VISIBLE) View.GONE else View.VISIBLE
                updateTitle()
            }
            allButton.setOnClickListener {
                val enable = groupSources.any { it !in selected }
                checks.forEach { it.isChecked = enable }
                if (inside.visibility == View.GONE) inside.visibility = View.VISIBLE
                updateTitle()
            }
            updateTitle()
            head.addView(title)
            head.addView(allButton)
            section.addView(head)
            section.addView(inside)
            container.addView(section)
        }
        return container
    }

    /** Envuelve el contenido de un diálogo para que se pueda desplazar si no cabe. */
    fun scrolling(context: Context, content: View): ScrollView {
        val density = context.resources.displayMetrics.density
        return ScrollView(context).apply {
            addView(content)
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                minOf((485 * density).toInt(), (context.resources.displayMetrics.heightPixels * 0.61f).toInt())
            )
        }
    }
}
