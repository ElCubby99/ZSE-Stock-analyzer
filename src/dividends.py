"""Dividende s EHO-a -> tablica dividends + godišnji dps u financials.

Tok (KORAK 2B iz runbooka, dio "dividende"):
  1. issuerNews feed za ticker (tipovi vezani uz skupštine/dividende),
  2. na svakoj objavi parsiraj strukturirane "Informacije o dividendi" blokove
     (po KLASI: ADRS i ADRS2 zasebno),
  3. upsert u dividends (idempotentno po (class_ticker, ex_date, amount)),
  4. izvedi godišnji dps po firmi i upiši u filings(doc_type='dividend') +
     financials(item='dps') da ga build_ctx/data('dps') vidi (DDM gate).

KONVENCIJA fiscal_year = ex_date.year - 1 (dividenda izglasana na GS u godini
N isplaćuje se iz dobiti godine N-1). Za CROS 2026 to potvrđuje i sama objava
("...isplate dividende ... iz neto dobiti ostvarene u 2025. godini",
eho.zse.hr/obavijesti-izdavatelja/view/65796). Konvencija je zabilježena u
source_page svakog dps retka. Ako je u istoj godini više izglasanih isplata
(npr. CROS 2024: ožujak + lipanj), dps za fiskalnu godinu je njihov ZBROJ.

U financials ulaze SAMO 'Izglasana dividenda' (ne prijedlozi ni predujmi bez
izglasavanja — konzervativno; predujmi se ipak čuvaju u dividends tablici).

CLI:
  python -m src.dividends ADRS CROS --from 2024-01-01
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import date

from . import eho
from .db import get_conn

# Tipovi objava koji nose dividendne blokove/odluke (eho feed dictionary):
#  9 = Predujam dividende, 13 = Obavijest o skupštini (odluke GS),
# 14 = Obavijest o dividendi. Uz to hvatamo i sve s 'dividend' u naslovu.
DIVIDEND_NEWS_TYPES = {9, 13, 14}
DPS_CONFIDENCE = 0.9  # ispod MIN_CONFIDENCE=0.85 ne bi prošlo data-gate


def scrape_dividends(ticker: str, date_from: str, date_to: str | None = None,
                     verbose: bool = True) -> list[eho.DividendInfo]:
    date_to = date_to or date.today().isoformat()
    d = eho.feed("issuerNews", ticker=ticker, date_from=date_from, date_to=date_to)
    found: list[eho.DividendInfo] = []
    seen_links: set[str] = set()
    for it in d.get("items") or []:
        title = (it.get("title") or "")
        if it.get("type") not in DIVIDEND_NEWS_TYPES and "dividend" not in title.lower():
            continue
        link = it.get("link")
        if not link or link in seen_links:
            continue
        seen_links.add(link)
        try:
            text = eho.page_text(link)
        except Exception as e:  # jedna neispravna objava ne ruši scrape
            print(f"  [warn] {link}: {e}", file=sys.stderr)
            continue
        blocks = eho.parse_dividend_blocks(text, link)
        if blocks and verbose:
            print(f"  {it.get('publishDate','')[:10]} {title[:70]}")
            for b in blocks:
                print(f"    -> {b.class_ticker}: {b.amount_eur} EUR ({b.div_type}), "
                      f"ex {b.ex_date}, isplata {b.payment_date}")
        found.extend(blocks)
    return found


def store_dividends(conn, company_ticker: str, divs: list[eho.DividendInfo]) -> int:
    """Upsert događaja u dividends. Vraća broj novih redaka."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM companies WHERE ticker = %s", (company_ticker,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"nepoznat ticker u companies: {company_ticker}")
        company_id = row[0]
        new = 0
        for b in divs:
            cur.execute("SELECT id FROM share_classes WHERE ticker = %s", (b.class_ticker,))
            sc = cur.fetchone()
            fiscal_year = b.ex_date.year - 1 if b.ex_date else None
            cur.execute(
                """
                INSERT INTO dividends (company_id, share_class_id, class_ticker,
                    fiscal_year, amount_eur, div_type, ex_date, record_date,
                    payment_date, source_url)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (class_ticker, ex_date, amount_eur) DO NOTHING
                """,
                (company_id, sc[0] if sc else None, b.class_ticker, fiscal_year,
                 b.amount_eur, b.div_type, b.ex_date, b.record_date,
                 b.payment_date, b.source_url),
            )
            new += cur.rowcount
    return new


def upsert_dps_financials(conn, company_ticker: str, verbose: bool = True) -> None:
    """Godišnji dps (zbroj izglasanih po fiskalnoj godini) -> filings+financials.

    dps je per-share veličina PRIMARNE linije; kad klase imaju različit iznos,
    uzima se iznos primarne klase (is_primary_line), uz napomenu u source_page.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM companies WHERE ticker = %s", (company_ticker,))
        company_id = cur.fetchone()[0]
        cur.execute(
            """
            SELECT d.fiscal_year,
                   SUM(d.amount_eur)          AS dps,
                   COUNT(*)                   AS n_events,
                   MIN(d.source_url)          AS src,
                   MAX(d.ex_date)             AS last_ex
            FROM   dividends d
            LEFT JOIN share_classes sc ON sc.id = d.share_class_id
            WHERE  d.company_id = %s
              AND  d.div_type ILIKE 'Izglasana%%'
              AND  d.fiscal_year IS NOT NULL
              AND  (sc.is_primary_line IS TRUE OR d.share_class_id IS NULL)
            GROUP BY d.fiscal_year
            """,
            (company_id,),
        )
        rows = cur.fetchall()
        for fiscal_year, dps, n_events, src, last_ex in rows:
            cur.execute(
                """
                INSERT INTO filings (company_id, doc_type, fiscal_year, period_type,
                                     basis, currency, reporting_scale, source_url,
                                     published_at, status)
                VALUES (%s,'dividend',%s,'annual','consolidated','EUR',1,%s,%s,'validated')
                ON CONFLICT (company_id, doc_type, fiscal_year, period_type, basis)
                DO UPDATE SET source_url = EXCLUDED.source_url,
                              published_at = EXCLUDED.published_at
                RETURNING id
                """,
                (company_id, fiscal_year, src, last_ex),
            )
            filing_id = cur.fetchone()[0]
            cur.execute("DELETE FROM financials WHERE filing_id = %s AND item='dps'",
                        (filing_id,))
            note = (f"EHO 'Informacije o dividendi' ({n_events} izglasana isplata); "
                    f"fiscal_year=ex_date.year-1 konvencija")
            cur.execute(
                """
                INSERT INTO financials (filing_id, company_id, fiscal_year, period_type,
                    basis, statement, item, value_raw, value_eur, confidence,
                    source_page, is_reported)
                VALUES (%s,%s,%s,'annual','consolidated','income','dps',%s,%s,%s,%s,TRUE)
                """,
                (filing_id, company_id, fiscal_year, dps, dps, DPS_CONFIDENCE, note),
            )
            if verbose:
                print(f"  dps[{company_ticker} FY{fiscal_year}] = {dps} EUR "
                      f"({n_events} isplata) -> filing {filing_id}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="EHO dividende -> dividends + dps")
    p.add_argument("tickers", nargs="+")
    p.add_argument("--from", dest="date_from", default="2024-01-01")
    p.add_argument("--to", dest="date_to", default=None)
    a = p.parse_args(argv)
    with get_conn() as conn:
        for t in a.tickers:
            print(f"== {t} ==")
            divs = scrape_dividends(t, a.date_from, a.date_to)
            n = store_dividends(conn, t, divs)
            print(f"  novih događaja u dividends: {n} (ukupno parsirano {len(divs)})")
            upsert_dps_financials(conn, t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
