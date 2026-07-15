#!/usr/bin/env python3
"""Z3.3: sektor za firme bez klasifikacije — iz NACE koda sa ZSE stranice
papira (službeni, deterministički izvor; polje "nace" u embedded JSON-u).

Mapa NACE -> naša taksonomija je kurirana (dolje, s obrazloženjem po firmi);
sector_confidence = 0.9 (službeni NACE, ali mapiranje u interni sektor je
odluka). NACE se sprema u companies.nace radi provenijencije.

Pokretanje:  python -m scripts.seed_sectors_nace
"""
from __future__ import annotations

import re
import sys
import time

sys.path.insert(0, ".")

import requests  # noqa: E402

from src.db import get_conn  # noqa: E402

# ticker -> (sektor, obrazloženje)  — NACE dohvaćen 15.07.2026.
MAP = {
    "ACI":  ("tourism",      "NACE 9329 (rekreacija) — marine, nautički turizam"),
    "AUHR": ("consumer",     "NACE 4511 — trgovina motornim vozilima"),
    "BRIN": ("fund",         "NACE 6612 — ZAIF (zatvoreni fond), P/NAV logika"),
    "BSQR": ("holding",      "NACE 7010 — uprava grupe"),
    "CIAK": ("holding",      "NACE 7010 — uprava grupe (distribucija autodijelova)"),
    "CRAL": ("transport",    "NACE 5110 — zračni prijevoz putnika"),
    "DDJH": ("holding",      "NACE 7010 — uprava industrijske grupe"),
    "DLPR": ("other",        "NACE 7022 — poslovno savjetovanje"),
    "IGH":  ("construction", "NACE 7219 — inženjerska istraživanja (graditeljstvo)"),
    "INGR": ("construction", "NACE 7112 — inženjerstvo i tehničko savjetovanje"),
    "INSP": ("fund",         "NACE 6499 — ZAIF, P/NAV logika"),
    "JNAF": ("energy",       "NACE 4950 — cjevovodni transport (naftovod)"),
    "QTLG": ("holding",      "NACE 7010 — uprava grupe (logistika)"),
    "STJD": ("real_estate",  "NACE 6810 — poslovanje vlastitim nekretninama"),
    "TRFM": ("fund",         "NACE 6499 — ostale financijske usluge (investicijsko društvo)"),
    "VJSN": ("other",        "NACE 5813 — izdavaštvo; društvo u likvidaciji"),
}


def main() -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS nace TEXT")
        cur.execute("""SELECT c.id, c.ticker, sc.isin FROM companies c
                       JOIN share_classes sc ON sc.company_id=c.id
                       WHERE c.ticker = ANY(%s) AND (sc.is_primary_line OR sc.id=(
                         SELECT MIN(id) FROM share_classes WHERE company_id=c.id))
                       ORDER BY c.ticker""", (list(MAP),))
        for cid, tick, isin in cur.fetchall():
            sector, why = MAP[tick]
            nace = None
            try:
                r = requests.get("https://zse.hr/hr/papir/310",
                                 params={"isin": isin}, timeout=30)
                m = re.search(r'"nace":"(\d+)"', r.text)
                nace = m.group(1) if m else None
            except Exception:  # noqa: BLE001 — NACE je provenijencija, ne gate
                pass
            cur.execute(
                """UPDATE companies SET sector=%s, sector_confidence=0.9, nace=%s
                   WHERE id=%s AND (sector IS NULL OR sector='')""",
                (sector, nace, cid))
            print(f"[sektor] {tick:6} -> {sector:13} (nace={nace}) — {why}")
            time.sleep(0.3)
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM companies WHERE sector IS NULL OR sector=''")
        print(f"\npreostalo bez sektora: {cur.fetchone()[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
