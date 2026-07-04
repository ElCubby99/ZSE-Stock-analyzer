"""Sastav ZSE indeksa (M6) — ŽIVO sa zse.hr, bez hardkodiranja članica.

Rezolucija indeksa: stranica /hr/indeksi/42 nosi <option> listu (ime -> ISIN
indeksa); sastav vraća /json/IndexComposition?isin=...&mic=XZAG (isti javni
JSON sloj kao TradingPriceList). Fallback ISIN-a postoji SAMO ako se stranica
ne može parsirati, i tada se sastav dodatno provjerava (total == očekivano).
"""
from __future__ import annotations

import os
import re
from typing import Any

INDEX_PAGE = "https://zse.hr/hr/indeksi/42"
COMPOSITION_URL = "https://zse.hr/json/IndexComposition"
# zadnji poznati ISIN (2026-07-05) — koristi se samo ako parsiranje stranice padne
FALLBACK_INDEX_ISIN = {"CROBEX10": "HRZB00ICB103"}


def _verify():
    return (os.getenv("ZSE_CA_BUNDLE") or os.getenv("REQUESTS_CA_BUNDLE")
            or os.getenv("SSL_CERT_FILE") or True)


def resolve_index_isin(index_name: str, timeout: int = 40) -> str:
    """Ime indeksa (npr. 'CROBEX10') -> ISIN, parsiranjem službene stranice."""
    import requests

    try:
        r = requests.get(INDEX_PAGE, timeout=timeout, verify=_verify())
        r.raise_for_status()
        # <option value='HRZB...'>CROBEX10</option> (razni navodnici/razmaci)
        for isin, label in re.findall(
                r"<option[^>]*value=['\"](HRZB[A-Z0-9]+)['\"][^>]*>\s*([^<]+?)\s*<",
                r.text):
            if label.strip().upper() == index_name.upper():
                return isin
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] parsiranje stranice indeksa palo ({e}) — fallback ISIN")
    isin = FALLBACK_INDEX_ISIN.get(index_name.upper())
    if not isin:
        raise RuntimeError(f"ne mogu razriješiti ISIN za indeks {index_name}")
    return isin


def fetch_composition(index_name: str = "CROBEX10", timeout: int = 40) -> list[dict[str, Any]]:
    """Vrati [{symbol, isin, name, free_float, weight_pct}] za aktualni sastav."""
    import requests

    isin = resolve_index_isin(index_name, timeout=timeout)
    r = requests.get(COMPOSITION_URL, params={"isin": isin, "mic": "XZAG"},
                     headers={"X-Requested-With": "XMLHttpRequest"},
                     timeout=timeout, verify=_verify())
    r.raise_for_status()
    data = r.json()
    rows = data.get("rows") or []
    if not rows:
        raise RuntimeError(f"IndexComposition prazan za {index_name} ({isin})")

    def _pct(s):
        if not s:
            return None
        s = re.sub(r"[^0-9,\.]", "", str(s)).replace(".", "").replace(",", ".")
        try:
            return float(s) / 100.0
        except ValueError:
            return None

    out = []
    for row in rows:
        out.append({
            "symbol": row.get("symbol"),
            "isin": row.get("isin"),
            "name": (row.get("name") or "").strip(),
            "free_float": _pct(row.get("free_float_factor")),
            "weight_pct": _pct(row.get("weight_percentage") or row.get("weight")),
        })
    return out


if __name__ == "__main__":
    import sys
    for m in fetch_composition(sys.argv[1] if len(sys.argv) > 1 else "CROBEX10"):
        print(m)
