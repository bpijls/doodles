"""Progressive web app: manifest, icons, service worker precache, and working offline."""

import json
import struct

import build
import pytest


def png_size(path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
    return struct.unpack(">II", data[16:24])


def test_manifest_is_installable(site):
    m = json.loads((site / "manifest.webmanifest").read_text())
    for field in ("name", "short_name", "start_url", "display", "icons", "theme_color", "background_color"):
        assert m.get(field), f"manifest has no {field}"
    assert m["display"] in ("standalone", "fullscreen", "minimal-ui")
    purposes = {icon.get("purpose", "any") for icon in m["icons"]}
    assert {"any", "maskable"} <= purposes
    for icon in m["icons"]:
        w, h = png_size(site / icon["src"])
        assert f"{w}x{h}" == icon["sizes"], icon["src"]
    assert any(i["sizes"] == "192x192" for i in m["icons"]) and any(i["sizes"] == "512x512" for i in m["icons"])


def test_portal_links_manifest_and_icons(site):
    index = (site / "index.html").read_text()
    assert '<link rel="manifest" href="manifest.webmanifest">' in index
    assert png_size(site / "icons" / "apple-touch-icon.png") == (180, 180)


def test_service_worker_precaches_every_built_file(site):
    sw = (site / "sw.js").read_text()
    assert "/*VERSION*/" not in sw and "/*PRECACHE*/" not in sw
    precache = json.loads(sw.split("const PRECACHE = ", 1)[1].split(";\n", 1)[0])
    built = {p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file()} - {"sw.js", "CNAME"}
    expected = {"./" + f.removesuffix("index.html") if f.endswith("index.html") else f for f in built}
    assert set(precache) == expected


def test_service_worker_version_follows_content(tmp_path):
    out = tmp_path / "s"
    out.mkdir()
    (out / "index.html").write_text("a")

    def version():
        build.write_service_worker(out)
        return (out / "sw.js").read_text().split('const VERSION = "', 1)[1][:12]

    first = version()
    assert first == version(), "same content must give the same version"
    (out / "index.html").write_text("b")
    assert version() != first


@pytest.fixture
def installed(watch, base_url):
    """A portal page whose service worker is installed and controlling it."""
    w = watch()
    w.page.goto(base_url)
    w.page.evaluate("navigator.serviceWorker.ready.then(() => true)")  # installed + activated
    w.page.reload()
    w.page.wait_for_function("navigator.serviceWorker.controller !== null")
    return w


def test_chromium_considers_it_installable(installed):
    cdp = installed.page.context.new_cdp_session(installed.page)
    errors = cdp.send("Page.getInstallabilityErrors")["installabilityErrors"]
    assert errors == [], [e["errorId"] for e in errors]


def test_install_button_hidden_until_browser_offers_install(installed):
    assert installed.page.locator("#install").is_hidden()


def test_portal_and_doodles_work_offline(installed, base_url, entries):
    page = installed.page
    page.context.set_offline(True)
    page.reload()
    assert page.locator("#list li").count() == len(entries)
    assert page.locator("#offline").is_visible()
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_function("[...document.querySelectorAll('#list img')].every(i => i.complete && i.naturalWidth)")

    for e in entries:
        page.goto(base_url + e["href"])
        assert page.title() == e["title"] or e["title"] == e["slug"].replace("-", " ")
        assert page.locator("doodles-backlink a").is_visible()
    page.context.set_offline(False)


def test_offline_unknown_page_falls_back_to_portal(installed, base_url):
    page = installed.page
    page.context.set_offline(True)
    page.goto(base_url + "pages/no-such-doodle.html")
    assert page.locator("header h1").inner_text().startswith("doodles")
    page.context.set_offline(False)
