#!/usr/bin/env python3
"""M35: sinkronizacija SADRŽAJNIH tablica lokalna (master) -> produkcijska baza.

Kontekst: kurirani podaci (ekstrakcije, klasifikacije dividendi, holdings/JV,
povijesna izvješća) nastaju u lokalnoj razvojnoj bazi, a daily pipeline na
Actionsu radi nad produkcijskim Supabaseom — bez sinka bi produkcijski regen
računao bez kuriranih ulaza i pregazio exporte.

Tok: `dump` (lokalno) -> data/sync/content_dump.json.gz (commit u repo) ->
`apply` (na Actionsu, ZSE_DSN) upsert u produkciju po PRIRODNIM ključevima
(ID-jevi se NE prenose; firma se mapira po tickeru, filing po
(ticker, doc_type, fy, period, basis), financials se za svaki filing
ZAMIJENE lokalnom verzijom — lokalna baza je izvor istine za sadržaj).

NE dira: prices_eod, index/bond/fund tablice, pipeline_runs, api_usage,
valuations (žive na produkciji iz daily runova).

Pokretanje:
  python -m scripts.db_sync dump
  python -m scripts.db_sync apply          # cilja bazu iz ZSE_DSN/config
"""
from __future__ import annotations

import gzip
import json
import pathlib
import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402

DUMP = pathlib.Path(__file__).resolve().parents[1] / "data" / "sync" / "content_dump.json.gz"

FILING_KEY = ("doc_type", "fiscal_year", "period_type", "basis")
FILING_ATTRS = ("audited", "cumulative", "period_start", "period_end",
                "currency", "reporting_scale", "source_url", "published_at",
                "status")
FIN_COLS = ("statement", "item", "value_raw", "value_eur", "confidence",
            "source_page", "is_reported")
COMPANY_COLS = ("sector", "tier", "holding_type", "nace", "is_live",
                "data_limited", "onboarding_status")
HOLDING_COLS = ("ownership_pct", "listed", "valuation_basis", "segment_key",
                "default_multiple", "is_insurance", "as_of", "source_page",
                "confidence", "associate_ni", "jv_book_value_eur",
                "jv_book_source")
DIV_COLS = ("payout_type", "payout_ratio", "classified_reason")
SC_COLS = ("isin", "class_type", "shares_issued", "treasury_shares",
           "has_voting", "dividend_note", "is_primary_line")


def _j(v):
    import datetime
    import decimal
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return float(v)
    return v


def dump() -> int:
    out = {"companies": [], "filings": [], "dividends": [], "holdings": [],
           "dividend_policies": [], "growth_estimates": [],
           "valuation_changelog": [], "share_classes": []}
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(f"""SELECT ticker, {', '.join(COMPANY_COLS)}
                        FROM companies ORDER BY ticker""")
        for row in cur.fetchall():
            out["companies"].append([_j(x) for x in row])

        cur.execute(f"""
          SELECT c.ticker, f.{', f.'.join(FILING_KEY)}, f.{', f.'.join(FILING_ATTRS)}, f.id
          FROM filings f JOIN companies c ON c.id=f.company_id ORDER BY f.id""")
        filings = cur.fetchall()
        for row in filings:
            *attrs, fid = row
            cur.execute(f"""SELECT {', '.join(FIN_COLS)} FROM financials
                            WHERE filing_id=%s ORDER BY id""", (fid,))
            fins = [[_j(x) for x in r] for r in cur.fetchall()]
            out["filings"].append({"k": [_j(x) for x in attrs], "fin": fins})

        # kanonski registar klasa (broj dionica, trezorske, prava) — kuriran
        cur.execute(f"""SELECT ticker, {', '.join(SC_COLS)}
                        FROM share_classes ORDER BY ticker""")
        out["share_classes"] = [[_j(x) for x in r] for r in cur.fetchall()]

        cur.execute(f"""SELECT class_ticker, ex_date, amount_eur,
                               {', '.join(DIV_COLS)}
                        FROM dividends ORDER BY id""")
        out["dividends"] = [[_j(x) for x in r] for r in cur.fetchall()]

        cur.execute(f"""
          SELECT pc.ticker, h.held_name,
                 (SELECT ticker FROM companies WHERE id=h.held_company_id),
                 {', '.join('h.' + c for c in HOLDING_COLS)}
          FROM holdings h JOIN companies pc ON pc.id=h.parent_company_id
          ORDER BY h.id""")
        out["holdings"] = [[_j(x) for x in r] for r in cur.fetchall()]

        cur.execute("""SELECT c.ticker, dp.policy_type, dp.params::text,
                              dp.source, dp.extracted_on
                       FROM dividend_policies dp
                       JOIN companies c ON c.id=dp.company_id""")
        out["dividend_policies"] = [[_j(x) for x in r] for r in cur.fetchall()]

        cur.execute("""SELECT c.ticker, g.fiscal_year, g.g1, g.horizon_years,
                              g.method, g.rule, g.drivers, g.basis,
                              g.signals::text, g.confidence, g.source
                       FROM growth_estimates g
                       JOIN companies c ON c.id=g.company_id""")
        out["growth_estimates"] = [[_j(x) for x in r] for r in cur.fetchall()]

        cur.execute("""SELECT c.ticker, v.changed_on, v.old_low, v.old_high,
                              v.new_low, v.new_high, v.reason, v.kind
                       FROM valuation_changelog v
                       JOIN companies c ON c.id=v.company_id ORDER BY v.id""")
        out["valuation_changelog"] = [[_j(x) for x in r] for r in cur.fetchall()]

    DUMP.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(DUMP, "wt", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"[sync] dump: {len(out['filings'])} filinga, "
          f"{sum(len(f['fin']) for f in out['filings'])} financials, "
          f"{len(out['dividends'])} dividendi, {len(out['holdings'])} holdinga "
          f"-> {DUMP} ({DUMP.stat().st_size // 1024} KB)")
    return 0


def apply() -> int:
    with gzip.open(DUMP, "rt", encoding="utf-8") as f:
        d = json.load(f)
    stats = {"companies": 0, "filings_new": 0, "filings_upd": 0,
             "fin_rows": 0, "dividends": 0, "holdings": 0}
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT ticker, id FROM companies")
        cid_of = dict(cur.fetchall())

        for row in d["companies"]:
            ticker, *vals = row
            if ticker not in cid_of:
                continue   # nove firme se onboardaju kroz pipeline, ne sync
            sets = ", ".join(f"{c}=%s" for c in COMPANY_COLS)
            cur.execute(f"UPDATE companies SET {sets} WHERE ticker=%s",
                        (*vals, ticker))
            stats["companies"] += cur.rowcount

        for row in d.get("share_classes", []):
            ticker, *vals = row
            sets = ", ".join(f"{c}=%s" for c in SC_COLS)
            cur.execute(f"UPDATE share_classes SET {sets} WHERE ticker=%s",
                        (*vals, ticker))
            stats["share_classes"] = stats.get("share_classes", 0) + cur.rowcount

        for frec in d["filings"]:
            ticker, doc_type, fy, pt, basis, *attrs = frec["k"]
            cid = cid_of.get(ticker)
            if cid is None:
                continue
            cur.execute(
                """SELECT id FROM filings WHERE company_id=%s AND doc_type=%s
                   AND fiscal_year=%s AND period_type=%s AND basis=%s""",
                (cid, doc_type, fy, pt, basis))
            r = cur.fetchone()
            if r:
                fid = r[0]
                sets = ", ".join(f"{c}=%s" for c in FILING_ATTRS)
                cur.execute(f"UPDATE filings SET {sets} WHERE id=%s",
                            (*attrs, fid))
                stats["filings_upd"] += 1
            else:
                cols = "company_id, doc_type, fiscal_year, period_type, basis, " \
                       + ", ".join(FILING_ATTRS)
                ph = ", ".join(["%s"] * (5 + len(FILING_ATTRS)))
                cur.execute(
                    f"INSERT INTO filings ({cols}) VALUES ({ph}) RETURNING id",
                    (cid, doc_type, fy, pt, basis, *attrs))
                fid = cur.fetchone()[0]
                stats["filings_new"] += 1
            # financials: lokalna verzija je istina — zamijeni u cijelosti.
            # execute_values: 24k pojedinačnih INSERT-a preko mreže traje
            # >15 min (Supabase RTT po upitu) — batch spušta na sekunde.
            from psycopg2.extras import execute_values
            cur.execute("DELETE FROM financials WHERE filing_id=%s", (fid,))
            if frec["fin"]:
                execute_values(
                    cur,
                    f"""INSERT INTO financials (filing_id, company_id,
                          fiscal_year, period_type, basis,
                          {', '.join(FIN_COLS)}) VALUES %s""",
                    [(fid, cid, fy, pt, basis, *fin) for fin in frec["fin"]])
                stats["fin_rows"] += len(frec["fin"])

        for row in d["dividends"]:
            ct, ex_date, amount, ptype, pratio, reason = row
            cur.execute(
                """UPDATE dividends SET payout_type=%s, payout_ratio=%s,
                     classified_reason=%s
                   WHERE class_ticker=%s AND ex_date=%s AND amount_eur=%s""",
                (ptype, pratio, reason, ct, ex_date, amount))
            stats["dividends"] += cur.rowcount

        for row in d["holdings"]:
            pticker, held_name, held_ticker, *vals = row
            pcid = cid_of.get(pticker)
            if pcid is None:
                continue
            hcid = cid_of.get(held_ticker) if held_ticker else None
            cur.execute("""SELECT id FROM holdings
                           WHERE parent_company_id=%s AND held_name=%s""",
                        (pcid, held_name))
            r = cur.fetchone()
            sets = ", ".join(f"{c}=%s" for c in HOLDING_COLS)
            if r:
                cur.execute(f"""UPDATE holdings SET held_company_id=%s, {sets}
                                WHERE id=%s""", (hcid, *vals, r[0]))
            else:
                cols = "parent_company_id, held_company_id, held_name, " \
                       + ", ".join(HOLDING_COLS)
                ph = ", ".join(["%s"] * (3 + len(HOLDING_COLS)))
                cur.execute(f"INSERT INTO holdings ({cols}) VALUES ({ph})",
                            (pcid, hcid, held_name, *vals))
            stats["holdings"] += 1

        for row in d["dividend_policies"]:
            ticker, ptype, params, source, extracted = row
            cid = cid_of.get(ticker)
            if cid is None:
                continue
            cur.execute(
                """INSERT INTO dividend_policies (company_id, policy_type,
                     params, source, extracted_on)
                   VALUES (%s,%s,%s::jsonb,%s,%s)
                   ON CONFLICT (company_id) DO UPDATE SET
                     policy_type=EXCLUDED.policy_type, params=EXCLUDED.params,
                     source=EXCLUDED.source, extracted_on=EXCLUDED.extracted_on""",
                (cid, ptype, params, source, extracted))

        for row in d["growth_estimates"]:
            ticker, fy, g1, hz, method, rule, drivers, basis, signals, conf, src = row
            cid = cid_of.get(ticker)
            if cid is None:
                continue
            cur.execute(
                """INSERT INTO growth_estimates (company_id, fiscal_year, g1,
                     horizon_years, method, rule, drivers, basis, signals,
                     confidence, source)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                   ON CONFLICT (company_id, fiscal_year, method) DO UPDATE SET
                     g1=EXCLUDED.g1, rule=EXCLUDED.rule, drivers=EXCLUDED.drivers,
                     basis=EXCLUDED.basis, signals=EXCLUDED.signals,
                     confidence=EXCLUDED.confidence, source=EXCLUDED.source""",
                (cid, fy, g1, hz, method, rule, drivers, basis, signals, conf, src))

        for row in d.get("valuation_changelog", []):
            ticker, changed_on, ol, oh, nl, nh, reason, kind = row
            cid = cid_of.get(ticker)
            if cid is None:
                continue
            cur.execute(
                """INSERT INTO valuation_changelog (company_id, changed_on,
                     old_low, old_high, new_low, new_high, reason, kind)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (company_id, changed_on, reason) DO NOTHING""",
                (cid, changed_on, ol, oh, nl, nh, reason, kind))

    print(f"[sync] apply: {stats}")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dump":
        sys.exit(dump())
    if cmd == "apply":
        sys.exit(apply())
    print(__doc__)
    sys.exit(2)
