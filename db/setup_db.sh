#!/usr/bin/env bash
# Idempotentno postavljanje lokalne Postgres baze za ZSE fundamental analytics.
# Kreira rolu + bazu i primjenjuje zse_schema.sql.
#
# Env varijable (s defaultima):
#   PGHOST=localhost  PGPORT=5432
#   ZSE_DB=zse  ZSE_USER=zse  ZSE_PASS=zse
set -euo pipefail

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
ZSE_DB="${ZSE_DB:-zse}"
ZSE_USER="${ZSE_USER:-zse}"
ZSE_PASS="${ZSE_PASS:-zse}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ">> Osiguravam Postgres servis..."
service postgresql start >/dev/null 2>&1 || pg_ctlcluster 16 main start >/dev/null 2>&1 || true

echo ">> Kreiram rolu '${ZSE_USER}' (ako ne postoji)..."
sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='${ZSE_USER}') THEN
    CREATE ROLE ${ZSE_USER} LOGIN PASSWORD '${ZSE_PASS}';
  END IF;
END \$\$;
SQL

echo ">> Kreiram bazu '${ZSE_DB}' (ako ne postoji)..."
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${ZSE_DB}'" \
  | grep -q 1 || sudo -u postgres createdb -O "${ZSE_USER}" "${ZSE_DB}"

# ZSE_RESET=1 => dropa i ponovno kreira public shemu (čist start).
# Bez toga, ponovno pokretanje na već postojećoj bazi padne na CREATE TABLE.
if [ "${ZSE_RESET:-0}" = "1" ]; then
  echo ">> ZSE_RESET=1: brišem i ponovno kreiram public shemu..."
  PGPASSWORD="${ZSE_PASS}" psql -h "${PGHOST}" -p "${PGPORT}" -U "${ZSE_USER}" -d "${ZSE_DB}" \
    -v ON_ERROR_STOP=1 -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
fi

echo ">> Primjenjujem shemu..."
PGPASSWORD="${ZSE_PASS}" psql -h "${PGHOST}" -p "${PGPORT}" -U "${ZSE_USER}" -d "${ZSE_DB}" \
  -v ON_ERROR_STOP=1 -f "${SCRIPT_DIR}/zse_schema.sql"

echo ">> Gotovo. Tablice:"
PGPASSWORD="${ZSE_PASS}" psql -h "${PGHOST}" -p "${PGPORT}" -U "${ZSE_USER}" -d "${ZSE_DB}" -c "\dt"
