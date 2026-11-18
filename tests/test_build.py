"""build.py logic: metadata parsing, backlink injection, thumbnail planning, site output. No browser."""

import json

import build
import pytest

DOODLE = """<!doctype html><html><head>
<title>  My
  Doodle &amp; Co </title>
<meta name="description" content="Does &quot;things&quot;">
<meta content="a, b ,, c" name="keywords">
</head><body><p>hi</p></body></html>"""


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A fake project: pages/, thumbs/ and a template, with build.py pointed at it."""
    (tmp_path / "pages").mkdir()
    (tmp_path / "thumbs").mkdir()
    (tmp_path / "index.template.html").write_text("<script>const D = /*DOODLES*/[];</script>")
    monkeypatch.setattr(build, "ROOT", tmp_path)
    monkeypatch.setattr(build, "PAGES", tmp_path / "pages")
    monkeypatch.setattr(build, "THUMBS", tmp_path / "thumbs")
    return tmp_path


def test_meta_reads_attributes_in_any_order():
    assert build.meta(DOODLE, "description") == 'Does "things"'
    assert build.meta(DOODLE, "keywords") == "a, b ,, c"
    assert build.meta(DOODLE, "viewport") == ""


def test_collect_single_file_and_directory_doodles(repo):
    (repo / "pages" / "one.html").write_text(DOODLE)
    (repo / "pages" / "multi").mkdir()
    (repo / "pages" / "multi" / "index.html").write_text("<title>Multi</title>")
    (repo / "pages" / "empty-dir").mkdir()  # no index.html: not a doodle
    (repo / "pages" / "notes.txt").write_text("not a doodle")
    (repo / "pages" / "_draft.html").write_text("<title>hidden</title>")

    by_slug = {e["slug"]: e for e in build.collect()}
    assert set(by_slug) == {"one", "multi"}
    one = by_slug["one"]
    assert one["title"] == "My Doodle & Co"
    assert one["tags"] == ["a", "b", "c"]
    assert one["href"] == "pages/one.html"
    assert by_slug["multi"]["href"] == "pages/multi/"


def test_title_falls_back_to_slug(repo):
    (repo / "pages" / "no_title-here.html").write_text("<p>x</p>")
    assert build.collect()[0]["title"] == "no title here"


@pytest.mark.parametrize("html, expect_end", [
    ("<html><body>x</body></html>", "</body></html>"),
    ("<html><body>x</BODY ></html>", "</BODY ></html>"),
    ("<p>no body tag</p>", "</script>\n"),
])
def test_backlink_goes_before_last_body_end(tmp_path, html, expect_end):
    f = tmp_path / "d.html"
    f.write_text(html)
    build.add_backlink(f)
    out = f.read_text()
    assert out.count("<doodles-backlink>") == 1
    assert out.endswith(expect_end)


def test_backlink_uses_last_body_end_when_text_mentions_one(tmp_path):
    f = tmp_path / "d.html"
    f.write_text("<body><pre>&lt;/body&gt; </body> in a string</pre></body>")
    build.add_backlink(f)
    assert f.read_text().endswith("</pre>" + build.BACKLINK + "</body>")


def test_thumbs_todo_only_missing_unless_asked(repo):
    for slug in ("a", "b", "c"):
        (repo / "pages" / f"{slug}.html").write_text(f"<title>{slug}</title>")
    (repo / "thumbs" / "a.jpg").write_bytes(b"x")
    (repo / "thumbs" / "b.jpg").write_bytes(b"x")
    entries = build.collect()

    def slugs(rethumb):
        return sorted(e["slug"] for e in build.thumbs_todo(entries, rethumb))

    assert slugs([]) == ["c"]
    assert slugs(["a"]) == ["a", "c"]
    assert slugs(["all"]) == ["a", "b", "c"]
    with pytest.raises(SystemExit, match="nope"):
        build.thumbs_todo(entries, ["nope"])


def test_orphan_thumbnails_are_removed(repo):
    (repo / "pages" / "kept.html").write_text("<title>k</title>")
    (repo / "thumbs" / "kept.jpg").write_bytes(b"x")
    (repo / "thumbs" / "gone.jpg").write_bytes(b"x")
    build.update_thumbs(build.collect(), [], enabled=False)
    assert sorted(p.name for p in (repo / "thumbs").iterdir()) == ["kept.jpg"]


def test_write_site(repo, tmp_path):
    (repo / "pages" / "one.html").write_text(DOODLE)
    (repo / "pages" / "two.html").write_text("<title>Two </script> evil</title><body></body>")
    (repo / "thumbs" / "one.jpg").write_bytes(b"jpg")
    out = tmp_path / "out"
    build.write_site(build.collect(), out)

    data = json.loads((out / "doodles.json").read_text())
    assert {d["slug"]: "thumb" in d for d in data} == {"one": True, "two": False}
    index = (out / "index.html").read_text()
    assert "/*DOODLES*/" not in index
    assert "</script> evil" not in index  # escaped, can't close the portal's <script>
    assert (out / "thumbs" / "one.jpg").exists()
    assert "<doodles-backlink>" in (out / "pages" / "one.html").read_text()
    assert "<doodles-backlink>" not in (repo / "pages" / "one.html").read_text()  # source untouched


def test_lint_doodles(repo):
    (repo / "pages" / "good.html").write_text(
        '<!DOCTYPE html><meta name="viewport" content="width=device-width">'
        '<title>G</title><meta name="description" content="d">')
    (repo / "pages" / "bad.html").write_text("<p>x</p>")
    problems = build.lint_doodles(build.collect())
    assert all(p.startswith("bad:") for p in problems)
    assert len(problems) == 4
