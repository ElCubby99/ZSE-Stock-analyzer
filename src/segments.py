"""IFRS 8 segmenti: API ekstrakcija -> segment_financials + EBITDA reconciliation.

Tok (SOTP korak 1):
  1. extract_segments (src/extract.py) nad sliceom bilješke o segmentima
     (+ stranice izvješća uprave za metrike koje bilješka ne objavljuje),
  2. load: pivot redaka (segment, metric) -> jedan red po segmentu u
     segment_financials, vezan na POSTOJEĆI filing (company, fy, annual,
     basis, doc_type='financial_report'). value = value_raw × reporting_scale.
     Briše se i ponovno upisuje SAMO kanonske ključeve koje ekstrakcija nosi —
     izvedeni ključevi (npr. 'tourism_hup' iz seed_verified) se NE diraju.
  3. reconciliation: Σ segment EBITDA (kanonski ključevi) vs grupna EBITDA iz
     financials; |plug| > 15% -> filing status 'needs_review' (nikad ne
     podiže status natrag u 'validated').

Napomena o prazninama: metrika koju izvor ne objavljuje ostaje NULL — radije
prazno (i needs_review na reconciliationu) nego izvedeno/izmišljeno.

CLI:
  python -m src.segments extract --text data/reports/adrs_2025_seg_slice.txt
  python -m src.segments load --json data/reports/adrs_2025_segments.json
"""
from __future__ import annotations

import argparse
import json
import sys

from .db import get_conn

CANONICAL_KEYS = ("tourism", "insurance", "aquaculture", "energy")
PLUG_THRESHOLD = 0.15  # |Σ segmenata − grupa| / grupa iznad ovoga -> needs_review


def _find_filing(cur, meta: dict) -> tuple[int, int]:
    """(filing_id, company_id) postojećeg filinga na koji se segmenti vežu."""
    cur.execute("SELECT id FROM companies WHERE ticker = %s", (meta["company_ticker"],))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"nepoznat ticker: {meta['company_ticker']}")
    company_id = row[0]
    cur.execute(
        """SELECT id FROM filings
           WHERE company_id=%s AND fiscal_year=%s AND period_type=%s AND basis=%s
             AND doc_type='financial_report'""",
        (company_id, meta["fiscal_year"], meta["period_type"], meta["basis"]),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(
            f"nema filinga {meta['company_ticker']} {meta['fiscal_year']} "
            f"{meta['period_type']}/{meta['basis']} — prvo pokreni 'ingest extract'."
        )
    return row[0], company_id


def load_segments(conn, extraction: dict) -> tuple[int, int]:
    """Upsert segmenata; vrati (filing_id, company_id)."""
    meta = extraction["meta"]
    scale = meta.get("reporting_scale", 1)
    cur = conn.cursor()
    filing_id, company_id = _find_filing(cur, meta)

    # pivot: segment -> {metric: (value_eur, source_page, confidence, note)}
    seg: dict[str, dict] = {}
    for it in extraction.get("items") or []:
        k = it["segment_key"]
        if k not in CANONICAL_KEYS:
            continue
        val = it["value_raw"] * scale if it["value_raw"] is not None else None
        seg.setdefault(k, {})[it["metric"]] = (
            val, it.get("source_page", ""), it.get("confidence", 0.0),
            it.get("note", ""),
        )

    n = 0
    for k, metrics in seg.items():
        present = {m: v for m, v in metrics.items() if v[0] is not None}
        conf = min((v[2] for v in present.values()), default=0.0)
        src = "; ".join(
            f"{m}: {v[1]} (conf {v[2]}{', ' + v[3] if v[3] else ''})"
            for m, v in metrics.items()
        )
        cur.execute(
            """DELETE FROM segment_financials
               WHERE filing_id=%s AND segment_key=%s""", (filing_id, k))
        cur.execute(
            """INSERT INTO segment_financials
                 (filing_id, company_id, fiscal_year, period_type, basis,
                  segment_key, revenue, ebitda, net_result, confidence, source_page)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (filing_id, company_id, meta["fiscal_year"], meta["period_type"],
             meta["basis"], k,
             metrics.get("revenue", (None,))[0],
             metrics.get("ebitda", (None,))[0],
             metrics.get("net_result", (None,))[0],
             conf, src),
        )
        n += 1
    print(f"Upisano {n} segmenata za filing {filing_id} "
          f"({meta['company_ticker']} {meta['fiscal_year']}, skala {scale}).")
    for f in extraction.get("flags") or []:
        print(f"  [flag] {f}")
    return filing_id, company_id


def reconcile_segment_ebitda(conn, filing_id: int, company_id: int,
                             fiscal_year: int) -> None:
    """Σ segment EBITDA (kanonski ključevi) vs grupna EBITDA; |plug|>15% -> needs_review."""
    cur = conn.cursor()
    cur.execute(
        """SELECT segment_key, ebitda FROM segment_financials
           WHERE filing_id=%s AND segment_key = ANY(%s)""",
        (filing_id, list(CANONICAL_KEYS)),
    )
    rows = cur.fetchall()
    seg_sum = sum(float(r[1]) for r in rows if r[1] is not None)
    missing = [r[0] for r in rows if r[1] is None]
    cur.execute(
        """SELECT fin.value_eur FROM financials fin
           WHERE fin.filing_id=%s AND fin.item='ebitda'""", (filing_id,))
    row = cur.fetchone()
    group = float(row[0]) if row and row[0] is not None else None

    print("\nRECONCILIATION Σ segment EBITDA vs grupna EBITDA:")
    if group is None:
        print("  grupna EBITDA nije u financials — provjera preskočena.")
        return
    plug = group - seg_sum
    pct = plug / group if group else 0.0
    print(f"  Σ segmenata: {seg_sum:,.0f}  |  grupa: {group:,.0f}  "
          f"|  plug: {plug:,.0f} ({pct * 100:.1f}%)")
    if missing:
        print(f"  segmenti bez EBITDA (NULL): {', '.join(missing)}")
    if abs(pct) > PLUG_THRESHOLD:
        cur.execute(
            "UPDATE filings SET status='needs_review' WHERE id=%s AND status<>'needs_review'",
            (filing_id,))
        print(f"  |plug| > {PLUG_THRESHOLD:.0%} -> filing {filing_id} status: needs_review")
    else:
        print(f"  |plug| <= {PLUG_THRESHOLD:.0%} -> OK")


def _run(extraction: dict) -> None:
    with get_conn() as conn:
        filing_id, company_id = load_segments(conn, extraction)
        reconcile_segment_ebitda(conn, filing_id, company_id,
                                 extraction["meta"]["fiscal_year"])


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="IFRS 8 segmenti -> segment_financials")
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("extract", help="API ekstrakcija iz teksta -> load -> reconcile")
    pe.add_argument("--text", required=True)
    pe.add_argument("--save-json", default=None,
                    help="spremi sirovu ekstrakciju u JSON (audit)")

    pl = sub.add_parser("load", help="load iz spremljenog extraction JSON-a")
    pl.add_argument("--json", required=True)

    a = p.parse_args(argv)
    if a.cmd == "extract":
        from .extract import extract_segments
        with open(a.text, encoding="utf-8") as f:
            text = f.read()
        extraction = extract_segments(text)
        if a.save_json:
            with open(a.save_json, "w", encoding="utf-8") as f:
                json.dump(extraction, f, ensure_ascii=False, indent=2)
            print(f"Ekstrakcija spremljena u {a.save_json}")
        _run(extraction)
    else:
        with open(a.json, encoding="utf-8") as f:
            extraction = json.load(f)
        _run(extraction)
    return 0


if __name__ == "__main__":
    sys.exit(main())
