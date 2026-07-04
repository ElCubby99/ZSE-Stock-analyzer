"""CLI driver (točke 2–5): ingest jednog izvješća ili ispis usporedne tablice.

Primjeri:
  # Ekstrakcija preko API-ja iz tekstualnog izvješća pa load+validate:
  python -m src.ingest extract --text data/reports/koei_2024_consolidated.txt \\
      --source-url https://zse.hr/... --published 2025-04-15

  # Load iz već spremljenog extraction JSON-a (bez API poziva):
  python -m src.ingest load --json data/reports/koei_2024.json \\
      --source-url https://zse.hr/...

  # Usporedna tablica (točka 5):
  python -m src.ingest report --years 2023 2024 2025
"""
from __future__ import annotations

import argparse
import json
import sys

from .db import get_conn
from .loader import load_extraction
from .report import render_comparison
from .validator import validate_filing


def _print_validation(res: dict) -> None:
    print(f"\nStatus filinga: {res['status'].upper()}")
    for r in res["results"]:
        print(f"  [{r['status']:4}] {r['rule']}: {r['detail']}")


def _ingest(extraction: dict, source_url: str, published: str | None,
            doc_type: str) -> None:
    with get_conn() as conn:
        fid = load_extraction(conn, extraction, source_url=source_url,
                              doc_type=doc_type, published_at=published)
        res = validate_filing(conn, fid)
        meta = extraction["meta"]
        print(f"Učitan filing {fid}: {meta['company_ticker']} {meta['fiscal_year']} "
              f"{meta['period_type']}/{meta['basis']}")
        _print_validation(res)


def cmd_extract(a) -> None:
    if getattr(a, "template", "industrial") == "bank":
        from .extract import extract_bank_filing as _extract
    else:
        from .extract import extract_filing as _extract
    with open(a.text, encoding="utf-8") as f:
        text = f.read()
    extraction = _extract(text)
    _ingest(extraction, a.source_url, a.published, a.doc_type)


def cmd_load(a) -> None:
    with open(a.json, encoding="utf-8") as f:
        extraction = json.load(f)
    _ingest(extraction, a.source_url, a.published, a.doc_type)


def cmd_report(a) -> None:
    with get_conn() as conn:
        print(render_comparison(conn, a.ticker, a.years, basis=a.basis,
                                period_type=a.period_type))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="ZSE ingest/report CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("extract", help="API ekstrakcija iz teksta -> load -> validate")
    pe.add_argument("--text", required=True)
    pe.add_argument("--source-url", required=True)
    pe.add_argument("--published", default=None)
    pe.add_argument("--doc-type", default="financial_report")
    pe.add_argument("--template", choices=["industrial", "bank"], default="industrial",
                    help="bank = bankovna taksonomija (NII/naknade/rezervacije/CET1...)")
    pe.set_defaults(fn=cmd_extract)

    pl = sub.add_parser("load", help="load iz extraction JSON-a -> validate")
    pl.add_argument("--json", required=True)
    pl.add_argument("--source-url", required=True)
    pl.add_argument("--published", default=None)
    pl.add_argument("--doc-type", default="financial_report")
    pl.set_defaults(fn=cmd_load)

    pr = sub.add_parser("report", help="usporedna tablica")
    pr.add_argument("--ticker", default="KOEI")
    pr.add_argument("--years", type=int, nargs="+", default=[2023, 2024, 2025])
    pr.add_argument("--basis", default="consolidated")
    pr.add_argument("--period-type", default="annual")
    pr.set_defaults(fn=cmd_report)

    a = p.parse_args(argv)
    a.fn(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
