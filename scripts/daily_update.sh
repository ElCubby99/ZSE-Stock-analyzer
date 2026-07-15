#!/usr/bin/env bash
# Dnevno osvježavanje ZSE analitike (vizija: izvještaj se osvježava kad stignu
# nova izvješća / cijene / dividende). Pokretati jednom dnevno (cron ili ručno).
#
#   TICKERS="ADRS CROS" scripts/daily_update.sh
#
# Koraci (svaki preskače uz poruku ako mu izvor nije dostupan):
#   1. NOVA FINANCIJSKA IZVJEŠĆA — eho.zse.hr feed; nove objave se samo ISPIŠU
#      (ekstrakcija u bazu je svjesna odluka: python -m src.ingest extract).
#   2. DIVIDENDE — eho.zse.hr objave skupština -> dividends + dps (idempotentno).
#   3. EOD CIJENE — službena ZSE tečajnica (JSON, javni web REST): src.prices zse-json.
#      CLASSES env var = tickere KLASA (default: ADRS ADRS2 CROS CROS2 MAIS KOEI).
#   4. VALUACIJA — ispis pokrenutih/preskočenih metoda + reconciliation.
#   5. AUTO-VIJESTI — draftovi u Supabase news_items (generate_news.py, dedup).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"; [ -x "$PY" ] || PY=python3
TICKERS="${TICKERS:-ADRS CROS}"
LOOKBACK_DAYS="${LOOKBACK_DAYS:-7}"
CA="${EHO_CA_BUNDLE:-${REQUESTS_CA_BUNDLE:-/root/.ccr/ca-bundle.crt}}"
FROM="$(date -d "-${LOOKBACK_DAYS} days" +%F 2>/dev/null || date -v-${LOOKBACK_DAYS}d +%F)"
TODAY="$(date +%F)"

echo "== 1/5 Nova financijska izvješća (EHO, od $FROM) =="
for T in $TICKERS; do
  curl -sS --cacert "$CA" --max-time 60 \
    "https://eho.zse.hr/feed/json?variant=financialReports&ticker=${T}&dateFrom=${FROM}&dateTo=${TODAY}" \
  | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
items=d.get('items') or []
if items:
    print(f'  ${T}: {len(items)} novih objava — pokreni ingest za relevantne:')
    for it in items:
        print(f\"    {it['publishDate'][:10]} y{it['year']} {it['period']} cons={it['consolidated']} {it['documentType']} {it['documentLink']}\")
else:
    print('  ${T}: ništa novo')
" || echo "  $T: feed nedostupan"
done

echo "== 2/5 Dividende (EHO, od $FROM) =="
(cd "$ROOT" && "$PY" -m src.dividends $TICKERS --from "$FROM") || echo "  dividende: greška (vidi iznad)"

echo "== 3/5 EOD cijene =="
CLASSES="${CLASSES:-ADRS ADRS2 CROS CROS2 MAIS KOEI}"
(cd "$ROOT" && "$PY" -m src.prices zse-json $CLASSES) \
  || echo "  zse-json nije uspio (mreža/allowlist?) — fallback: src.prices import-csv"

echo "== 4/5 Valuacija =="
(cd "$ROOT" && "$PY" -m src.valuation_methods $TICKERS)

echo "== 5/5 Auto-vijesti (draftovi u Supabase, dedup po izvoru) =="
(cd "$ROOT" && "$PY" scripts/generate_news.py --lookback-days "$LOOKBACK_DAYS") \
  || echo "  vijesti: greška (vidi iznad) — pipeline nastavlja"
