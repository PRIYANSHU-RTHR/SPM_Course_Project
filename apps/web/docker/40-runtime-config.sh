#!/bin/sh
# Writes /config.js from the container environment, so one image works for any API URL.
# Run by the nginx image's entrypoint (/docker-entrypoint.d) before nginx starts.
set -eu

api_url="${API_URL:-http://localhost:8000}"
case "$api_url" in
  http://*|https://*) ;;
  *) echo "API_URL must start with http:// or https:// (got: $api_url)" >&2; exit 1 ;;
esac
# Keep the value a plain JS string: drop quotes, backslashes and angle brackets.
safe_url=$(printf '%s' "$api_url" | tr -d '"\\<>')

mkdir -p /tmp/orchestrai
printf 'window.__ORCHESTRAI_CONFIG__ = { apiUrl: "%s" }\n' "$safe_url" > /tmp/orchestrai/config.js
echo "orchestrai: API_URL=$safe_url"
