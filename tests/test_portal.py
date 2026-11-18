"""The portal page in a real browser: cards, thumbnails, filter, tags, layout."""

import build
import pytest


@pytest.fixture
def portal(watch, base_url):
    w = watch()
    w.page.goto(base_url)
    w.page.wait_for_load_state("networkidle")
    return w


def titles(page):
    return page.locator("#list li h2").all_inner_texts()


def test_one_card_per_doodle_newest_first(portal, entries):
    assert titles(portal.page) == [e["title"] for e in entries]
    assert portal.page.locator("#count").inner_text() == f"{len(entries)} so far."
    dates = [e["date"] for e in entries]
    assert dates == sorted(dates, reverse=True)


def test_thumbnails_load(portal, entries):
    page = portal.page
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")  # images are lazy
    page.wait_for_function("[...document.querySelectorAll('#list img')].every(i => i.complete)")
    widths = page.evaluate("[...document.querySelectorAll('#list img')].map(i => i.naturalWidth)")
    with_thumb = [e for e in entries if (build.THUMBS / f"{e['slug']}.jpg").exists()]
    assert len(widths) == len(with_thumb)
    assert all(w == 600 for w in widths), widths


def test_no_errors(portal):
    assert portal.errors == []
    assert portal.failed == []


def test_filter(portal, entries):
    page = portal.page
    target = entries[0]["title"]
    page.fill("#q", target.split()[0])
    assert target in titles(page)
    page.fill("#q", "zzzz-no-such-doodle")
    assert titles(page) == []
    assert page.locator("#empty").is_visible()
    page.fill("#q", "")
    assert len(titles(page)) == len(entries)


def test_tags_filter_and_toggle(portal, entries):
    page = portal.page
    tags = page.locator("#tags .tag")
    if tags.count() == 0:
        pytest.skip("no doodle has keywords")
    tag = tags.first.inner_text()
    tags.first.click()
    assert sorted(titles(page)) == sorted(e["title"] for e in entries if tag in e["tags"])
    assert tags.first.get_attribute("aria-pressed") == "true"
    tags.first.click()
    assert len(titles(page)) == len(entries)


@pytest.mark.parametrize("scheme, background", [("light", "rgb(246, 243, 236)"), ("dark", "rgb(22, 21, 19)")])
def test_phone_layout(watch, base_url, scheme, background):
    w = watch(viewport={"width": 360, "height": 780}, color_scheme=scheme)
    w.page.goto(base_url)
    w.page.wait_for_load_state("networkidle")
    assert w.page.evaluate("document.documentElement.scrollWidth") <= 360
    assert w.page.evaluate("getComputedStyle(document.body).backgroundColor") == background


def test_tab_reaches_filter_first(portal):
    portal.page.keyboard.press("Tab")
    assert portal.page.evaluate("document.activeElement.id") == "q"
