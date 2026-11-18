# doodles

## What this is

A static portal for HTML artifacts made in the Claude chat interface, served by GitHub Pages at
`https://doodles.feib.nl` (repo `bpijls/doodles`, public). No backend, no Docker — deliberately outside
the default project shape because it is just static files.

```
pages/*.html ──scripts/build.py──> _site/ (index.html + doodles.json + pages/) ──Actions──> GitHub Pages
```

## Running / adding

- `./add.sh <file.html|dir> [slug]` — copy into `pages/`, commit, push (`-n` = copy only).
- `python3 scripts/build.py --no-push && python3 -m http.server -d _site 8000` — local preview. Stdlib only, except
  making thumbnails: `uv venv && uv pip install -r requirements.txt && .venv/bin/playwright install
  chromium-headless-shell`, then `.venv/bin/python scripts/build.py`. Without Playwright the build skips them.
- `scripts/build.py --rethumb <slug>[,<slug>] | all` — regenerate thumbnails; `--plan` lists what would be
  made; `--no-thumbs` makes none; `--no-push` keeps new thumbnails local (use it for previews);
  `--out DIR` builds elsewhere; `--check` lints and tests after building. In CI: Actions → "Deploy to GitHub Pages" → Run workflow → `rethumb`.

## Tests

```bash
uv venv && uv pip install -r requirements-dev.txt && .venv/bin/playwright install chromium-headless-shell
.venv/bin/python scripts/build.py --check --no-push   # build, then ruff + doodle lint + pytest
.venv/bin/python -m pytest -q                          # tests only (builds its own copy in a temp dir)
.venv/bin/python -m ruff check .
```

- `tests/test_build.py` — build.py logic against a fake pages/ tree (no browser).
- `tests/test_portal.py` — the portal in headless Chromium: cards, thumbnails, filter, tags, phone layout.
- `tests/test_pwa.py` — manifest + icon sizes, precache = every built file, version follows content,
  Chromium's own installability check (CDP), portal and every doodle load with the network offline.
- `tests/test_doodles.py` — **parametrised over every doodle**: no uncaught JS errors in the first 2 s, no
  missing local files, backlink visible bottom-left and returning to `/`, backlink gone inside an iframe.
- Doodle lint (`lint_doodles`) only warns: missing title / description / viewport / doctype.
- CI runs `build.py --check`; any failure — including one broken doodle — blocks the whole deploy.

## Architecture

```
pages/                    one doodle per <slug>.html, or <slug>/index.html for multi-file ones
index.template.html       portal page; build.py replaces the `/*DOODLES*/[]` marker with the JSON list;
                          registers sw.js, shows the Install button (beforeinstallprompt) and an offline note
manifest.webmanifest      PWA manifest (copied into _site/)
sw.template.js            service worker; build.py fills /*VERSION*/ (content hash) and /*PRECACHE*/[]
icons/                    PWA icons (192/512, maskable 512, apple-touch 180), rendered by scripts/icons.py
scripts/build.py          scans pages/, reads <title>, meta description/keywords, git first-commit date;
                          injects the back-to-portal link into each doodle in _site/
scripts/icons.py          renders icons/*.png from the favicon design with Playwright (run by hand)
scripts/thumbs.py         Playwright capture: serves pages/ locally, 1200x750 layout -> 600x375 JPEG
tests/                    pytest suite; conftest builds the site into a temp dir and serves it
ruff.toml, pytest.ini     lint (line length 120) and test config
requirements-dev.txt      pytest + ruff on top of requirements.txt
scripts/dns.py            TransIP CNAME helper; runs from ~/projects/hva/pagelink with its venv + .env
add.sh                    add + commit + pull --rebase + push helper
thumbs/<slug>.jpg         committed thumbnails (copied into _site/thumbs/)
requirements.txt          playwright, pinned; only needed for thumbnails
CNAME                     doodles.feib.nl (copied into _site/)
.github/workflows/pages.yml  build + deploy on push to main (GitHub-hosted runner: repo is public)
```

## Key constraints

- Pages source is "GitHub Actions" (build_type `workflow`); the custom domain is also set in repo
  settings, the `CNAME` file alone does nothing for Actions deploys.
- Checkout uses `fetch-depth: 0` — the card date comes from `git log`; shallow clones would date everything today.
- Repo is public, so the paws self-hosted runner can't be used (add-repo.sh refuses public repos).
- Doodle files in `pages/` are never modified. At build time `build.py` injects a "← doodles" link
  (a `<doodles-backlink>` element with a shadow root, before the last `</body>`) into each entry page in
  `_site/` only. It skips itself when the doodle is framed. Other files of a multi-file doodle are left alone.
- Thumbnails are made only for doodles without `thumbs/<slug>.jpg`, or when named in `--rethumb`. CI makes
  them. `build.py` itself commits `thumbs/` (that path only) and pushes it back as the cache — as
  github-actions[bot] in CI (GITHUB_TOKEN pushes don't trigger a new run), as you locally. A failed push
  only warns;
  it installs Playwright only when `--plan` says something is needed. Thumbnails of removed doodles are
  deleted by the build. Shots come from `pages/` (no injected backlink), light color scheme.
- Because CI commits to main, pull before pushing (add.sh does).
- PWA: `sw.js` precaches everything in `_site/` on install and is re-versioned by a hash of the built files,
  so every deploy that changes anything installs a new cache (skipWaiting + clients.claim) and deletes the
  old one. HTML/JSON is network-first (fresh online, cached offline); other same-origin files are
  stale-while-revalidate. Cross-origin **scripts/styles/fonts/images only** go in a runtime cache (max 150)
  so CDN-based doodles work offline after one visit; other cross-origin requests (APIs) are not touched.
  Unknown pages offline fall back to the cached portal.
