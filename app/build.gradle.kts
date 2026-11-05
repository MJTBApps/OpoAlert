import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Datos privados de la versión de Google Play: clave de subida e identificadores
// reales de AdMob. Nunca en el repositorio (es público): están en el iMac, en
// ~/OpoAlert-claves/play.properties (o en la ruta de OPOALERT_PLAY_PROPERTIES).
val playProperties = Properties().apply {
    val path = System.getenv("OPOALERT_PLAY_PROPERTIES")
        ?: (System.getProperty("user.home") + "/OpoAlert-claves/play.properties")
    file(path).takeIf { it.exists() }?.inputStream()?.use { load(it) }
}

// Identificadores de PRUEBA de Google: los usan la versión web y las pruebas.
val testAdmobApp = "ca-app-pub-3940256099942544~3347511713"
val testBanner = "ca-app-pub-3940256099942544/9214589741"
val testOpenAd = "ca-app-pub-3940256099942544/9257395921"

android {
    namespace = "es.opoalert.app"
    compileSdk = 36

    defaultConfig {
        applicationId = "es.opoalert.app"
        minSdk = 26
        // Google Play exige API 36 a las apps nuevas desde el 31/08/2026.
        targetSdk = 36
        versionCode = 65
        versionName = "1.52.0"
    }

    // Firma fija de OpoAlert: sin ella cada compilación sale con una firma distinta
    // y Android obliga a desinstalar (y perder favoritos) en cada actualización.
    // La clave no está en el repositorio: en GitHub llega por secretos y en local
    // por las variables OPOALERT_KEYSTORE y OPOALERT_KEY_PASSWORD.
    val keystore = System.getenv("OPOALERT_KEYSTORE")?.let { file(it) }?.takeIf { it.exists() }
    signingConfigs {
        if (keystore != null) {
            create("opoalert") {
                storeFile = keystore
                storePassword = System.getenv("OPOALERT_KEY_PASSWORD")
                keyAlias = "opoalert"
                keyPassword = System.getenv("OPOALERT_KEY_PASSWORD")
            }
        }
        // Clave de SUBIDA a Google Play (Google firma la app final con la suya).
        playProperties.getProperty("storeFile")?.let { path ->
            create("play") {
                storeFile = file(path)
                storePassword = playProperties.getProperty("storePassword")
                keyAlias = playProperties.getProperty("keyAlias")
                keyPassword = playProperties.getProperty("keyPassword")
            }
        }
    }

    buildFeatures {
        buildConfig = true
    }

    // Dos canales: «web» (la APK de GitHub Pages, con aviso de versiones nuevas) y
    // «play» (Google Play: se actualiza por la tienda y lleva los anuncios reales).
    flavorDimensions += "canal"
    productFlavors {
        create("web") {
            dimension = "canal"
            buildConfigField("boolean", "SELF_UPDATE", "true")
            // Sin Google Play no hay cobro: las alertas son gratis en esta versión.
            buildConfigField("boolean", "BILLING", "false")
            buildConfigField("String", "ADMOB_BANNER", "\"$testBanner\"")
            buildConfigField("String", "ADMOB_OPEN_AD", "\"$testOpenAd\"")
            buildConfigField("String", "REVIEW_CODE_SHA256", "\"\"")
            manifestPlaceholders["admobAppId"] = testAdmobApp
        }
        create("play") {
            dimension = "canal"
            // Google Play no permite que la app se actualice fuera de la tienda.
            buildConfigField("boolean", "SELF_UPDATE", "false")
            // Premium se paga con Google Play Billing (suscripción opoalert_premium).
            buildConfigField("boolean", "BILLING", "true")
            buildConfigField("String", "ADMOB_BANNER", "\"${playProperties.getProperty("admobBanner", testBanner)}\"")
            buildConfigField("String", "ADMOB_OPEN_AD", "\"${playProperties.getProperty("admobOpenAd", testOpenAd)}\"")
            // Código para los revisores de Google Play: en la app solo va su huella SHA-256.
            buildConfigField("String", "REVIEW_CODE_SHA256",
                "\"${playProperties.getProperty("reviewCodeSha256", "")}\"")
            manifestPlaceholders["admobAppId"] = playProperties.getProperty("admobAppId", testAdmobApp)
        }
    }

    buildTypes {
        debug {
            signingConfigs.findByName("opoalert")?.let { signingConfig = it }
        }
        release {
            isMinifyEnabled = false
            signingConfigs.findByName("play")?.let { signingConfig = it }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("org.jsoup:jsoup:1.18.3")
    implementation("androidx.work:work-runtime-ktx:2.9.1")
    implementation("androidx.core:core-ktx:1.15.0")
    testImplementation("junit:junit:4.13.2")
    // org.json de Android está vacío en las pruebas locales.
    testImplementation("org.json:json:20240303")
    implementation("com.google.android.gms:play-services-ads:25.5.0")
    implementation("com.google.android.ump:user-messaging-platform:4.0.0")
    implementation("com.android.billingclient:billing-ktx:8.0.0")
}

// Nunca se sube a Google Play una versión con anuncios de prueba ni sin firmar.
tasks.matching { it.name == "bundlePlayRelease" || it.name == "assemblePlayRelease" }.configureEach {
    doFirst {
        val missing = listOf("storeFile", "admobAppId", "admobBanner", "admobOpenAd", "reviewCodeSha256")
            .filter { playProperties.getProperty(it).isNullOrBlank() }
        check(missing.isEmpty()) { "Faltan datos en ~/OpoAlert-claves/play.properties: $missing" }
        check(listOf("admobAppId", "admobBanner", "admobOpenAd").none {
            playProperties.getProperty(it).startsWith("ca-app-pub-3940256099942544")
        }) { "La versión de Google Play no puede llevar identificadores de PRUEBA de AdMob" }
    }
}
