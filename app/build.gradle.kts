plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "es.opoalert.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "es.opoalert.app"
        minSdk = 26
        targetSdk = 34
        versionCode = 53
        versionName = "1.40.0"
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
    }

    buildTypes {
        debug {
            signingConfigs.findByName("opoalert")?.let { signingConfig = it }
        }
        release {
            isMinifyEnabled = false
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
}
