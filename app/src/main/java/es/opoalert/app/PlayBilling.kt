package es.opoalert.app

import android.app.Activity
import android.content.Context
import android.os.Handler
import android.os.Looper
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.PendingPurchasesParams
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.PurchasesUpdatedListener
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.QueryPurchasesParams

/**
 * Suscripción OpoAlert Premium con Google Play Billing (solo en la versión de Play).
 *
 * En Play Console: suscripción `opoalert_premium` con un plan base anual y, si se
 * quiere, una oferta de prueba gratuita. Google cobra, gestiona renovaciones y
 * cancelaciones; aquí solo se consulta si hay una suscripción activa.
 */
object PlayBilling {
    const val PRODUCT_ID = "opoalert_premium"

    /** Precio y prueba gratuita tal como los devuelve Google Play (ya traducidos). */
    data class Offer(val details: ProductDetails, val offerToken: String, val price: String, val trialDays: Int?)

    private val main by lazy { Handler(Looper.getMainLooper()) }
    private var client: BillingClient? = null
    private var onChange: (() -> Unit)? = null

    private val listener = PurchasesUpdatedListener { result, purchases ->
        val context = appContext ?: return@PurchasesUpdatedListener
        if (result.responseCode == BillingClient.BillingResponseCode.OK && purchases != null) {
            handle(context, purchases)
        }
    }
    private var appContext: Context? = null

    val enabled: Boolean get() = BuildConfig.BILLING

    private fun connect(context: Context, ready: (BillingClient?) -> Unit) {
        if (!enabled) return ready(null)
        appContext = context.applicationContext
        val current = client ?: BillingClient.newBuilder(context.applicationContext)
            .setListener(listener)
            .enablePendingPurchases(PendingPurchasesParams.newBuilder().enableOneTimeProducts().build())
            .enableAutoServiceReconnection()
            .build()
            .also { client = it }
        if (current.isReady) return ready(current)
        current.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(result: BillingResult) {
                main.post { ready(if (result.responseCode == BillingClient.BillingResponseCode.OK) current else null) }
            }
            override fun onBillingServiceDisconnected() {}
        })
    }

    /** Al abrir la app: comprueba en Google Play si la suscripción sigue activa. */
    fun refresh(context: Context, changed: () -> Unit = {}) {
        onChange = changed
        connect(context) { billing ->
            billing ?: return@connect
            billing.queryPurchasesAsync(
                QueryPurchasesParams.newBuilder().setProductType(BillingClient.ProductType.SUBS).build()
            ) { result, purchases ->
                // Sin respuesta de Google (sin conexión) se conserva el estado anterior.
                if (result.responseCode != BillingClient.BillingResponseCode.OK) return@queryPurchasesAsync
                main.post { handle(context, purchases, replaceState = true) }
            }
        }
    }

    fun loadOffer(context: Context, done: (Offer?) -> Unit) {
        connect(context) { billing ->
            billing ?: return@connect done(null)
            val params = QueryProductDetailsParams.newBuilder().setProductList(listOf(
                QueryProductDetailsParams.Product.newBuilder()
                    .setProductId(PRODUCT_ID)
                    .setProductType(BillingClient.ProductType.SUBS)
                    .build()
            )).build()
            billing.queryProductDetailsAsync(params) { result, found ->
                val details = found.productDetailsList.firstOrNull()
                val offer = if (result.responseCode == BillingClient.BillingResponseCode.OK && details != null)
                    bestOffer(details) else null
                main.post { done(offer) }
            }
        }
    }

    /** La oferta con prueba gratuita si la hay; si no, el plan base. */
    private fun bestOffer(details: ProductDetails): Offer? {
        val offers = details.subscriptionOfferDetails.orEmpty()
        val chosen = offers.firstOrNull { offer -> offer.pricingPhases.pricingPhaseList.any { it.priceAmountMicros == 0L } }
            ?: offers.firstOrNull() ?: return null
        val phases = chosen.pricingPhases.pricingPhaseList
        val paid = phases.lastOrNull { it.priceAmountMicros > 0 } ?: return null
        val trial = phases.firstOrNull { it.priceAmountMicros == 0L }?.let { trialDays(it.billingPeriod) }
        return Offer(details, chosen.offerToken, paid.formattedPrice + periodLabel(paid.billingPeriod), trial)
    }

    fun buy(activity: Activity, offer: Offer): Boolean {
        val billing = client ?: return false
        val params = BillingFlowParams.newBuilder().setProductDetailsParamsList(listOf(
            BillingFlowParams.ProductDetailsParams.newBuilder()
                .setProductDetails(offer.details)
                .setOfferToken(offer.offerToken)
                .build()
        )).build()
        return billing.launchBillingFlow(activity, params).responseCode == BillingClient.BillingResponseCode.OK
    }

    private fun handle(context: Context, purchases: List<Purchase>, replaceState: Boolean = false) {
        val premium = purchases.filter { PRODUCT_ID in it.products }
        val active = premium.any { it.purchaseState == Purchase.PurchaseState.PURCHASED }
        if (active || replaceState) {
            val before = Premium.isActive(context)
            Premium.setActive(context, active)
            if (before != active) main.post { onChange?.invoke() }
        }
        // Google devuelve el dinero si una compra no se confirma en tres días.
        premium.filter { it.purchaseState == Purchase.PurchaseState.PURCHASED && !it.isAcknowledged }.forEach {
            client?.acknowledgePurchase(
                AcknowledgePurchaseParams.newBuilder().setPurchaseToken(it.purchaseToken).build()
            ) {}
        }
    }

    /** «P1Y» → « al año», «P1M» → « al mes». */
    fun periodLabel(period: String): String = when (period) {
        "P1Y" -> " al año"
        "P6M" -> " cada 6 meses"
        "P3M" -> " cada 3 meses"
        "P1M" -> " al mes"
        "P1W" -> " a la semana"
        else -> ""
    }

    /** «P7D» → 7, «P1W» → 7, «P1M» → 30 (aproximado, solo para el texto). */
    fun trialDays(period: String): Int? {
        val match = Regex("""P(\d+)([DWM])""").matchEntire(period) ?: return null
        val n = match.groupValues[1].toInt()
        return when (match.groupValues[2]) { "D" -> n; "W" -> n * 7; else -> n * 30 }
    }
}
