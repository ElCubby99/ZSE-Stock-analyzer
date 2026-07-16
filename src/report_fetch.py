"""v3 FAZA SOTP (nastavak): automatski dohvat GODIŠNJIH izvještaja s EHO-a —
i KONSOLIDIRANOG i NEKONSOLIDIRANOG (odvojenog).

Nekonsolidirani izvještaj matice je ulaz za standalone SOTP komponentu
(vidi Metodologiju), pa se ubuduće skidaju OBA: najnovija godišnja objava
po (basis, documentType=PDF), revidirana ima prednost pred nerevidiranom.

Datoteke: data/reports/auto/{ticker}_{year}[_separate].pdf
CLI:  python -m src.report_fetch KOEI [HT ...]
"""
from __future__ import annotations

import os
import pathlib

from . import eho

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "reports" / "auto"


def pick_annual(items: list[dict], consolidated: bool) -> dict | None:
    """Najnovije godišnje izvješće za zadanu osnovu: PDF, revidirano prvo."""
    cand = [r for r in items
            if r.get("period") == "1Y" and r.get("documentType") == "PDF"
            and bool(r.get("consolidated")) == consolidated
            and r.get("documentLink")]
    if not cand:
        return None
    cand.sort(key=lambda r: (r.get("year") or 0, bool(r.get("revised")),
                             r.get("publishDate") or ""), reverse=True)
    return cand[0]


def fetch_both(ticker: str, log=print) -> dict:
    """Skini najnoviji godišnji KONSOLIDIRANI i NEKONSOLIDIRANI PDF.
    -> {'consolidated': path|None, 'separate': path|None} (None uz razlog u logu)."""
    import requests
    d = eho.feed("financialReports", ticker=ticker,
                 date_from="2022-01-01",
                 date_to=__import__("datetime").date.today().isoformat())
    items = d.get("items") or []
    os.makedirs(OUT_DIR, exist_ok=True)
    out: dict = {}
    for key, cons in (("consolidated", True), ("separate", False)):
        rep = pick_annual(items, cons)
        if rep is None:
            log(f"[report_fetch] {ticker}: nema godišnjeg "
                f"{'konsolidiranog' if cons else 'NEKONSOLIDIRANOG'} PDF-a na "
                "EHO feedu — preskačem s razlogom")
            out[key] = None
            continue
        suffix = "" if cons else "_separate"
        path = OUT_DIR / f"{ticker.lower()}_{rep['year']}{suffix}.pdf"
        if path.exists() and path.stat().st_size > 10_000:
            log(f"[report_fetch] {ticker}: {path.name} već postoji — preskačem")
            out[key] = str(path)
            continue
        url = rep["documentLink"].replace("//fileadmin", "/fileadmin")
        r = requests.get(url, timeout=300)
        r.raise_for_status()
        if not r.content.startswith(b"%PDF"):
            log(f"[report_fetch] {ticker}: {url} nije PDF — preskačem s razlogom")
            out[key] = None
            continue
        path.write_bytes(r.content)
        log(f"[report_fetch] {ticker}: FY{rep['year']} "
            f"{'kons.' if cons else 'NEKONS.'} ({'rev.' if rep.get('revised') else 'nerev.'}) "
            f"-> {path.name} ({len(r.content) / 1e6:.1f} MB) [{url}]")
        out[key] = str(path)
    return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    for t in sys.argv[1:] or ["KOEI"]:
        fetch_both(t.upper())
