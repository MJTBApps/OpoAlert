"""Static UI smoke checks for the native v0.8.2 layout and its view wiring."""
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
        "menuButton", "searchInput", "tabsRow", "filterRow", "resultsScroll",
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
    assert 'versionName = "0.8.2"' in gradle
    assert "versionCode = 10" in gradle
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
    assert "SearchText.normalize(searchInput.text.toString().trim())" in activity
    assert "SearchText.matchesNormalized(" in activity
    print("OK: Android 0.8.2, resumen mas compacto, titulos CAS, scroll, favoritos")


if __name__ == "__main__":
    main()
