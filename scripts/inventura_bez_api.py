"""M19-B KORAK 1/5: inventura pokrivenosti bez API-ja — što ima, što fali, i
je li preostalo išta lokalno ekstraktibilno.

Za svaku dionicu: puna analiza (annual u bazi) / market_only + TOČAN razlog
što fali (koje izvješće/format), TTM spremnost (kvartali). Ispisuje markdown
tablicu u docs/inventura_bez_api.md i sažetak na stdout.
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402

# Razlozi za market_only utvrđeni pregledom EHO feeda (2026-07-14):
MISSING = {
    "BRIN": "ZAIF obrazac (invest. fond) — XLSX postoji, ali fond-forma "
            "(Ulaganja/NAV) traži zaseban parser + P/NAV pristup; nije "
            "industrijska taksonomija. API ne pomaže bez tog pristupa.",
    "BSQR": "NEMA nijednog financijskog izvješća na EHO feedu (ni PDF ni XLSX) "
            "— ne vrijedi trošiti API; čekati prvu objavu.",
    "INSP": "ZAIF — nema XLSX/PDF financijskih izvješća na EHO feedu.",
    "JNAF": "SAMO PDF izvješća na EHO (nema TFI XLSX) — kandidat za API "
            "ekstrakciju (FY2025 godišnje PDF postoji).",
    "UCG":  "Strani izdavatelj (UniCredit, Milano) — ne objavljuje TFI/EHO "
            "obrasce; izvješća su talijanska/engleska PDF na vlastitim "
            "stranicama. Kandidat za API ekstrakciju iz PDF-a.",
}


def main() -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
          SELECT c.ticker, c.name, c.sector, c.is_live,
                 (SELECT MAX(fiscal_year) FROM financials f
                  WHERE f.company_id=c.id AND f.period_type='annual') fy,
                 (SELECT COUNT(DISTINCT (f.fiscal_year, f.period_type)) FROM filings f
                  WHERE f.company_id=c.id AND f.period_type IN ('q1','h1','9m','q4')
                  AND f.status IN ('validated','needs_review')) nq,
                 (SELECT MAX(f.fiscal_year*10 + CASE f.period_type
                     WHEN 'q1' THEN 1 WHEN 'h1' THEN 2 WHEN '9m' THEN 3 ELSE 4 END)
                  FROM filings f WHERE f.company_id=c.id
                  AND f.period_type IN ('q1','h1','9m')
                  AND f.status IN ('validated','needs_review')) last_q
          FROM companies c ORDER BY c.is_live DESC, c.ticker""")
        rows = cur.fetchall()
    live = [r for r in rows if r[3]]
    dead = [r for r in rows if not r[3]]
    lines = ["# Inventura pokrivenosti — bez ijednog API poziva",
             "",
             f"**Punih analiza: {len(live)}** | market_only: {len(dead)}",
             "",
             "## Pune analize (godišnje financije u bazi, valuacija v2.1 + pokazatelji)",
             "",
             "| Ticker | Sektor | Zadnji FY | Interim perioda | Napomena |",
             "|---|---|---|---|---|"]
    for t, n, s, _, fy, nq, last_q in live:
        note = ""
        if s in ("bank", "insurance"):
            note = ("nadzorni obrazac — interim (FINREP layout) traži zaseban "
                    "parser; TTM = n/p, FY s oznakom" if nq == 0 else "")
        elif nq == 0:
            note = "bez kvartala na EHO — TTM n/p, FY s oznakom"
        lines.append(f"| {t} | {s or 'n/p'} | {fy or '—'} | {nq} | {note} |")
    lines += ["", "## market_only — što TOČNO fali (za odluku isplati li se API)",
              "",
              "| Ticker | Ime | Što fali |", "|---|---|---|"]
    for t, n, s, _, fy, nq, last_q in dead:
        lines.append(f"| {t} | {n[:40]} | {MISSING.get(t, 'n/p — provjeriti EHO')} |")
    lines += ["",
              "Napomena: sve gore ekstrahirano je deterministički iz EHO XLSX "
              "obrazaca (TFI-POD, nadzorni bankovni, financijsko-uslužna "
              "varijanta) kroz validate gate — 0 API poziva. Skenirani PDF-ovi "
              "(bivši CTKS/KTJV problem) više nisu blokada jer izdavatelji od "
              "FY2025 objavljuju XLSX."]
    out = "\n".join(lines)
    with open("docs/inventura_bez_api.md", "w", encoding="utf-8") as f:
        f.write(out + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
