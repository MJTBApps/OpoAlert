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
import com.google.android.gms.ads.interstitial.InterstitialAd
import com.google.android.gms.ads.interstitial.InterstitialAdLoadCallback
import com.google.android.ump.ConsentInformation
import com.google.android.ump.ConsentRequestParameters
import com.google.android.ump.UserMessagingPlatform

/**
 * Publicidad de OpoAlert: un anuncio al abrir la app, un intersticial cada
 * [NOTICES_PER_INTERSTITIAL] fichas cerradas, anuncios intercalados en la lista y dos en la ficha (a mitad y al final). Hoy usa los identificadores de PRUEBA de Google (no producen
 * ingresos); con la cuenta de AdMob basta cambiar los de abajo y el del manifiesto.
 * Con Premium activo no se pide ningún anuncio.
 */
class DemoAds(private val activity: Activity, private val onBannerLoaded: () -> Unit) {
    private val consent = UserMessagingPlatform.getConsentInformation(activity)
    private var started = false
    private var initialized = false
    private var wantsOpenAd = false
    private val banners = mutableListOf<AdView>()
    private val retryHandler = Handler(Looper.getMainLooper())
    private val loaded = mutableSetOf<Int>()
    private val prefs = activity.getSharedPreferences(PREFS, Activity.MODE_PRIVATE)
    private var interstitial: InterstitialAd? = null
    private var loadingInterstitial = false
    private var interstitialLoadedAt = 0L

    /** [openAd]: mostrar el anuncio de apertura (al arrancar la app, también la primera vez). */
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
                mobileAdsReady = true
                activity.runOnUiThread {
                    if (!activity.isFinishing && !activity.isDestroyed) {
                        if (wantsOpenAd) loadOpenAd()
                        repeat(2) { bannerFor(it) }
                        loadInterstitial()
                    }
                }
            }
        }.start()
    }

    private fun loadOpenAd() {
        val now = System.currentTimeMillis()
        if (now - prefs.getLong(LAST_OPEN_AD, 0L) < OPEN_AD_MIN_INTERVAL_MS) return
        var expired = false
        // Si tarda, no se hace esperar: el anuncio se descarta.
        Handler(Looper.getMainLooper()).postDelayed({ expired = true }, OPEN_AD_TIMEOUT_MS)
        AppOpenAd.load(activity, OPEN_AD_ID, AdRequest.Builder().build(),
            object : AppOpenAd.AppOpenAdLoadCallback() {
                override fun onAdLoaded(ad: AppOpenAd) {
                    if (expired || activity.isFinishing || activity.isDestroyed || !Premium.showsAds(activity)) return
                    prefs.edit().putLong(LAST_OPEN_AD, System.currentTimeMillis())
                        .putLong(LAST_FULLSCREEN, System.currentTimeMillis()).apply()
                    ad.fullScreenContentCallback = object : FullScreenContentCallback() {}
                    ad.show(activity)
                }
                override fun onAdFailedToLoad(error: LoadAdError) {}
            })
    }

    private fun loadInterstitial() {
        if (INTERSTITIAL_ID.isBlank() || interstitial != null || loadingInterstitial) return
        if (!initialized || activity.isFinishing || activity.isDestroyed || !Premium.showsAds(activity)) return
        loadingInterstitial = true
        InterstitialAd.load(activity, INTERSTITIAL_ID, AdRequest.Builder().build(),
            object : InterstitialAdLoadCallback() {
                override fun onAdLoaded(ad: InterstitialAd) {
                    loadingInterstitial = false
                    interstitial = ad
                    interstitialLoadedAt = System.currentTimeMillis()
                }
                override fun onAdFailedToLoad(error: LoadAdError) {
                    loadingInterstitial = false
                    retryHandler.postDelayed({ loadInterstitial() }, 60_000L)
                }
            })
    }

    /**
     * El usuario vuelve a la lista tras ver una ficha. Cada [NOTICES_PER_INTERSTITIAL] fichas
     * sale un anuncio a pantalla completa, nunca a menos de 2 minutos de otro (apertura incluida).
     * Si aún no ha cargado o es pronto, sale en la siguiente ficha.
     */
    /** true si se ha mostrado el anuncio a pantalla completa. */
    fun noticeClosed(): Boolean {
        if (INTERSTITIAL_ID.isBlank() || !Premium.showsAds(activity)) return false
        val count = prefs.getInt(NOTICES_SINCE_AD, 0) + 1
        prefs.edit().putInt(NOTICES_SINCE_AD, count).apply()
        val now = System.currentTimeMillis()
        // Un intersticial cargado caduca a la hora: Google ya no lo mostraría.
        if (interstitial != null && now - interstitialLoadedAt > INTERSTITIAL_LIFETIME_MS) interstitial = null
        val ad = interstitial
        if (count < NOTICES_PER_INTERSTITIAL || ad == null ||
            now - prefs.getLong(LAST_FULLSCREEN, 0L) < FULLSCREEN_MIN_GAP_MS) { loadInterstitial(); return false }
        interstitial = null
        prefs.edit().putInt(NOTICES_SINCE_AD, 0).putLong(LAST_FULLSCREEN, now).apply()
        ad.fullScreenContentCallback = object : FullScreenContentCallback() {
            override fun onAdDismissedFullScreenContent() { loadInterstitial() }
            override fun onAdFailedToShowFullScreenContent(error: com.google.android.gms.ads.AdError) {
                // No se pudo mostrar: toca en la próxima ficha.
                prefs.edit().putInt(NOTICES_SINCE_AD, NOTICES_PER_INTERSTITIAL - 1).apply()
                loadInterstitial()
            }
        }
        ad.show(activity)
        return true
    }

    /** Anuncio n.º [slot] de la lista (empieza en 0); null mientras no haya cargado. */
    fun bannerFor(slot: Int): View? {
        if (!initialized || !Premium.showsAds(activity)) return null
        while (banners.size <= slot) {
            val index = banners.size
            val dm = activity.resources.displayMetrics
            val widthDp = ((dm.widthPixels / dm.density).toInt() - 50).coerceAtLeast(260)
            val view = AdView(activity)
            view.adUnitId = BANNER_ID
            view.setAdSize(AdSize.getCurrentOrientationAnchoredAdaptiveBannerAdSize(activity, widthDp))
            view.adListener = object : AdListener() {
                private var tries = 0
                override fun onAdLoaded() {
                    tries = 0
                    loaded.add(index)
                    onBannerLoaded()
                }
                // Si no llega anuncio, se vuelve a pedir: a los 30 s, 60 s… hasta 5 min
                // (antes ese hueco no volvía a tener anuncio hasta reabrir la app).
                override fun onAdFailedToLoad(error: LoadAdError) {
                    // Si el hueco estaba en la lista, se quita: nunca se queda un recuadro vacío.
                    if (loaded.remove(index)) onBannerLoaded()
                    tries++
                    val delay = (30_000L * tries).coerceAtMost(300_000L)
                    retryHandler.postDelayed({
                        if (index < banners.size && banners[index] === view && !activity.isFinishing && !activity.isDestroyed) {
                            view.loadAd(AdRequest.Builder().build())
                        }
                    }, delay)
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
                .setMessage("OpoAlert muestra un anuncio al abrir la app, otro de vez en cuando al cerrar una convocatoria y algunos en la lista. " +
                    (if (BANNER_ID.startsWith("ca-app-pub-3940256099942544"))
                        "Por ahora son anuncios de prueba de Google y no generan ingresos. " else "") +
                    "Si no das tu consentimiento, la app funciona igual sin publicidad. " +
                    "Con OpoAlert Premium no hay anuncios. OpoAlert es una aplicación independiente.")
                .setPositiveButton("Entendido", null)
                .show()
        }
    }

    private var pausedAt = 0L

    fun pause() {
        pausedAt = System.currentTimeMillis()
        banners.forEach { it.pause() }
    }

    /**
     * Tras más de 5 minutos fuera, los banners guardados ya no muestran nada (el anuncio
     * caduca): se vuelven a pedir todos. Antes había que cerrar la app del todo.
     */
    fun resume() {
        banners.forEach { it.resume() }
        if (pausedAt == 0L || System.currentTimeMillis() - pausedAt < STALE_AFTER_MS) return
        pausedAt = 0L
        if (!initialized || !Premium.showsAds(activity)) return
        if (loaded.isNotEmpty()) { loaded.clear(); onBannerLoaded() }
        banners.forEach { it.loadAd(AdRequest.Builder().build()) }
    }
    fun destroy() { retryHandler.removeCallbacksAndMessages(null); banners.forEach { it.destroy() }; banners.clear(); loaded.clear() }

    companion object {
        /** Cada cuántas convocatorias va un anuncio en la lista (también al pulsar «Ver más»). */
        const val LIST_AD_EVERY = 2
        /** Cada cuántas fichas abiertas sale el intersticial. */
        const val NOTICES_PER_INTERSTITIAL = 3

        // De PRUEBA en la versión web; los reales de AdMob en la de Google Play (build.gradle.kts).
        private val BANNER_ID = BuildConfig.ADMOB_BANNER
        private val OPEN_AD_ID = BuildConfig.ADMOB_OPEN_AD
        /** Vacío = sin intersticial (versión de Play sin el bloque creado en AdMob). */
        private val INTERSTITIAL_ID = BuildConfig.ADMOB_INTERSTITIAL

        private const val PREFS = "opoalert_ui"
        private const val LAST_OPEN_AD = "last_app_open_ad"
        private const val LAST_FULLSCREEN = "last_fullscreen_ad"
        private const val NOTICES_SINCE_AD = "notices_since_interstitial"
        private const val FULLSCREEN_MIN_GAP_MS = 60 * 1000L
        private const val INTERSTITIAL_LIFETIME_MS = 50 * 60 * 1000L
        private const val STALE_AFTER_MS = 5 * 60 * 1000L

        /** MobileAds ya iniciado (con consentimiento) en este proceso. */
        @Volatile private var mobileAdsReady = false

        /**
         * Banner del final de la ficha. Solo si la lista ya inició la publicidad con
         * consentimiento y no hay Premium; [onLoaded] recibe el anuncio cuando carga
         * (si no carga, no se muestra nada: nunca un hueco vacío).
         */
        fun detailBanner(activity: Activity, onLoaded: (AdView) -> Unit): AdView? {
            if (!mobileAdsReady || !Premium.showsAds(activity) ||
                !UserMessagingPlatform.getConsentInformation(activity).canRequestAds()) return null
            val dm = activity.resources.displayMetrics
            val widthDp = ((dm.widthPixels / dm.density).toInt() - 36).coerceAtLeast(260)
            val view = AdView(activity)
            view.adUnitId = BANNER_ID
            view.setAdSize(AdSize.getCurrentOrientationAnchoredAdaptiveBannerAdSize(activity, widthDp))
            view.adListener = object : AdListener() {
                override fun onAdLoaded() {
                    if (!activity.isFinishing && !activity.isDestroyed) onLoaded(view)
                }
            }
            view.loadAd(AdRequest.Builder().build())
            return view
        }
        private const val OPEN_AD_MIN_INTERVAL_MS = 15 * 60 * 1000L
        private const val OPEN_AD_TIMEOUT_MS = 5000L
    }
}
