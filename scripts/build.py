#!/usr/bin/env python3
"""Build the doodles site into _site/: copy pages/ and generate index.html from the template.

A doodle is either pages/<slug>.html or pages/<slug>/index.html (for multi-file artifacts).
Title comes from <title>, description from <meta name="description">, date from the file's
first git commit (falls back to mtime). Stdlib only.
"""

import html
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "pages"
OUT = ROOT / "_site"

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
META_RE = re.compile(r"<meta\s[^>]*>", re.I)
ATTR_RE = re.compile(r'([\w-]+)\s*=\s*("[^"]*"|\'[^\']*\')')


def meta(text: str, name: str) -> str:
    for tag in META_RE.findall(text):
        attrs = {k.lower(): v[1:-1] for k, v in ATTR_RE.findall(tag)}
        if attrs.get("name", "").lower() == name:
            return html.unescape(attrs.get("content", "")).strip()
    return ""


def added(path: Path) -> datetime:
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--follow", "--format=%cI", "--", str(path)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.split()
        if out:
            return datetime.fromisoformat(out[-1])
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)


def collect() -> list[dict]:
    entries = []
    for p in PAGES.iterdir():
        if p.name.startswith((".", "_")):
            continue
        if p.is_file() and p.suffix == ".html":
            file, href, slug = p, f"pages/{p.name}", p.stem
        elif p.is_dir() and (p / "index.html").exists():
            file, href, slug = p / "index.html", f"pages/{p.name}/", p.name
        else:
            continue
        text = file.read_text(encoding="utf-8", errors="replace")
        m = TITLE_RE.search(text)
        title = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else ""
        entries.append({
            "slug": slug,
            "href": href,
            "title": title or slug.replace("-", " ").replace("_", " "),
            "description": meta(text, "description"),
            "tags": [t.strip() for t in meta(text, "keywords").split(",") if t.strip()],
            "date": added(p).date().isoformat(),
        })
    return sorted(entries, key=lambda e: (e["date"], e["slug"]), reverse=True)


# Injected into each doodle's entry page (only in _site/; pages/ stays untouched). A shadow root keeps
# the doodle's CSS and the link's CSS from affecting each other.
BACKLINK = """
<doodles-backlink></doodles-backlink>
<script>
(() => {
  const host = document.querySelector("doodles-backlink");
  if (!host || window.top !== window.self) return host && host.remove();
  const root = host.attachShadow({mode: "open"});
  root.innerHTML = `<style>
    a { position: fixed; left: 12px; bottom: 12px; z-index: 2147483647;
        display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px 6px 10px;
        font: 500 13px/1 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
        color: #fffdf8; background: rgba(29,27,24,.72); border-radius: 99px; text-decoration: none;
        backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
        opacity: .55; transition: opacity .15s; }
    a:hover, a:focus-visible { opacity: 1; outline: 2px solid #fb923c; outline-offset: 2px; }
    @media print { a { display: none; } }
  </style><a href="/" aria-label="Back to all doodles">&larr; doodles</a>`;
})();
</script>
"""
BODY_END_RE = re.compile(r"</body\s*>", re.I)


def add_backlink(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    ends = list(BODY_END_RE.finditer(text))
    if ends:
        i = ends[-1].start()
        text = text[:i] + BACKLINK + text[i:]
    else:
        text += BACKLINK
    path.write_text(text, encoding="utf-8")


def main() -> None:
    entries = collect()
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(PAGES, OUT / "pages", ignore=shutil.ignore_patterns(".*"))
    for e in entries:
        href = OUT / e["href"]
        add_backlink(href / "index.html" if e["href"].endswith("/") else href)
    for extra in ("CNAME", "favicon.svg"):
        if (ROOT / extra).exists():
            shutil.copy(ROOT / extra, OUT / extra)
    (OUT / "doodles.json").write_text(json.dumps(entries, indent=2))
    template = (ROOT / "index.template.html").read_text(encoding="utf-8")
    data = json.dumps(entries).replace("</", "<\\/")
    (OUT / "index.html").write_text(template.replace("/*DOODLES*/[]", data), encoding="utf-8")
    print(f"built {len(entries)} doodle(s) into {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
