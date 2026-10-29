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
        versionCode = 36
        versionName = "1.23.0"
    }

    buildTypes {
        debug {
            // Instalación paralela para probar sin desinstalar la versión habitual.
            applicationIdSuffix = ".dogv"
            versionNameSuffix = "-privada"
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
    implementation("com.google.android.gms:play-services-ads:25.5.0")
    implementation("com.google.android.ump:user-messaging-platform:4.0.0")
}
