"""Korak 1 (audit fix): broj dionica sa službenog ZSE listinga — BEZ API.

Puni share_classes.shares_issued iz 'Uvrštena količina' (zse.hr stranica
papira) za SVE klase kojima broj dionica fali, s citiranim izvorom u
dividend_note. Posebni slučaj ATGR: baza je držala ex-trezor broj (GI FY2025
str. 377: 13.254.264) kao izdani; ZSE listing kaže 13.337.200 uvrštenih, a
GI FY2025 ima treasury_shares=82.936 -> 13.337.200 − 82.936 = 13.254.264
(egzaktno). Ispravak: shares_issued=ZSE, treasury=GI — ex-trezor NEPROMIJENJEN.

Idempotentno: postojeći shares_issued se ne dira (osim dokumentiranog ATGR).
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402
from src.onboard import fetch_listed_quantity  # noqa: E402

ATGR_ISSUED = 13_337_200      # ZSE listing 'Uvrštena količina'
ATGR_TREASURY = 82_936        # GI FY2025 (financials.treasury_shares, FY2025)


def main() -> int:
    with get_conn() as conn, conn.cursor() as cur:
        # 1) sve klase bez broja dionica -> ZSE listing
        cur.execute("""SELECT sc.id, sc.ticker, sc.isin FROM share_classes sc
                       WHERE sc.shares_issued IS NULL ORDER BY sc.ticker""")
        for scid, tick, isin in cur.fetchall():
            if not isin:
                print(f"[shares] {tick}: nema ISIN -> preskačem")
                continue
            try:
                qty = fetch_listed_quantity(isin)
            except Exception as e:  # noqa: BLE001
                print(f"[shares] {tick}: dohvat pao ({e})")
                continue
            if not qty:
                print(f"[shares] {tick}: ZSE listing bez 'Uvrštena količina'")
                continue
            cur.execute(
                """UPDATE share_classes SET shares_issued=%s,
                       dividend_note = COALESCE(dividend_note,'') ||
                       ' | broj dionica = Uvrštena količina (zse.hr papir, ISIN ' || isin ||
                       '); trezorske NEPOZNATE (0 uz ogradu)'
                   WHERE id=%s AND shares_issued IS NULL""", (qty, scid))
            print(f"[shares] {tick}: {qty:,} (zse.hr 'Uvrštena količina')")

        # 2) ATGR: izdani = ZSE listing, trezorske = GI FY2025 (ex-trezor isti)
        cur.execute("""UPDATE share_classes
                       SET shares_issued=%s, treasury_shares=%s,
                           dividend_note='ISIN iz službene ZSE tečajnice; '
                             'izdano = Uvrštena količina 13.337.200 (zse.hr papir); '
                             'trezorske 82.936 = GI FY2025 (financials); '
                             'ex-trezor 13.254.264 = GI FY2025 str. 377 (konzistentno)'
                       WHERE ticker='ATGR' AND (shares_issued <> %s
                             OR COALESCE(treasury_shares,0) <> %s)""",
                    (ATGR_ISSUED, ATGR_TREASURY, ATGR_ISSUED, ATGR_TREASURY))
        if cur.rowcount:
            print(f"[shares] ATGR: izdano {ATGR_ISSUED:,}, trezorske {ATGR_TREASURY:,} "
                  f"(ex-trezor {ATGR_ISSUED - ATGR_TREASURY:,} nepromijenjen)")
        conn.commit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
