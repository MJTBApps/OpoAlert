package es.opoalert.app

import android.app.Activity
import android.graphics.Color
import android.view.View
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat

/**
 * Desde Android 15 (y sin excepción en Android 16) las apps se dibujan a pantalla
 * completa, debajo de la barra de estado y de la de navegación. Aquí cada pantalla
 * deja ese hueco (y el del teclado) para que nada quede tapado. Se aplica igual en
 * todas las versiones de Android para que se vea siempre igual.
 */
object SystemBars {
    private const val BACKGROUND = "#F7F9FC"

    fun fit(activity: Activity) {
        WindowCompat.setDecorFitsSystemWindows(activity.window, false)
        activity.window.decorView.setBackgroundColor(Color.parseColor(BACKGROUND))
        val content = activity.findViewById<View>(android.R.id.content)
        ViewCompat.setOnApplyWindowInsetsListener(content) { view, insets ->
            val bars = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() or
                    WindowInsetsCompat.Type.displayCutout() or
                    WindowInsetsCompat.Type.ime()
            )
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            WindowInsetsCompat.CONSUMED
        }
        ViewCompat.requestApplyInsets(content)
    }
}
