"""Every doodle, as served: loads without JS errors, keeps running, and links back to the portal.

These run once per doodle, so a broken new doodle fails the build (and so blocks the deploy).
"""

import build
import pytest

ENTRIES = build.collect()
SETTLE_MS = 2000  # long enough for a crash on the first animation frames to show up


@pytest.fixture(params=ENTRIES, ids=[e["slug"] for e in ENTRIES])
def doodle(request, watch, base_url):
    w = watch()
    w.page.goto(base_url + request.param["href"])
    w.page.wait_for_load_state("load")
    w.page.wait_for_timeout(SETTLE_MS)
    return w


def test_no_javascript_errors(doodle):
    assert doodle.errors == [], "uncaught errors while loading and running the doodle"


def test_no_missing_local_files(doodle):
    assert doodle.failed == []


def test_backlink_returns_to_portal(doodle, base_url):
    link = doodle.page.locator("doodles-backlink a")
    assert link.is_visible()
    box = link.bounding_box()
    viewport = doodle.page.viewport_size
    assert box["x"] < 40 and box["y"] + box["height"] > viewport["height"] - 40, "not in the bottom-left corner"
    link.click()
    doodle.page.wait_for_url(base_url)


def test_backlink_hidden_when_framed(watch, base_url):
    w = watch()
    w.page.goto(base_url)
    w.page.set_content(f'<iframe src="{base_url}{ENTRIES[0]["href"]}"></iframe>')
    frame = w.page.frame_locator("iframe")
    frame.locator("body").wait_for()
    w.page.wait_for_timeout(300)
    assert frame.locator("doodles-backlink").count() == 0
