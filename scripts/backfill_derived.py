#!/usr/bin/env python3
"""M39: re-izvedi izvedene stavke (ebit, ebitda, amortizacija, net_debt, FCF…)
nad SVIM postojećim filinzima prema proširenim pravilima u normalize.derive_items.

Uzrok: zadnji godišnji filing ponekad objavi samo dio stavki (npr. RIVP FY2025
ima prihod/opex/amortizaciju ali ne EBIT/EBITDA), pa valuacija posegne za
starijom godinom koja te stavke ima — fer vrijednost tiho počiva na
zastarjelom ulazu (vidi src/freshness.py). Ovaj backfill dopunjava izvedene
stavke IZ VEĆ OBJAVLJENIH (reported) vrijednosti istog filinga — ništa se ne
izmišlja, samo determinstički identiteti; upisuje se is_reported=FALSE,
source='computed'.

Idempotentno: dodaje samo stavke kojih u filingu još nema (bilo reported bilo
izvedenih). Pokretanje:  python -m scripts.backfill_derived [--apply]
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from src.canonical import DERIVED_ITEMS  # noqa: E402
from src.db import get_conn  # noqa: E402
from src.normalize import derive_items  # noqa: E402


def main() -> int:
    apply = "--apply" in sys.argv
    added: list[str] = []
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT f.filing_id, f.company_id, f.fiscal_year,
                              f.period_type, f.basis, c.sector
                       FROM financials f JOIN companies c ON c.id=f.company_id""")
        filings = cur.fetchall()
        for fid, cid, fy, pt, basis, sector in filings:
            is_financial = sector in ("bank", "insurance")
            # reported (objavljene) vrijednosti ovog filinga
            cur.execute("""SELECT item, value_eur FROM financials
                           WHERE filing_id=%s AND is_reported=TRUE
                                 AND value_eur IS NOT NULL""", (fid,))
            reported = {i: float(v) for i, v in cur.fetchall()}
            # već postojeće stavke (da ne dupliramo)
            cur.execute("SELECT item FROM financials WHERE filing_id=%s", (fid,))
            existing = {r[0] for r in cur.fetchall()}
            for item, value_eur in derive_items(reported, is_financial).items():
                if item in existing:
                    continue
                statement = DERIVED_ITEMS.get(item)
                if statement is None:
                    continue
                added.append(f"{fid}:{fy}{pt}:{item}={value_eur/1e6:.2f}M")
                if apply:
                    cur.execute(
                        """INSERT INTO financials (filing_id, company_id,
                             fiscal_year, period_type, basis, statement, item,
                             value_raw, value_eur, confidence, source_page,
                             is_reported)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,NULL,%s,NULL,
                                   'computed (M39 backfill izvedeno)',FALSE)""",
                        (fid, cid, fy, pt, basis, statement, item, value_eur))
        if not apply:
            conn.rollback()
    verb = "UPISANO" if apply else "bi se dodalo (dry-run, dodaj --apply)"
    print(f"[backfill_derived] {verb}: {len(added)} izvedenih stavki")
    for a in added[:60]:
        print("   ", a)
    if len(added) > 60:
        print(f"    … +{len(added) - 60}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
