package es.opoalert.app

import android.app.Activity
import android.app.AlertDialog
import android.os.Handler
import android.os.Looper
import android.view.View
import com.google.android.gms.ads.AdListener
import com.google.android.gms.ads.AdRequest
import com.google.android.gms.ads.AdSize
import com.google.android.gms.ads.AdView
import com.google.android.gms.ads.FullScreenContentCallback
import com.google.android.gms.ads.LoadAdError
import com.google.android.gms.ads.MobileAds
import com.google.android.gms.ads.appopen.AppOpenAd
import com.google.android.ump.ConsentInformation
import com.google.android.ump.ConsentRequestParameters
import com.google.android.ump.UserMessagingPlatform

/**
 * Publicidad de OpoAlert: un anuncio al abrir la app y anuncios intercalados en
 * la lista. Hoy usa los identificadores de PRUEBA de Google (no producen
 * ingresos); con la cuenta de AdMob basta cambiar los de abajo y el del manifiesto.
 * Con Premium activo no se pide ningún anuncio.
 */
class DemoAds(private val activity: Activity, private val onBannerLoaded: () -> Unit) {
    private val consent = UserMessagingPlatform.getConsentInformation(activity)
    private var started = false
    private var initialized = false
    private var wantsOpenAd = false
    private val banners = mutableListOf<AdView>()
    private val loaded = mutableSetOf<Int>()

    /** [openAd]: mostrar el anuncio de apertura (solo al abrir la app, nunca la primera vez). */
    fun start(openAd: Boolean = false) {
        if (started || !Premium.showsAds(activity)) return
        started = true
        wantsOpenAd = openAd
        consent.requestConsentInfoUpdate(activity,
            ConsentRequestParameters.Builder().build(), {
                UserMessagingPlatform.loadAndShowConsentFormIfRequired(activity) {
                    initializeIfAllowed()
                }
                initializeIfAllowed()
            }, {
                // Ante una incidencia de consentimiento, no se solicita publicidad
                // a menos que el gestor permita reutilizar un consentimiento valido.
                initializeIfAllowed()
            })
    }

    private fun initializeIfAllowed() {
        if (!consent.canRequestAds() || initialized || activity.isFinishing || activity.isDestroyed) return
        initialized = true
        Thread {
            MobileAds.initialize(activity) {
                activity.runOnUiThread {
                    if (!activity.isFinishing && !activity.isDestroyed) {
                        if (wantsOpenAd) loadOpenAd()
                        repeat(2) { bannerFor(it) }
                    }
                }
            }
        }.start()
    }

    private fun loadOpenAd() {
        val prefs = activity.getSharedPreferences(PREFS, Activity.MODE_PRIVATE)
        val now = System.currentTimeMillis()
        if (now - prefs.getLong(LAST_OPEN_AD, 0L) < OPEN_AD_MIN_INTERVAL_MS) return
        var expired = false
        // Si tarda, no se hace esperar: el anuncio se descarta.
        Handler(Looper.getMainLooper()).postDelayed({ expired = true }, OPEN_AD_TIMEOUT_MS)
        AppOpenAd.load(activity, OPEN_AD_ID, AdRequest.Builder().build(),
            object : AppOpenAd.AppOpenAdLoadCallback() {
                override fun onAdLoaded(ad: AppOpenAd) {
                    if (expired || activity.isFinishing || activity.isDestroyed || !Premium.showsAds(activity)) return
                    prefs.edit().putLong(LAST_OPEN_AD, System.currentTimeMillis()).apply()
                    ad.fullScreenContentCallback = object : FullScreenContentCallback() {}
                    ad.show(activity)
                }
                override fun onAdFailedToLoad(error: LoadAdError) {}
            })
    }

    /** Anuncio n.º [slot] de la lista (empieza en 0); null mientras no haya cargado. */
    fun bannerFor(slot: Int): View? {
        if (!initialized || slot >= MAX_LIST_ADS || !Premium.showsAds(activity)) return null
        while (banners.size <= slot) {
            val index = banners.size
            val dm = activity.resources.displayMetrics
            val widthDp = ((dm.widthPixels / dm.density).toInt() - 50).coerceAtLeast(260)
            val view = AdView(activity)
            view.adUnitId = BANNER_ID
            view.setAdSize(AdSize.getCurrentOrientationAnchoredAdaptiveBannerAdSize(activity, widthDp))
            view.adListener = object : AdListener() {
                override fun onAdLoaded() {
                    loaded.add(index)
                    onBannerLoaded()
                }
                override fun onAdFailedToLoad(error: LoadAdError) {
                    loaded.remove(index)
                }
            }
            banners.add(view)
            view.loadAd(AdRequest.Builder().build())
        }
        return if (slot in loaded) banners[slot] else null
    }

    fun showPrivacyOptions() {
        if (consent.privacyOptionsRequirementStatus == ConsentInformation.PrivacyOptionsRequirementStatus.REQUIRED) {
            UserMessagingPlatform.showPrivacyOptionsForm(activity) {
                if (consent.canRequestAds()) initializeIfAllowed()
            }
        } else {
            AlertDialog.Builder(activity)
                .setTitle("Privacidad y publicidad")
                .setMessage("OpoAlert muestra un anuncio al abrir la app y algunos entre las convocatorias. " +
                    "Por ahora son anuncios de prueba de Google y no generan ingresos. " +
                    "Si no das tu consentimiento, la app funciona igual sin publicidad. " +
                    "Con OpoAlert Premium no hay anuncios. OpoAlert es una aplicación independiente.")
                .setPositiveButton("Entendido", null)
                .show()
        }
    }

    fun pause() { banners.forEach { it.pause() } }
    fun resume() { banners.forEach { it.resume() } }
    fun destroy() { banners.forEach { it.destroy() }; banners.clear(); loaded.clear() }

    companion object {
        /** Cada cuántas convocatorias va un anuncio en la lista, y cuántos como máximo. */
        const val LIST_AD_EVERY = 8
        const val MAX_LIST_ADS = 5

        // Identificadores de PRUEBA de Google, no de la cuenta del usuario.
        private const val BANNER_ID = "ca-app-pub-3940256099942544/9214589741"
        private const val OPEN_AD_ID = "ca-app-pub-3940256099942544/9257395921"

        private const val PREFS = "opoalert_ui"
        private const val LAST_OPEN_AD = "last_app_open_ad"
        private const val OPEN_AD_MIN_INTERVAL_MS = 60 * 60 * 1000L
        private const val OPEN_AD_TIMEOUT_MS = 5000L
    }
}
