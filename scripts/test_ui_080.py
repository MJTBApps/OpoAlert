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
        "menuButton", "provinceSelector", "chooseSourcesButton", "searchInput", "tabsRow", "filterRow", "resultsScroll",
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
    assert 'versionName = "1.26.0"' in gradle
    assert "versionCode = 39" in gradle
    # El bloque resumen debe permitir que el listado crezca: maximo 8dp
    # de relleno vertical y el texto de metadatos en una sola linea.
    summary = next(node for node in tree.getroot() if
                   node.attrib.get(ANDROID + "background") == "@drawable/bg_summary_compact")
    assert summary.attrib.get(ANDROID + "paddingTop") == "8dp"
    assert summary.attrib.get(ANDROID + "paddingBottom") == "8dp"
    assert ids["historyInfoText"].attrib.get(ANDROID + "maxLines") == "1"
    assert ids["countText"].attrib.get(ANDROID + "textSize") == "24sp"
    assert "compactUpdated(lastSync)" in activity
    assert "latestById" in activity
    assert "showProvinceChooser" in activity
    assert "ProvinceSettings.selected(this)" in activity
    assert "R.id.provinceSelector" in activity
    assert "provinceSelector" in ids
    assert "SearchText.matchesNormalized(" in activity
    assert "addDemoBannerIfAvailable()" in activity
    assert "DemoAds(this)" in activity
    ads = (KOTLIN / "DemoAds.kt").read_text(encoding="utf-8")
    assert "ca-app-pub-3940256099942544/9214589741" in ads
    assert "canRequestAds()" in ads
    assert "loadAndShowConsentFormIfRequired" in ads
    manifest = (ROOT / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    assert "ca-app-pub-3940256099942544~3347511713" in manifest
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
    assert 'TAB_ALERTS to "♧ Alertas"' in activity, "Alertas debe ser tercera pestaña"
    assert 'NoticeDetailActivity::class.java' in activity
    assert 'android:name=".NoticeDetailActivity"' in manifest
    assert "R.id.alertsButton" not in activity
    detail = (KOTLIN / "NoticeDetailActivity.kt").read_text(encoding="utf-8")
    assert "Ver PDF oficial" in detail
    assert "Compartir convocatoria" in detail
    assert "FavoritesStore.toggle" in detail
    assert "NoticeDetails.placesInTitle" in detail
    assert "NoticeDetails.deadlineLabel" in detail
    assert "bottomTabs()" not in detail, "La ficha no debe mostrar una barra inferior"
    assert "private fun nav(" not in detail
    assert "Volver al listado" in detail, "Mantener la flecha para volver"
    assert "link.host != province.pdfHost" in detail
    assert "Sede electrónica" not in detail, "No inventar enlace de sede"
    province = (KOTLIN / "Province.kt").read_text(encoding="utf-8")
    assert 'BOE(' in province and 'BOE-A-' in province
    assert 'boe.json' in province
    assert 'shown.take(displayedLimit)' in activity, "Paginación necesaria para anuncios nacionales"
    assert 'setTitle("Elegir boletines")' in activity
    assert 'SourceCatalog.groups()' in activity
    assert 'chooseSourcesButton.setOnClickListener' in activity
    assert 'BOE n.º ' in detail
    print("OK: Android 1.20.0: DOGV Comunidad Valenciana, Aragón BOA, Andalucía BOJA, Galicia, Euskadi, BORM Murcia, Extremadura y CyL privados, selector y favoritos")


if __name__ == "__main__":
    main()
