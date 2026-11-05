package es.opoalert.app

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView

/** Barra de pestañas flotante de abajo, igual que la de la app de iPhone. */
object BottomTabs {
    const val EXPLORE = "all"
    const val FAVORITES = "favorites"
    const val ALERTS = "alerts"

    private val TABS = listOf(
        Triple(EXPLORE, "Explorar", R.drawable.ic_tab_explore),
        Triple(FAVORITES, "Favoritas", R.drawable.ic_tab_star),
        Triple(ALERTS, "Alertas", R.drawable.ic_tab_bell)
    )

    fun build(bar: LinearLayout, selected: String, onSelect: (String) -> Unit) {
        val context = bar.context
        fun dp(v: Int) = (v * context.resources.displayMetrics.density + 0.5f).toInt()
        bar.removeAllViews()
        bar.background = GradientDrawable().apply {
            setColor(Color.parseColor("#F7FFFFFF"))
            cornerRadius = dp(32).toFloat()
            setStroke(dp(1), Color.parseColor("#E1E6EE"))
        }
        for ((tab, label, icon) in TABS) {
            val active = tab == selected
            val tint = Color.parseColor(if (active) "#1E4FD5" else "#3B4659")
            val item = LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                gravity = Gravity.CENTER
                isClickable = true
                isFocusable = true
                contentDescription = label
                if (active) background = GradientDrawable().apply {
                    setColor(Color.parseColor("#E9EDF4"))
                    cornerRadius = dp(27).toFloat()
                }
                setOnClickListener { if (!active) onSelect(tab) }
            }
            item.addView(ImageView(context).apply {
                setImageResource(icon)
                setColorFilter(tint)
            }, LinearLayout.LayoutParams(dp(24), dp(24)))
            item.addView(TextView(context).apply {
                text = label
                textSize = 11.5f
                typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
                setTextColor(tint)
                gravity = Gravity.CENTER
            })
            bar.addView(item, LinearLayout.LayoutParams(0, -1, 1f))
        }
    }

    /** Desde otra pantalla (Mis alertas): vuelve a la lista con esa pestaña, sin animación. */
    fun openMain(activity: Activity, tab: String) {
        activity.startActivity(Intent(activity, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            .putExtra(MainActivity.EXTRA_OPEN_TAB, tab))
        activity.finish()
        @Suppress("DEPRECATION") activity.overridePendingTransition(0, 0)
    }
}
