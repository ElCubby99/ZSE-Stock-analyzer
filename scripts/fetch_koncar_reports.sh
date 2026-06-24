#!/usr/bin/env bash
# Dohvati Končarova konsolidirana godišnja izvješća (2023-2025) u data/reports/.
#
# PREDUVJET: u mrežnoj politici okruženja (Custom network access) moraju biti
# dopušteni koncar.hr, *.koncar.hr, *.zse.hr — i to u NOVOJ sesiji.
# Ako su domene blokirane, curl vraća 403 (egress policy) i skripta to javlja.
#
# Koristi CA bundle proxyja i browser User-Agent (stranice znaju blokirati botove).
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/data/reports"
mkdir -p "$DIR"
CA="/root/.ccr/ca-bundle.crt"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# year|primary_url|mirror_url
ROWS=(
"2023|https://eho.zse.hr/fileadmin/issuers/KOEI/FI-KOEI-26b6d17c58e5d24666dbc8255aca031b.pdf|"
"2024|https://www.koncar.hr/sites/default/files/dokumenti/financijski-izvjestaji/2025-04/Revidirano%20konsolidirano%202024.pdf|https://eho.zse.hr/fileadmin/issuers/KOEI/FI-KOEI-962b2a89874cfc24b05051381efef45a.pdf"
"2025|https://www.koncar.hr/sites/default/files/dokumenti/financijski-izvjestaji/2026-04/Izvjestaj%20GRUPA%202025_HRV.pdf|"
)

fetch() {  # url -> out ; vrati 0 ako je rezultat validan PDF
  local url="$1" out="$2"
  curl -sS -L --fail --cacert "$CA" -A "$UA" --max-time 120 -o "$out" "$url" || return 1
  if head -c 5 "$out" | grep -q '%PDF'; then return 0; fi
  rm -f "$out"; return 1
}

fail=0
for row in "${ROWS[@]}"; do
  IFS='|' read -r year primary mirror <<<"$row"
  out="$DIR/koei_${year}_consolidated.pdf"
  echo ">> $year"
  if fetch "$primary" "$out"; then
    echo "   OK (primary): $out ($(wc -c <"$out") B)"
  elif [ -n "$mirror" ] && fetch "$mirror" "$out"; then
    echo "   OK (mirror):  $out ($(wc -c <"$out") B)"
  else
    echo "   NEUSPJEH za $year — provjeri whitelist (koncar.hr/*.zse.hr) i da je NOVA sesija."
    fail=1
  fi
done

exit $fail
