#!/usr/bin/env bash
# Add a doodle and publish it.
#   ./add.sh ~/Downloads/thing.html [slug]     single HTML file -> pages/<slug>.html
#   ./add.sh ./some-dir [slug]                 directory with index.html -> pages/<slug>/
# Slug defaults to the file/dir name, lowercased and dashed. Pass -n to skip commit+push.
set -euo pipefail
cd "$(dirname "$0")"

push=1
if [[ "${1:-}" == "-n" ]]; then push=0; shift; fi
src="${1:?usage: ./add.sh [-n] <file.html|dir> [slug]}"
[[ -e "$src" ]] || { echo "no such file: $src" >&2; exit 1; }

base="$(basename "$src")"; base="${base%.html}"
slug="${2:-$base}"
slug="$(echo "$slug" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')"
[[ -n "$slug" ]] || { echo "empty slug" >&2; exit 1; }

if [[ -d "$src" ]]; then
  [[ -f "$src/index.html" ]] || { echo "$src has no index.html" >&2; exit 1; }
  dest="pages/$slug"
  [[ -e "$dest" ]] && { echo "$dest already exists" >&2; exit 1; }
  cp -r "$src" "$dest"
else
  dest="pages/$slug.html"
  [[ -e "$dest" ]] && { echo "$dest already exists" >&2; exit 1; }
  cp "$src" "$dest"
fi
echo "added $dest"

if (( push )); then
  git add "$dest"
  git commit -q -m "Add doodle: $slug"
  git pull -q --rebase  # CI commits thumbnails back to main
  git push -q
  echo "published: https://doodles.feib.nl/${dest}$([[ -d $dest ]] && echo /)"
fi
