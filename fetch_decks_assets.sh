#!/bin/bash
set -euo pipefail

# Fetch the /decks page and its referenced app bundles using an authenticated cookie.
# Usage:
#   COOKIE_HEADER="ankiweb=...; has_auth=1" ./fetch_decks_assets.sh [/tmp/ankiweb-assets]
# If COOKIE_HEADER is unset, the script will try ~/.rememberit/settings.json:cookie_header

DEST="${1:-/tmp/ankiweb-assets}"
mkdir -p "$DEST"

COOKIE_HEADER="${COOKIE_HEADER:-}"
if [[ -z "$COOKIE_HEADER" ]]; then
  if [[ -f "$HOME/.rememberit/settings.json" ]]; then
    COOKIE_HEADER="$(jq -r '.cookie_header // empty' "$HOME/.rememberit/settings.json")"
  fi
fi

if [[ -z "$COOKIE_HEADER" ]]; then
  echo "ERROR: Set COOKIE_HEADER=\"ankiweb=...; has_auth=1\" or store it in ~/.rememberit/settings.json" >&2
  exit 1
fi

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"

echo "Fetching /decks HTML..."
curl -sS -D "$DEST/headers.txt" \
  -A "$UA" \
  -H "Cookie: $COOKIE_HEADER" \
  -o "$DEST/decks.html" \
  "https://ankiweb.net/decks"

echo "Extracting asset URLs..."
ASSETS=$(rg -o '/_app/immutable[^"]+\.mjs' "$DEST/decks.html" | sort -u)

if [[ -z "$ASSETS" ]]; then
  echo "No assets found in decks.html; check authentication." >&2
  exit 1
fi

echo "$ASSETS" | while read -r path; do
  file="${path##*/}"
  echo "Downloading $file"
  curl -sS -A "$UA" -H "Cookie: $COOKIE_HEADER" -o "$DEST/$file" "https://ankiweb.net${path}"
done

echo "Done. Assets in $DEST"
