"""M42-A: učitaj višegodišnje godišnje financije (FY2022-2024) za 8 firmi
koje su imale samo FY2025. Ulaz: scratchpad/backfill_banks1.json,
backfill_banks2.json, backfill_nonbanks.json. Kreira godišnji filing po
(ticker, godina, basis) i upisuje financials stavke s izvorom.
"""
from __future__ import annotations

import json
import pathlib
import sys

import src.db as db

S = pathlib.Path("/tmp/claude-0/-home-user-ZSE-Stock-analyzer/"
                 "bb2e6cb3-8fb7-5416-83d2-f5f529dd7764/scratchpad")
FILES = ["backfill_banks1.json", "backfill_banks2.json", "backfill_nonbanks.json"]

BALANCE_ITEMS = {"net_debt", "total_equity", "equity_parent", "cash_and_equivalents"}


def main(apply: bool) -> int:
    data = {}
    for fn in FILES:
        p = S / fn
        if not p.exists():
            print(f"NEDOSTAJE {fn} — preskačem")
            continue
        d = json.load(open(p, encoding="utf-8"))
        for tk, yrs in d.items():
            data.setdefault(tk, {}).update(yrs)
    if not data:
        print("nema ulaznih podataka")
        return 1

    with db.get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT ticker, id FROM companies")
        cid = dict(cur.fetchall())
        n_fil, n_fin = 0, 0
        for tk in sorted(data):
            if tk not in cid:
                print(f"  {tk}: nema u companies — preskačem")
                continue
            company_id = cid[tk]
            for yr, blk in sorted(data[tk].items()):
                if not (isinstance(yr, str) and yr.isdigit() and len(yr) == 4):
                    continue  # preskoči _note i sl. ne-godišnje ključeve
                if not isinstance(blk, dict):
                    continue
                fy = int(yr)
                # DB konvencija: primarni godišnji izvještaj se vodi kao
                # 'consolidated' (i za banke koje ne konsolidiraju) — postojeći
                # FY2025 svih 8 firmi je 'consolidated', a data()/_ni_annual
                # čitaju SAMO 'consolidated'. Poravnavamo backfill s time da
                # višegodišnji trend i payout ratio (D_sust) prorade.
                basis = "consolidated"
                items = blk.get("items") or {}
                # izvedi ebitda = ebit + amortizacija (nefinancijske firme)
                ebit = (items.get("ebit") or {}).get("value_eur")
                da = (items.get("depreciation_amortization") or {}).get("value_eur")
                if ebit is not None and da is not None and "ebitda" not in items:
                    items = dict(items)
                    items["ebitda"] = {
                        "value_eur": float(ebit) + float(da),
                        "source_page": f"izvedeno: EBIT + amortizacija (FY{fy})",
                        "derived": True}
                present = {k: v for k, v in items.items()
                          if v and v.get("value_eur") is not None}
                if not present:
                    continue
                if not apply:
                    print(f"  [dry] {tk} FY{fy} ({basis}): "
                          + ", ".join(f"{k}={present[k]['value_eur']:,.0f}"
                                      for k in present))
                    continue
                # find-or-create annual filing
                cur.execute(
                    """SELECT id FROM filings WHERE company_id=%s AND fiscal_year=%s
                       AND period_type='annual' AND basis=%s LIMIT 1""",
                    (company_id, fy, basis))
                r = cur.fetchone()
                if r:
                    fid = r[0]
                else:
                    cur.execute(
                        """INSERT INTO filings (company_id, doc_type, fiscal_year,
                             period_type, basis, currency, source_url, status)
                           VALUES (%s,%s,%s,'annual',%s,'EUR',%s,'ingested')
                           RETURNING id""",
                        (company_id, "godišnje (M42 backfill)", fy, basis,
                         (blk.get("doc") or "")[:500] or "M42 backfill"))
                    fid = cur.fetchone()[0]
                    n_fil += 1
                for item, v in present.items():
                    stmt = "balance" if item in BALANCE_ITEMS else "income"
                    is_rep = not v.get("derived")
                    cur.execute(
                        """INSERT INTO financials (filing_id, company_id, fiscal_year,
                             period_type, basis, statement, item, value_eur,
                             confidence, source_page, is_reported)
                           VALUES (%s,%s,%s,'annual',%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT DO NOTHING""",
                        (fid, company_id, fy, basis, stmt, item,
                         float(v["value_eur"]), 0.9 if is_rep else 0.85,
                         (v.get("source_page") or "")[:500], is_rep))
                    n_fin += cur.rowcount
        print(f"{'UPISANO' if apply else 'DRY'}: {n_fil} filinga, {n_fin} financials")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--apply" in sys.argv))
