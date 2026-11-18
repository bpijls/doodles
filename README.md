# doodles

Static HTML artifacts made in the Claude chat interface, published at **https://doodles.feib.nl**.

## Add a doodle

Download the artifact as an `.html` file, then:

```bash
./add.sh ~/Downloads/my-thing.html            # -> pages/my-thing.html, commit, push
./add.sh ~/Downloads/my-thing.html cool-name  # pick the slug yourself
./add.sh -n ~/Downloads/my-thing.html         # copy only, no commit/push
./add.sh ./some-folder                        # multi-file: folder with index.html -> pages/<slug>/
```

A push to `main` rebuilds the portal and deploys it (GitHub Actions → Pages), usually within a minute.
You can also just drop a file in `pages/` via the GitHub web UI.

The portal card uses, from the page itself:

| Card field  | Source                                   |
|-------------|------------------------------------------|
| title       | `<title>` (falls back to the slug)       |
| description | `<meta name="description" content="…">`  |
| tags        | `<meta name="keywords" content="a, b">`  |
| date        | first git commit of the file             |

Every doodle gets a small "← doodles" link back to the portal in the bottom-left corner. It is added
at build time; the files in `pages/` stay exactly as you downloaded them.

## Preview locally

```bash
python3 scripts/build.py && python3 -m http.server -d _site 8000
```

## DNS

`doodles.feib.nl` is a CNAME to `bpijls.github.io.` at TransIP; see `scripts/dns.py`.
