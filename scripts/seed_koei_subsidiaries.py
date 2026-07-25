"""M50: uvrsti KONČAR-ove neuvrštene operativne kćeri u SOTP + KPT normalizacija.

Izvor: KONČAR d.d. GI 2025 (NEKONSOLIDIRANI), bilj. 17 „Ulaganja u ovisna
društva" (str. 34) — knjigovodstvena vrijednost udjela (već je NAŠ udio, po
trošku) i bilj. 16 (KPT, pridruženo društvo).

Neuvrštene kćeri ulaze po KNJIGOVODSTVENOJ vrijednosti (konzervativan pod,
jasno označeno) jer nemamo zasebnu procjenu; uvrštene (KODT, DLKV) ostaju po
tržištu. KPT: normalizirana godišnja dobit (⌀ 2024-25) za DCF u valuaciji.

Idempotentno: briše postojeće subsidiary_book retke KOEI-ja pa ih ponovno
umeće; KPT redak se UPDATE-a. Pokretati lokalno; content_dump.json.gz onda
prenosi na produkciju (db-sync workflow).
"""
from __future__ import annotations

import sys

from src.db import get_conn

# (naziv, udio, knjigovodstvena vrijednost udjela u EUR) — bilj. 17, 31.12.2025.
UNLISTED = [
    ("KONČAR – Digital d.o.o.", 1.0000, 24_703_000),
    ("KONČAR – Transformatorski kotlovi d.o.o.", 0.6000, 23_978_000),
    ("KONČAR – Aparati i postrojenja d.o.o.", 1.0000, 11_198_000),
    ("KONČAR – Elektronika i informatika d.d.", 1.0000, 8_353_000),
    ("KONČAR – Institut za elektrotehniku d.o.o.", 1.0000, 8_108_000),
    ("KONČAR – Generatori i motori d.o.o.", 1.0000, 7_946_000),
    ("KONČAR – Obnovljivi izvori d.o.o.", 1.0000, 7_290_000),
    ("KONČAR – Motori i električni sustavi d.o.o.", 1.0000, 6_451_000),
    ("KONČAR – Električna vozila d.d.", 0.8573, 5_776_000),
    ("HELB d.o.o.", 0.7500, 5_529_000),
    ("KONČAR – Metalne konstrukcije d.o.o.", 1.0000, 5_302_000),
    ("KONČAR – Mjerni transformatori d.d.", 0.6197, 4_089_000),
    ("TELENERG-INŽENJERING d.o.o.", 1.0000, 1_008_000),
    ("INK PROJEKT d.o.o.", 1.0000, 206_000),
    ("KONČAR – Hydro Turbine d.o.o.", 1.0000, 2_000),
]
UNLISTED_SRC = ("KOEI GI 2025 (nekonsolidirani), bilj. 17 (Ulaganja u ovisna "
                "društva), str. 34 — knjigovodstvena vrijednost udjela (trošak).")

# KPT (pridruženo društvo, 49%): normalizirana 100% godišnja dobit = ⌀(2025, 2024)
KPT_NI_NORM = round((87_700_000 + 51_700_000) / 2)   # 69,7 M€
KPT_SRC = ("KOEI GI 2025, bilj. 16, str. 130-131: KONČAR – Energetski "
           "transformatori (Siemens JV, 49%). Dobit nakon poreza 2025.: "
           "87,7 M€ (2024.: 51,7 M€) — NORMALIZIRANO (⌀) 69,7 M€ za DCF. "
           "Knjigovodstvena vrijednost udjela 44,2 M€; JV gotovo cijelu dobit "
           "isplaćuje kao dividendu (2025.: 43,0 M€) pa knjiga ostaje niska.")


def main() -> int:
    sys.path.insert(0, ".")
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM companies WHERE ticker='KOEI'")
        r = cur.fetchone()
        if not r:
            print("KOEI nije u bazi"); return 1
        cid = r[0]

        # 1) KPT: normalizirana dobit + dokumentiran izvor
        cur.execute(
            """UPDATE holdings SET associate_ni=%s, jv_book_source=%s
               WHERE parent_company_id=%s AND held_name ILIKE 'KPT%%'""",
            (KPT_NI_NORM, KPT_SRC, cid))
        print(f"KPT update: {cur.rowcount} redak (norm NI {KPT_NI_NORM:,} €)")

        # 2) neuvrštene kćeri — idempotentno (obriši pa umetni)
        cur.execute("""DELETE FROM holdings WHERE parent_company_id=%s
                       AND valuation_basis='subsidiary_book'""", (cid,))
        for name, pct, book in UNLISTED:
            cur.execute(
                """INSERT INTO holdings (parent_company_id, held_company_id, held_name,
                     ownership_pct, listed, valuation_basis, jv_book_value_eur,
                     jv_book_source, confidence, as_of)
                   VALUES (%s,NULL,%s,%s,FALSE,'subsidiary_book',%s,%s,0.6,'2025-12-31')""",
                (cid, name, pct, book, UNLISTED_SRC))
        print(f"neuvrštene kćeri umetnute: {len(UNLISTED)} "
              f"(ukupno book {sum(b for _,_,b in UNLISTED)/1e6:,.1f} M€)")
        conn.commit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
