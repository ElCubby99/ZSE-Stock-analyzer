#!/usr/bin/env bash
# SessionStart hook: pripremi okruženje za ZSE pipeline u cloud sesijama.
# - pokrene Postgres
# - kreira rolu/bazu i primijeni shemu AKO tablice ne postoje (idempotentno)
# - postavi .venv i instalira requirements ako fali
# Sigurno: greške ne ruše sesiju (hook teče nakon launcha Claudea).
set -uo pipefail

# Samo u cloud sesijama (lokalno preskoči).
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ZSE_DB="${ZSE_DB:-zse}"; ZSE_USER="${ZSE_USER:-zse}"; ZSE_PASS="${ZSE_PASS:-zse}"

echo "[session_start] Postgres..."
service postgresql start >/dev/null 2>&1 || pg_ctlcluster 16 main start >/dev/null 2>&1 || true

# Ima li već shema? (provjeri tablicu financials)
HAS_TABLE="$(PGPASSWORD="$ZSE_PASS" psql -h localhost -U "$ZSE_USER" -d "$ZSE_DB" -tAc \
  "SELECT to_regclass('public.financials') IS NOT NULL" 2>/dev/null || echo "")"
if [ "$HAS_TABLE" != "t" ]; then
  echo "[session_start] primjenjujem shemu..."
  bash "$ROOT/db/setup_db.sh" >/dev/null 2>&1 || echo "[session_start] setup_db.sh nije uspio (provjeri ručno)"
else
  echo "[session_start] shema već postoji."
fi

# Python venv.
if [ ! -d "$ROOT/.venv" ]; then
  echo "[session_start] kreiram .venv i instaliram requirements..."
  python3 -m venv "$ROOT/.venv" >/dev/null 2>&1 || true
  "$ROOT/.venv/bin/pip" install -q --upgrade pip >/dev/null 2>&1 || true
  "$ROOT/.venv/bin/pip" install -q -r "$ROOT/requirements.txt" >/dev/null 2>&1 \
    || echo "[session_start] pip install nije uspio (provjeri ručno)"
fi

echo "[session_start] gotovo."
exit 0
