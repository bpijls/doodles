"""Render the PWA icons in icons/ from the favicon design. Run after changing the design; commit the PNGs.

    .venv/bin/python scripts/icons.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "icons"

ACCENT, PAPER = "#c2410c", "#fffdf8"
SQUIGGLE = "M8 20c3-9 6 3 9-5s5 4 7-1"  # in a 32x32 box, same as favicon.svg


def svg(rounded: bool, glyph_scale: float) -> str:
    """Full-bleed square (maskable) or rounded tile ("any"); the squiggle scaled about the centre."""
    rx = 8 if rounded else 0
    s = glyph_scale
    t = 16 * (1 - s)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            f'<rect width="32" height="32" rx="{rx}" fill="{ACCENT}"/>'
            f'<g transform="translate({t} {t}) scale({s})"><path d="{SQUIGGLE}" fill="none" stroke="{PAPER}" '
            f'stroke-width="3" stroke-linecap="round"/></g></svg>')


# name -> (size px, rounded tile, glyph scale). Maskable keeps the glyph inside the central 80% safe zone.
VARIANTS = {
    "icon-192.png": (192, True, 1.0),
    "icon-512.png": (512, True, 1.0),
    "maskable-512.png": (512, False, 0.72),
    "apple-touch-icon.png": (180, False, 0.8),  # iOS rounds the corners itself
}


def main() -> None:
    from playwright.sync_api import sync_playwright

    ICONS.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name, (size, rounded, scale) in VARIANTS.items():
            page = browser.new_page(viewport={"width": size, "height": size})
            page.set_content(f'<style>html,body{{margin:0;background:transparent}}svg{{display:block;'
                             f'width:{size}px;height:{size}px}}</style>{svg(rounded, scale)}')
            page.screenshot(path=ICONS / name, omit_background=True)
            page.close()
            print(f"  {name} ({size}px)")
        browser.close()


if __name__ == "__main__":
    main()
