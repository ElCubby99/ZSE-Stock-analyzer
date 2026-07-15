#!/usr/bin/env bash
# M32: jednokratna migracija lokalne pipeline baze (Postgres 'zse', ~21 MB)
# u Supabase Postgres (projekt burzovnilist, Frankfurt). Nakon ovoga GitHub
# Actions pipeline radi izravno nad Supabaseom (secret ZSE_DSN) i lokalna
# baza više nije potrebna za dnevni rad.
#
# Upotreba (na stroju s lokalnom bazom):
#   SUPABASE_DB_URL='postgresql://postgres:<lozinka>@db.<ref>.supabase.co:5432/postgres?sslmode=require' \
#     scripts/migrate_db_to_supabase.sh
#
# Sigurnost dizajna:
#  - dump je SAMO public shema lokalne baze (20 pipeline tablica) — ne dira
#    Supabase auth/storage niti postojeće tablice (blog_posts, news_items,
#    profiles, portfolios...) jer one u lokalnoj bazi ne postoje
#  - --no-owner --no-privileges: bez grantova -> tablice NISU vidljive kroz
#    PostgREST API (anon/authenticated nemaju prava; auto-expose je ionako
#    isključen) — pipeline im pristupa isključivo direktnom konekcijom
#  - idempotentno NIJE: pokreni jednom; za ponovni pokušaj prvo obriši
#    pipeline tablice u Supabaseu (popis ispod)
set -euo pipefail

: "${SUPABASE_DB_URL:?postavi SUPABASE_DB_URL (Supabase -> Database -> Connection string, sslmode=require)}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DUMP="$ROOT/data/zse_pipeline_dump.sql"

echo "== 1/3 pg_dump lokalne baze (public shema) =="
pg_dump "host=${PGHOST:-localhost} port=${PGPORT:-5432} dbname=${ZSE_DB:-zse} user=${ZSE_USER:-zse} password=${ZSE_PASS:-zse}" \
  --schema=public --no-owner --no-privileges --file "$DUMP"
echo "   dump: $DUMP ($(du -h "$DUMP" | cut -f1))"

echo "== 2/3 restore u Supabase =="
psql "$SUPABASE_DB_URL" --set ON_ERROR_STOP=1 --file "$DUMP"

echo "== 3/3 provjera =="
psql "$SUPABASE_DB_URL" -tAc \
  "select count(*) from companies" | xargs -I{} echo "   companies: {} redova"
psql "$SUPABASE_DB_URL" -tAc \
  "select count(*) from prices_eod" | xargs -I{} echo "   prices_eod: {} redova"

echo "GOTOVO. GitHub secret ZSE_DSN = isti connection string koji si upravo koristio."
echo "Tablice (za eventualni ponovni pokušaj): announcements api_usage"
echo "business_profiles calibrations companies dividends filings financials"
echo "growth_estimates holdings index_eod pipeline_runs prices_eod ratios"
echo "segment_financials share_classes shareholders valuation_changelog valuations watcher_state"
