#!/bin/sh
set -eu
password=$(cat /secrets/db-password)
case "$password" in ''|*[!0-9a-f]*) echo 'Invalid database secret' >&2; exit 1;; esac
[ "${#password}" -eq 64 ] || exit 1
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_password="$password" <<'SQL'
CREATE ROLE bitblik LOGIN PASSWORD :'app_password';
ALTER DATABASE bitblik OWNER TO bitblik;
GRANT ALL ON SCHEMA public TO bitblik;
SQL
