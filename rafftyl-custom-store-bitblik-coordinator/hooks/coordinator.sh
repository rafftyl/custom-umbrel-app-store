#!/bin/sh
set -eu
umask 077
cd /state
if [ ! -f ENABLED ]; then
  echo 'BitBlik is disabled. Follow README activation steps; no Nostr or LND calls are made.'
  exec sleep infinity
fi
[ -s settings.env ] || { echo 'Missing settings.env' >&2; exit 1; }
[ -s coordinator.macaroon ] || { echo 'Missing restricted LND macaroon' >&2; exit 1; }
[ -s /lnd/tls.cert ] || { echo 'Missing LND TLS certificate' >&2; exit 1; }
# This is operator-owned shell configuration. Never accept it from the browser.
set -a
. ./settings.env
set +a
case "${TERMS_OF_USAGE_NADDR:-}" in naddr1?*) ;; *) echo 'Configure TERMS_OF_USAGE_NADDR before activation' >&2; exit 1;; esac
export DB_PASSWORD="$(cat /secrets/db-password)"
# Key generation/loading is upstream-owned; /state preserves the generated file.
exec /app/bin/bundle/bin/server
