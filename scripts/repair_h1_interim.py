"""M52: popravak interim serija u koje su ušle SOLO (KN) brojke.

Incident 30.07.2026.: za izdavatelje koji su isti dan objavili i konsolidirani
i nekonsolidirani polugodišnji TFI XLSX, watcher je (sort po datumu objave)
stvorio drugi filing sa SOLO dokumentom; njegov ingest je prepisao retke
konsolidiranog filinga (basis u ekstrakciji je bio hardkodiran 'consolidated')
pa su TTM/EV pokazatelji grupe računati na brojkama matice (12 tickera,
npr. KOEI EV/EBITDA 17,9x umjesto ~10x).

Skripta za svaki ticker koji u EHO feedu ima KONSOLIDIRANI interim XLSX:
ponovno uveze taj XLSX (load_extraction briše i prepisuje retke filinga)
i validira. Idempotentno — ispravni filingi dobiju iste vrijednosti.
Na kraju ispiše tickere kojima su se vrijednosti stvarno promijenile
(kandidati za revalorizaciju + regen).
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import eho  # noqa: E402
from src.db import get_conn  # noqa: E402
from src.validator import validate_filing  # noqa: E402
from scripts.parse_tfi_universe import LABEL_TO_PT, ingest_tfi_xlsx  # noqa: E402


def _company_id(cur, ticker):
    cur.execute("SELECT id FROM companies WHERE ticker=%s", (ticker,))
    r = cur.fetchone()
    return r[0] if r else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lookback-days", type=int, default=10)
    ap.add_argument("--tickers", default="",
                    help="opcionalni filter, zarezom; prazno = svi iz feeda")
    args = ap.parse_args()
    only = {t.strip().upper() for t in args.tickers.split(",") if t.strip()}

    d = eho.feed("financialReports",
                 date_from=(date.today() - timedelta(days=args.lookback_days)).isoformat(),
                 date_to=date.today().isoformat())
    kons: dict[tuple, dict] = {}
    for x in d.get("items") or []:
        t = x.get("issuerCode") or x.get("ticker")
        pt = LABEL_TO_PT.get(str(x.get("period")))
        if (not t or pt in (None, "annual") or not x.get("consolidated")
                or x.get("documentType") != "XLSX" or not x.get("documentLink")):
            continue
        if only and t not in only:
            continue
        key = (t, x.get("year"), pt)
        # najnovija objava pobjeđuje
        if key not in kons or (x.get("publishDate") or "") > (kons[key].get("publishDate") or ""):
            kons[key] = x

    changed: list[str] = []
    with get_conn() as conn:
        cur = conn.cursor()
        for (t, year, pt), x in sorted(kons.items()):
            cid = _company_id(cur, t)
            if cid is None:
                continue
            cur.execute(
                """SELECT f.id FROM filings f WHERE f.company_id=%s
                     AND f.doc_type='financial_report' AND f.fiscal_year=%s
                     AND f.period_type=%s AND f.basis='consolidated'""",
                (cid, year, pt))
            row = cur.fetchone()
            if not row:
                continue  # serija ne postoji — regularni sync će je stvoriti
            fid = row[0]
            cur.execute("""SELECT item, value_eur FROM financials
                           WHERE filing_id=%s AND item IN ('revenue','ebit')""", (fid,))
            before = dict(cur.fetchall())
            url = (x.get("documentLink") or "").replace("\\/", "/")
            try:
                new_fid, parsed = ingest_tfi_xlsx(
                    conn, t, url, year, pt, cumulative=True,
                    published_at=(x.get("publishDate") or "")[:10] or None,
                    expect_consolidated=True)
            except Exception as e:  # noqa: BLE001 — jedan ticker ne ruši popravak
                conn.rollback()
                print(f"[repair] {t} FY{year} {pt}: FAILED {type(e).__name__}: {e}")
                continue
            if new_fid is None:
                conn.rollback()
                reason = (parsed or {}).get("skip_reason") if isinstance(parsed, dict) else None
                print(f"[repair] {t} FY{year} {pt}: preskočeno ({reason or 'nije TFI-POD'})")
                continue
            res = validate_filing(conn, new_fid)
            cur.execute("""SELECT item, value_eur FROM financials
                           WHERE filing_id=%s AND item IN ('revenue','ebit')""", (new_fid,))
            after = dict(cur.fetchall())
            diff = any(before.get(k) != after.get(k) for k in set(before) | set(after))
            conn.commit()
            tag = "PROMIJENJENO" if diff else "bez promjene"
            print(f"[repair] {t} FY{year} {pt}: filing {new_fid} -> {res['status']} ({tag})")
            if diff:
                changed.append(t)
    print("PROMIJENJENI TICKERI: " + (",".join(sorted(set(changed))) or "-"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
