"""Shared fixtures: the built site in a temp dir, served over HTTP, and a headless Chromium."""

import functools
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build  # noqa: E402  (needs the sys.path entry above)


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class _QuietServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        pass  # a page closed mid-request (broken pipe): harmless


@pytest.fixture(scope="session")
def entries() -> list[dict]:
    return build.collect()


@pytest.fixture(scope="session")
def site(tmp_path_factory, entries) -> Path:
    """The site as build.py writes it, without making thumbnails or touching git."""
    out = tmp_path_factory.mktemp("site")
    build.write_site([dict(e) for e in entries], out)
    return out


@pytest.fixture(scope="session")
def base_url(site) -> str:
    server = _QuietServer(("127.0.0.1", 0), functools.partial(_QuietHandler, directory=str(site)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/"
    server.shutdown()


@pytest.fixture(scope="session")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        yield b
        b.close()


class PageWatch:
    """A page that records uncaught JS errors, console errors and failed same-origin requests."""

    def __init__(self, page, base_url):
        self.page, self.errors, self.failed = page, [], []
        page.on("pageerror", lambda e: self.errors.append(str(e).splitlines()[0]))
        page.on("console", lambda m: m.type == "error" and not m.text.startswith("Failed to load resource")
                and self.errors.append(m.text))
        page.on("response", lambda r: r.status >= 400 and r.url.startswith(base_url)
                and self.failed.append(f"{r.status} {r.url}"))
        page.on("requestfailed", lambda r: r.url.startswith(base_url) and self.failed.append(f"failed {r.url}"))


@pytest.fixture
def watch(browser, base_url):
    """Factory: watch(viewport=..., color_scheme=...) -> PageWatch; pages are closed after the test."""
    pages = []

    def make(**ctx):
        page = browser.new_page(**{"viewport": {"width": 1200, "height": 900}, **ctx})
        pages.append(page)
        return PageWatch(page, base_url)

    yield make
    for p in pages:
        p.close()
