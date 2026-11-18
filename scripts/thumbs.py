"""Screenshot doodles into thumbs/<slug>.jpg with Playwright (headless Chromium).

Pages are served from pages/ by a throwaway local HTTP server, so the shots never include the injected
backlink and multi-file doodles resolve their relative assets.
"""

import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VIEWPORT = {"width": 1200, "height": 750}  # layout size; the image is half that (scale 0.5)
SETTLE_MS = 1500  # let fonts, intro animations and canvases draw
TIMEOUT_MS = 20000


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def capture(pages_dir: Path, thumbs_dir: Path, entries: list[dict]) -> list[str]:
    """Capture one thumbnail per entry ({"slug", "href"} with href under pages/). Returns slugs done."""
    from playwright.sync_api import Error, sync_playwright  # imported lazily: only needed here

    thumbs_dir.mkdir(exist_ok=True)
    handler = functools.partial(_QuietHandler, directory=str(pages_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/"
    done = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=0.5, color_scheme="light")
            for e in entries:
                page = ctx.new_page()
                try:
                    page.goto(base + e["href"].removeprefix("pages/"), wait_until="load", timeout=TIMEOUT_MS)
                    page.wait_for_timeout(SETTLE_MS)
                    page.screenshot(path=thumbs_dir / f"{e['slug']}.jpg", type="jpeg", quality=80)
                    done.append(e["slug"])
                    print(f"  thumbnail: {e['slug']}")
                except Error as err:
                    print(f"  thumbnail FAILED for {e['slug']}: {err.message.splitlines()[0]}")
                finally:
                    page.close()
            browser.close()
    finally:
        server.shutdown()
    return done
