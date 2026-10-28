"""Static UI smoke checks for the native v0.8 layout and its view wiring."""
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
    assert 'versionName = "0.8.0"' in gradle
    assert "versionCode = 8" in gradle
    print("OK: Android 0.8, XML, pantalla compacta, scroll, avisos y fuente fija")


if __name__ == "__main__":
    main()
