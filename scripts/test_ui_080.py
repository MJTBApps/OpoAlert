"""Static UI smoke checks for the native v0.9.0 layout and its view wiring."""
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "app/src/main/res"
KOTLIN = ROOT / "app/src/main/java/es/opoalert/app"
ANDROID = "{http://schemas.android.com/apk/res/android}"


def main() -> None:
    for document in RES.rglob("*.xml"):
        ET.parse(document)
    tree = ET.parse(RES / "layout/activity_main.xml")
    ids = {
        node.attrib.get(ANDROID + "id", "").split("/")[-1]: node
        for node in tree.iter()
        if node.attrib.get(ANDROID + "id")
    }
    desired = (
        "listContainer", "countText", "favoritesCountText", "statusText",
        "sourceInfoText", "historyInfoText", "progressBar", "refreshButton",
        "menuButton", "provinceSelector", "titleText", "summaryCard", "searchInput", "tabsRow", "filterRow", "resultsScroll",
        "resultsText",
    )
    activity = (KOTLIN / "MainActivity.kt").read_text(encoding="utf-8")
    for item in desired:
        assert item in ids, f"Missing view ID: {item}"
        assert f"R.id.{item}" in activity, f"View not wired: {item}"
    for gone in ("alertsSwitch", "feedSettingsButton", "recentOnlySwitch"):
        assert gone not in ids and gone not in activity, f"Technical UI still visible: {gone}"
    scroll = ids["resultsScroll"]
    assert scroll.attrib.get(ANDROID + "layout_weight") == "1", "List must fill remaining height"
    assert ids["refreshButton"].tag.endswith("ImageButton"), "Refresh must be a real icon button"
    assert ids["menuButton"].tag.endswith("ImageButton")
    assert ids["refreshButton"].attrib[ANDROID + "layout_width"] == "44dp"
    assert "NOTIFICATIONS_PROMPTED" in activity and "requestNotificationsOnce()" in activity
    assert "NoticeText.headline(item.title)" in activity
    assert "NoticeText.isProcedureUpdate(item.title)" in activity
    repository = (KOTLIN / "Repository.kt").read_text(encoding="utf-8")
    assert "fun feedUrl(ctx: Context): String = DEFAULT_FEED_URL" in repository
    assert "https://mjtbapps.github.io/OpoAlert/convocatorias.json" in repository
    gradle = (ROOT / "app/build.gradle.kts").read_text(encoding="utf-8")
    assert 'versionName = "1.53.1"' in gradle
    assert "versionCode = 67" in gradle
    assert "applicationIdSuffix" not in gradle, "La APK publicada debe actualizar la app habitual"
    assert not (ROOT / "app/src/debug").exists(), "Sin variante paralela: misma app y mismo nombre"
    reader = (KOTLIN / "RemoteFeedReader.kt").read_text(encoding="utf-8")
    assert "assets" not in reader, "Todas las fuentes se leen de GitHub Pages, sin copias congeladas"
    # 1.53.0: diseño de iPhone. Tarjeta de resumen blanca dentro de la lista,
    # buscador fijo fuera de ella y barra de pestañas flotante abajo.
    assert ids["summaryCard"].attrib.get(ANDROID + "background") == "@drawable/bg_card_white"
    assert ids["tabsRow"].attrib.get(ANDROID + "layout_gravity") == "bottom"
    assert "BottomTabs.build(tabsRow" in activity
    assert ids["historyInfoText"].attrib.get(ANDROID + "maxLines") == "1"
    assert "compactUpdated(lastSync)" in activity
    assert "latestById" in activity
    assert "showProvinceChooser" in activity
    assert "ProvinceSettings.selected(this)" in activity
    assert "R.id.provinceSelector" in activity
    assert "provinceSelector" in ids
    assert "SearchText.matchesNormalized(" in activity
    assert "addBannerIfAvailable(index / DemoAds.LIST_AD_EVERY)" in activity
    assert "demoAds.start(openAd = coldStart)" in activity, "Anuncio de apertura solo al arrancar"
    assert "DemoAds(this)" in activity
    ads = (KOTLIN / "DemoAds.kt").read_text(encoding="utf-8")
    assert "BuildConfig.ADMOB_BANNER" in ads and "BuildConfig.ADMOB_OPEN_AD" in ads, "Identificadores por canal"
    gradle_text = (ROOT / "app/build.gradle.kts").read_text(encoding="utf-8")
    assert 'create("web")' in gradle_text and 'create("play")' in gradle_text, "Canales web y Google Play"
    assert "ca-app-pub-3940256099942544/9214589741" in gradle_text, "La web usa anuncios de prueba"
    assert "no puede llevar identificadores de PRUEBA" in gradle_text, "Play nunca con anuncios de prueba"
    assert "targetSdk = 36" in gradle_text, "Google Play exige API 36"
    assert '"SELF_UPDATE", "false"' in gradle_text, "Play no se autoactualiza"
    assert "BuildConfig.SELF_UPDATE" in activity and "BuildConfig.SELF_UPDATE" in repository
    for screen in ("MainActivity.kt", "NoticeDetailActivity.kt", "AlertsActivity.kt", "PdfViewerActivity.kt"):
        assert "SystemBars.fit(this)" in (KOTLIN / screen).read_text(encoding="utf-8"), screen + ": barras del sistema"
    assert "canRequestAds()" in ads
    assert "loadAndShowConsentFormIfRequired" in ads
    assert "AppOpenAd.load(" in ads and "OPEN_AD_TIMEOUT_MS" in ads, "Anuncio de apertura con espera máxima"
    assert "Premium.showsAds(activity)" in ads, "Premium quita la publicidad"
    premium = (KOTLIN / "Premium.kt").read_text(encoding="utf-8")
    assert "BuildConfig.BILLING" in premium, "Las alertas son de pago solo donde hay Google Play Billing"
    assert '"BILLING", "false"' in gradle_text and '"BILLING", "true"' in gradle_text, "Web gratis, Play con pago"
    billing = (KOTLIN / "PlayBilling.kt").read_text(encoding="utf-8")
    assert 'PRODUCT_ID = "opoalert_premium"' in billing and "acknowledgePurchase" in billing, "Suscripción confirmada"
    alerts_screen = (KOTLIN / "AlertsActivity.kt").read_text(encoding="utf-8")
    assert "PremiumDialog.show(" in alerts_screen and "premiumCard" in alerts_screen, "Alertas: invitar a Premium"
    manifest = (ROOT / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    assert "${admobAppId}" in manifest, "El identificador de AdMob sale del canal"
    assert "AlertsActivity::class.java" in activity
    assert "Notifications.show(this, result.alertMatches)" in activity
    assert "AlertRuleStore.list(ctx)" in repository
    assert "SmartAlertMatcher.matching(newOnes" in repository
    worker = (KOTLIN / "BopWorker.kt").read_text(encoding="utf-8")
    assert "result.alertMatches" in worker
    notifications = (KOTLIN / "Notifications.kt").read_text(encoding="utf-8")
    assert "SmartAlertMatcher.matching(" in notifications
    assert "AlertRuleStore.list(context)" in notifications
    manifest = (ROOT / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    assert 'android:name=".AlertsActivity"' in manifest
    assert 'android:exported="false"' in manifest
    assert (KOTLIN / "AlertRuleStore.kt").exists()
    assert (KOTLIN / "AlertsActivity.kt").exists()
    tabs = (KOTLIN / "BottomTabs.kt").read_text(encoding="utf-8")
    assert tabs.index('"Explorar"') < tabs.index('"Favoritas"') < tabs.index('"Alertas"'), "Alertas debe ser tercera pestaña"
    assert 'NoticeDetailActivity::class.java' in activity
    assert 'android:name=".NoticeDetailActivity"' in manifest
    assert "R.id.alertsButton" not in activity
    detail = (KOTLIN / "NoticeDetailActivity.kt").read_text(encoding="utf-8")
    assert "Ver PDF oficial" in detail
    assert "Compartir convocatoria" in detail
    assert "FavoritesStore.toggle" in detail
    assert "NoticeDetails.placesInTitle" in detail
    assert "NoticeDetails.deadlineLabel" not in detail, "Sin recuadro de plazo: confundía"
    assert "bottomTabs()" not in detail, "La ficha no debe mostrar una barra inferior"
    assert "private fun nav(" not in detail
    assert "Volver al listado" in detail, "Mantener la flecha para volver"
    assert "link.host != province.pdfHost" in detail
    assert "PdfViewerActivity.open(" in detail, "El PDF oficial se ve dentro de la app"
    assert 'android:name=".PdfViewerActivity"' in manifest
    viewer = (KOTLIN / "PdfViewerActivity.kt").read_text(encoding="utf-8")
    assert "cacheDir" in viewer and "file.delete()" in viewer, "No se guarda en Descargas"
    assert "looksLikePdf" in viewer and "openOutside()" in viewer
    document = (KOTLIN / "PdfDocumentView.kt").read_text(encoding="utf-8")
    assert "ScaleGestureDetector" in document and "OverScroller" in document and "onDoubleTap" in document, "Zoom continuo como una foto"
    assert "renderDetails" in document, "Al soltar el zoom el texto se vuelve a dibujar nítido"
    assert "addDeadline(content)" in detail and "DeadlineStore.find(" in detail, "Plazo copiado del anuncio en la ficha"
    assert "no calcula la fecha" in detail, "Avisar de que no se calcula ninguna fecha"
    assert "VisitStore.startVisit(this)" in activity and "VisitStore.remember(this, notices)" in activity
    assert 'FILTER_NEW = "Nuevas"' in activity and '"NUEVA"' in activity, "Marcar las convocatorias nuevas"
    ios_project = (ROOT / "ios/project.yml").read_text(encoding="utf-8")
    assert 'MARKETING_VERSION: "1.53.1"' in ios_project, "iOS y Android con el mismo número de versión"
    assert 'android:networkSecurityConfig="@xml/network_security_config"' in manifest
    security = (ROOT / "app/src/main/res/xml/network_security_config.xml").read_text(encoding="utf-8")
    assert '<certificates src="system" />' in security and "@raw/sectigo_r46" in security
    assert 'cleartextTrafficPermitted="false"' in security, "Solo HTTPS"
    assert "Sede electrónica" not in detail, "No inventar enlace de sede"
    province = (KOTLIN / "Province.kt").read_text(encoding="utf-8")
    assert 'BOE(' in province and 'BOE-A-' in province
    assert 'boe.json' in province
    assert 'shown.take(displayedLimit)' in activity, "Paginación necesaria para anuncios nacionales"
    assert 'setTitle("Elegir boletines")' in activity
    picker = (KOTLIN / "SourcePicker.kt").read_text(encoding="utf-8")
    assert 'SourceCatalog.groups()' in picker
    assert 'SourcePicker.build(this, selected)' in activity
    alerts = (KOTLIN / "AlertsActivity.kt").read_text(encoding="utf-8")
    assert 'SourcePicker.build(this, selected)' in alerts, "Alertas: mismo selector por comunidades"
    assert 'SourcePicker.scrolling(this, content)' in alerts, "El editor de alertas debe poder desplazarse"
    assert 'provinceSelector.setOnClickListener { showProvinceChooser() }' in activity
    assert 'BOE n.º ' in detail
    print("OK: Android 1.53.1: diseño de iPhone y cambio de pestaña rápido")


if __name__ == "__main__":
    main()
