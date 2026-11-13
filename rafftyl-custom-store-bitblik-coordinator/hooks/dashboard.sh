#!/bin/sh
set -eu
export DB_PASSWORD="$(cat /secrets/db-password)"
cd /app
exec node server.js
