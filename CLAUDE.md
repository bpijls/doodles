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
- `python3 scripts/build.py && python3 -m http.server -d _site 8000` — local preview. Stdlib only.

## Architecture

```
pages/                    one doodle per <slug>.html, or <slug>/index.html for multi-file ones
index.template.html       portal page; build.py replaces the `/*DOODLES*/[]` marker with the JSON list
scripts/build.py          scans pages/, reads <title>, meta description/keywords, git first-commit date
scripts/dns.py            TransIP CNAME helper; runs from ~/projects/hva/pagelink with its venv + .env
add.sh                    add + commit + push helper
CNAME                     doodles.feib.nl (copied into _site/)
.github/workflows/pages.yml  build + deploy on push to main (GitHub-hosted runner: repo is public)
```

## Key constraints

- Pages source is "GitHub Actions" (build_type `workflow`); the custom domain is also set in repo
  settings, the `CNAME` file alone does nothing for Actions deploys.
- Checkout uses `fetch-depth: 0` — the card date comes from `git log`; shallow clones would date everything today.
- Repo is public, so the paws self-hosted runner can't be used (add-repo.sh refuses public repos).
- Doodle pages are served as-is; nothing in them is rewritten.
