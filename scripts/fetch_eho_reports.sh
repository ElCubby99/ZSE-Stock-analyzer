#!/usr/bin/env bash
# Dohvat konsolidiranih financijskih izvješća s EHO disclosure portala ZSE-a
# (eho.zse.hr) preko njegovog JSON feeda — BEZ scrapinga www.zse.hr/zse.hr.
#
# Zašto EHO feed: www.zse.hr redirecta na zse.hr (egress 403), adris.hr cert
# lanac se ne verificira, rest.zse.hr traži ZSE_API_KEY. eho.zse.hr je dosegljiv
# i nudi strukturirani feed objava (financijska izvješća) s direktnim PDF/XLSX linkovima.
#
# Egress proxy re-terminira TLS, pa curl MORA vjerovati CA bundleu:
#   --cacert /root/.ccr/ca-bundle.crt   (vidi /root/.ccr/README.md)
#
# Uporaba:
#   scripts/fetch_eho_reports.sh ADRS CROS
#   YEARS="2024 2025" scripts/fetch_eho_reports.sh ADRS
#
# Env:
#   CA          (default /root/.ccr/ca-bundle.crt)
#   DATE_FROM   (default 2022-01-01)   DATE_TO (default danas)
#   OUTDIR      (default data/reports)
#   YEARS       (opcionalno: filtriraj na ove godine; prazno = sve dostupne)
#   PERIOD      (default 1Y — godišnji)   CONSOLIDATED (default true)   DOCTYPE (default PDF)
set -euo pipefail

CA="${CA:-/root/.ccr/ca-bundle.crt}"
DATE_FROM="${DATE_FROM:-2022-01-01}"
DATE_TO="${DATE_TO:-$(date +%F)}"
OUTDIR="${OUTDIR:-data/reports}"
PERIOD="${PERIOD:-1Y}"
CONSOLIDATED="${CONSOLIDATED:-true}"
DOCTYPE="${DOCTYPE:-PDF}"
YEARS="${YEARS:-}"
FEED="https://eho.zse.hr/feed/json?variant=financialReports"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${ROOT}/.venv/bin/python"
[ -x "$PY" ] || PY="python3"
mkdir -p "$OUTDIR/eho"

if [ "$#" -eq 0 ]; then
  echo "usage: $0 <TICKER> [TICKER...]  (npr. ADRS CROS)" >&2
  exit 2
fi

for T in "$@"; do
  echo ">> $T: dohvaćam feed objava financijskih izvješća..."
  J="$OUTDIR/eho/${T}_fr.json"
  curl -sS --cacert "$CA" --max-time 60 \
    "${FEED}&ticker=${T}&dateFrom=${DATE_FROM}&dateTo=${DATE_TO}" -o "$J"

  # Parsiraj feed i preuzmi tražene (period/consolidated/doctype, opc. godine) dokumente.
  PERIOD="$PERIOD" CONSOLIDATED="$CONSOLIDATED" DOCTYPE="$DOCTYPE" YEARS="$YEARS" \
  OUTDIR="$OUTDIR" CA="$CA" TICKER="$T" "$PY" - <<'PYEOF'
import json, os, subprocess, sys
J=os.path.join(os.environ["OUTDIR"],"eho",os.environ["TICKER"]+"_fr.json")
d=json.load(open(J))
want_years={int(y) for y in os.environ.get("YEARS","").split()} if os.environ.get("YEARS","").strip() else None
period, cons, dtype = os.environ["PERIOD"], os.environ["CONSOLIDATED"]=="true", os.environ["DOCTYPE"]
ca, out, t = os.environ["CA"], os.environ["OUTDIR"], os.environ["TICKER"]
items=[it for it in (d.get("items") or [])
       if it.get("period")==period and bool(it.get("consolidated"))==cons
       and it.get("documentType")==dtype and (want_years is None or it.get("year") in want_years)]
if not items:
    print(f"   (nema dokumenata: period={period} consolidated={cons} {dtype} years={want_years})"); sys.exit(0)
for it in items:
    y=it["year"]; link=it["documentLink"].replace("\\/","/")
    dest=os.path.join(out, f"{t.lower()}_{y}_consolidated.{dtype.lower()}")
    print(f"   y{y} rev={it.get('revised')} -> {dest}")
    subprocess.run(["curl","-sS","--cacert",ca,"--max-time","180",link,"-o",dest], check=True)
PYEOF
done
echo ">> Gotovo. Sljedeće: pdf_extract -> python -m src.ingest extract (kad API limit dopusti)."
