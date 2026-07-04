"""Točka 2 (loader): extraction dict -> normalizacija -> insert u filings+financials.

Tok:
  parse_extraction / extract_filing  ->  load_extraction(conn, extraction, source_url)
Loader NE postavlja status='validated' — to radi validator. Postavlja 'extracted'.
Re-ingest istog filinga (isti unique ključ) zamjenjuje njegove financials retke.
"""
from __future__ import annotations

from typing import Any

from . import canonical
from .normalize import derive_items, to_eur


def _get_company_id(conn, ticker: str) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM companies WHERE ticker = %s", (ticker,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Nepoznat ticker: {ticker}. Dodaj ga u companies.")
        return row[0]


def _upsert_filing(conn, company_id: int, meta: dict[str, Any], source_url: str,
                   doc_type: str, published_at: str | None) -> int:
    """Insert ili update filinga po unique ključu; vrati filing_id."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO filings (company_id, doc_type, fiscal_year, period_type,
                                 basis, audited, cumulative, currency,
                                 reporting_scale, source_url, published_at, status)
            VALUES (%(company_id)s, %(doc_type)s, %(fiscal_year)s, %(period_type)s,
                    %(basis)s, %(audited)s, %(cumulative)s, %(currency)s,
                    %(reporting_scale)s, %(source_url)s, %(published_at)s, 'extracted')
            ON CONFLICT (company_id, doc_type, fiscal_year, period_type, basis)
            DO UPDATE SET audited = EXCLUDED.audited,
                          cumulative = EXCLUDED.cumulative,
                          currency = EXCLUDED.currency,
                          reporting_scale = EXCLUDED.reporting_scale,
                          source_url = EXCLUDED.source_url,
                          published_at = EXCLUDED.published_at,
                          status = 'extracted'
            RETURNING id
            """,
            {
                "company_id": company_id,
                "doc_type": doc_type,
                "fiscal_year": meta["fiscal_year"],
                "period_type": meta["period_type"],
                "basis": meta["basis"],
                "audited": meta.get("audited"),
                "cumulative": meta.get("cumulative"),
                "currency": meta.get("currency", "EUR"),
                "reporting_scale": meta.get("reporting_scale", 1),
                "source_url": source_url,
                "published_at": published_at,
            },
        )
        return cur.fetchone()[0]


def load_extraction(conn, extraction: dict[str, Any], *, source_url: str,
                    doc_type: str = "financial_report",
                    published_at: str | None = None) -> int:
    """Učitaj jednu ekstrakciju u bazu. Vrati filing_id.

    - Preskače stavke s value_raw=None (nepostojeće u dokumentu).
    - Validira da su item ključevi kanonski (nepoznate odbacuje uz upozorenje).
    - Računa derivirane stavke (is_reported=FALSE).
    """
    meta = extraction["meta"]
    items = extraction.get("items", [])
    company_id = _get_company_id(conn, meta["company_ticker"])
    fiscal_year = meta["fiscal_year"]
    period_type = meta["period_type"]
    basis = meta["basis"]
    currency = meta.get("currency", "EUR")
    scale = int(meta.get("reporting_scale", 1))

    filing_id = _upsert_filing(conn, company_id, meta, source_url, doc_type, published_at)

    with conn.cursor() as cur:
        # Re-ingest: očisti prethodne retke za ovaj filing.
        cur.execute("DELETE FROM financials WHERE filing_id = %s", (filing_id,))

        reported_eur: dict[str, float] = {}
        skipped: list[str] = []

        for it in items:
            item = it.get("item")
            value_raw = it.get("value_raw")
            if item not in canonical.REPORTED_ITEMS:
                skipped.append(str(item))
                continue
            if value_raw is None:
                continue  # ne postoji u dokumentu — ne spremamo null
            statement = canonical.STATEMENT_OF[item]
            # Broj dionica je apsolutni count, a regulatorne stavke su OMJERI
            # (decimalni razlomci) — NE primjenjuj monetarnu skalu ni FX.
            if statement in ("shares", "regulatory"):
                value_eur = float(value_raw)
            else:
                value_eur = to_eur(value_raw, scale, currency)
            reported_eur[item] = value_eur
            cur.execute(
                """
                INSERT INTO financials (filing_id, company_id, fiscal_year, period_type,
                    basis, statement, item, value_raw, value_eur, confidence,
                    source_page, is_reported)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE)
                """,
                (filing_id, company_id, fiscal_year, period_type, basis, statement,
                 item, value_raw, value_eur, it.get("confidence"), it.get("source_page")),
            )

        # Derivirane stavke (is_reported=FALSE, value_raw=NULL, confidence=NULL).
        for item, value_eur in derive_items(reported_eur).items():
            statement = canonical.DERIVED_ITEMS[item]
            cur.execute(
                """
                INSERT INTO financials (filing_id, company_id, fiscal_year, period_type,
                    basis, statement, item, value_raw, value_eur, confidence,
                    source_page, is_reported)
                VALUES (%s,%s,%s,%s,%s,%s,%s,NULL,%s,NULL,'computed',FALSE)
                """,
                (filing_id, company_id, fiscal_year, period_type, basis, statement,
                 item, value_eur),
            )

    if skipped:
        print(f"[loader] filing {filing_id}: odbačene nekanonske stavke: {sorted(set(skipped))}")
    return filing_id
