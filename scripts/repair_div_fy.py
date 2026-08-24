#!/usr/bin/env python3
"""M74: popravak fiskalne godine dividendi kojima je ex-datum skliznuo u
siječanj (odluka GS iz prosinca), pa je konvencija fiscal_year =
ex_date.year - 1 preskočila godinu (HPB: izglasana 21,83 € ex 5.1.2026.
dobila FY2025 umjesto FY2024, dok prijedlog iste dividende ex 22.12.2025.
uredno stoji na FY2024).

Pravilo (idempotentno): redak s ex-datumom u siječnju nasljeđuje fiskalnu
godinu ranijeg retka ISTE firme, ISTE klase i ISTOG iznosa čiji je ex-datum
unutar prethodnih 60 dana — ali samo kad je razlika točno +1 godina (uvjet
čini ponovno pokretanje no-opom). Nakon popravka se za pogođene firme
ponovno klasificiraju isplate (payout_type/ratio) i ponovno izvodi godišnji
dps u financials.

Pokretanje: kroz db-sync workflow (div_fy_repair=true) nad ZSE_DSN, ili
lokalno: python -m scripts.repair_div_fy
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402
from src.dividend_sustainability import classify_company, ensure_schema  # noqa: E402
from src.dividends import upsert_dps_financials  # noqa: E402

REPAIR_SQL = """
    UPDATE dividends d
       SET fiscal_year = p.fiscal_year,
           classified_reason = COALESCE(d.classified_reason || '; ', '')
             || 'M74: fiskalna godina naslijeđena od objave '
             || p.ex_date::text || ' (siječanjski ex-datum)'
      FROM dividends p
     WHERE d.company_id = p.company_id
       AND d.class_ticker = p.class_ticker
       AND d.amount_eur = p.amount_eur
       AND d.id <> p.id
       AND EXTRACT(MONTH FROM d.ex_date) = 1
       AND p.ex_date >= d.ex_date - INTERVAL '60 days'
       AND p.ex_date < d.ex_date
       AND p.fiscal_year IS NOT NULL
       AND d.fiscal_year = p.fiscal_year + 1
    RETURNING d.id, d.company_id, d.class_ticker, d.amount_eur,
              d.ex_date, d.fiscal_year
"""


def main() -> int:
    with get_conn() as conn:
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute(REPAIR_SQL)
            fixed = cur.fetchall()
            if not fixed:
                print("[div-fy] nema redaka za popravak — sve konzistentno")
                conn.commit()
                return 0
            company_ids = sorted({r[1] for r in fixed})
            for _id, cid, ctk, amt, ex, fy in fixed:
                print(f"[div-fy] popravljen red id={_id}: {ctk} {amt} € "
                      f"ex {ex} -> FY{fy}")
            cur.execute("SELECT id, ticker FROM companies WHERE id = ANY(%s)",
                        (company_ids,))
            tickers = dict(cur.fetchall())
        conn.commit()
        # reklasifikacija + ponovna izvedba godišnjeg dps-a za pogođene firme
        for cid in company_ids:
            n = classify_company(conn, cid)
            upsert_dps_financials(conn, tickers[cid], verbose=False)
            print(f"[div-fy] {tickers[cid]}: {n} isplata reklasificirano, "
                  "dps ponovno izveden")
        # prijedlozi se NE klasificiraju — očisti zaostale (stare) klasifikacije
        # na prijedlozima pogođenih firmi da UI ne prikazuje zastarjeli payout
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE dividends
                      SET payout_type = NULL, payout_ratio = NULL
                    WHERE company_id = ANY(%s) AND div_type ILIKE '%%rijedlog%%'
                      AND (payout_type IS NOT NULL OR payout_ratio IS NOT NULL)""",
                (company_ids,))
            if cur.rowcount:
                print(f"[div-fy] očišćene zaostale klasifikacije na "
                      f"{cur.rowcount} prijedloga")
        conn.commit()
    print(f"[div-fy] GOTOVO: {len(fixed)} redaka, firme: "
          f"{', '.join(sorted(tickers.values()))} — pokreni recompute + regen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
