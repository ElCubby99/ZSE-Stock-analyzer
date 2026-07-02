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
#   3. EOD CIJENE — blokirano: zse.hr 403 / rest.zse.hr traži ZSE_API_KEY /
#      mojedionice.com 403 (stanje 2026-07-02; vidi docs/adrs_cros_sources.md).
#   4. VALUACIJA — ispis pokrenutih/preskočenih metoda + reconciliation.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"; [ -x "$PY" ] || PY=python3
TICKERS="${TICKERS:-ADRS CROS}"
LOOKBACK_DAYS="${LOOKBACK_DAYS:-7}"
CA="${EHO_CA_BUNDLE:-${REQUESTS_CA_BUNDLE:-/root/.ccr/ca-bundle.crt}}"
FROM="$(date -d "-${LOOKBACK_DAYS} days" +%F 2>/dev/null || date -v-${LOOKBACK_DAYS}d +%F)"
TODAY="$(date +%F)"

echo "== 1/4 Nova financijska izvješća (EHO, od $FROM) =="
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

echo "== 2/4 Dividende (EHO, od $FROM) =="
(cd "$ROOT" && "$PY" -m src.dividends $TICKERS --from "$FROM") || echo "  dividende: greška (vidi iznad)"

echo "== 3/4 EOD cijene =="
if [ -n "${ZSE_API_KEY:-}" ]; then
  (cd "$ROOT" && "$PY" -m src.prices zse-rest $TICKERS) || true
else
  echo "  PRESKOČENO: nema dosegljivog izvora (zse.hr 403; ZSE_API_KEY nije postavljen)."
fi

echo "== 4/4 Valuacija =="
(cd "$ROOT" && "$PY" -m src.valuation_methods $TICKERS)
