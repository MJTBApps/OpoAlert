package es.opoalert.app

import android.app.Activity
import android.app.AlertDialog
import android.view.View
import com.google.android.gms.ads.AdListener
import com.google.android.gms.ads.AdRequest
import com.google.android.gms.ads.AdSize
import com.google.android.gms.ads.AdView
import com.google.android.gms.ads.LoadAdError
import com.google.android.gms.ads.MobileAds
import com.google.android.ump.ConsentInformation
import com.google.android.ump.ConsentRequestParameters
import com.google.android.ump.UserMessagingPlatform

/** Anuncios exclusivamente de DEMOSTRACION. No producen ingresos. */
class DemoAds(private val activity: Activity, private val onBannerLoaded: () -> Unit) {
    private val consent = UserMessagingPlatform.getConsentInformation(activity)
    private var started = false
    private var initialized = false
    private var banner: AdView? = null
    private var bannerLoaded = false

    fun start() {
        if (started) return
        started = true
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
                    if (!activity.isFinishing && !activity.isDestroyed) prepareBanner()
                }
            }
        }.start()
    }

    private fun prepareBanner() {
        if (banner != null) return
        val dm = activity.resources.displayMetrics
        val widthDp = ((dm.widthPixels / dm.density).toInt() - 50).coerceAtLeast(260)
        val view = AdView(activity)
        view.adUnitId = DEMO_BANNER_ID
        view.setAdSize(AdSize.getCurrentOrientationAnchoredAdaptiveBannerAdSize(activity, widthDp))
        view.adListener = object : AdListener() {
            override fun onAdLoaded() {
                bannerLoaded = true
                onBannerLoaded()
            }
            override fun onAdFailedToLoad(error: LoadAdError) {
                bannerLoaded = false
                onBannerLoaded()
            }
        }
        banner = view
        view.loadAd(AdRequest.Builder().build())
    }

    fun availableBanner(): View? = if (bannerLoaded) banner else null

    fun showPrivacyOptions() {
        if (consent.privacyOptionsRequirementStatus == ConsentInformation.PrivacyOptionsRequirementStatus.REQUIRED) {
            UserMessagingPlatform.showPrivacyOptionsForm(activity) {
                if (consent.canRequestAds()) initializeIfAllowed()
            }
        } else {
            AlertDialog.Builder(activity)
                .setTitle("Publicidad de prueba")
                .setMessage("Esta versión solo utiliza anuncios de demostración de Google. " +
                    "No genera ingresos. Si el gestor de consentimiento no permite anuncios, " +
                    "la lista continúa sin publicidad. OpoAlert es una aplicación independiente.")
                .setPositiveButton("Entendido", null)
                .show()
        }
    }

    fun pause() { banner?.pause() }
    fun resume() { banner?.resume() }
    fun destroy() { banner?.destroy(); banner = null }

    companion object {
        // ID de anuncio DEMO para Android de Google, no de la cuenta del usuario.
        private const val DEMO_BANNER_ID = "ca-app-pub-3940256099942544/9214589741"
    }
}
