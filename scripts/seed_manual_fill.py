"""M14 ("odglumi API"): ručna dopuna filinga IZ SLUŽBENIH IZVJEŠTAJA — bez API.

API kredit je potrošen, pa je ekstrakciju odradio model U SESIJI čitanjem
lokalnih dokumenata (ista verified-seed politika kao TOK minority / KOEI
holdings). Svaka brojka nosi izvor (dokument + stranica); troškovne magnitude
pozitivne (kanon); derivirane stavke se PONOVNO izvode nakon dopune.

  HPB filing 27 (FY2025): RDG obrazac s EHO PDF-a (str. 9) — prihodovne
    stavke koje su falile (jezgra za bankovni gate): NII = AOP001−AOP003,
    neto naknade = AOP008−AOP009, ukupni operativni prihod = NII + naknade +
    fin. aktivnosti (010) + ostali op. prihodi (011) + prihodi od vp (004).
  HT filing 29 (FY2025): ESEF iXBRL (Grupa, tisuće EUR) — bilanca (str. 14-15),
    RDG (str. 12-13), novčani tok (str. 16). Dug = obveze za najam (HT nema
    bankovnog duga u bilanci Grupe).

Pokretanje:  python -m scripts.seed_manual_fill
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402
from src.normalize import derive_items  # noqa: E402
from src.validator import validate_filing  # noqa: E402

K = 1000  # HT iskazuje u tisućama EUR

FILLS = {
    27: {  # HPB FY2025 — izvor: hpb_2025.pdf (EHO), RDG obrazac str. 9, u EUR
        "net_interest_income": (154_027_866, "str. 9 (AOP001 227.951.115 − AOP003 73.923.249)"),
        "net_fee_income": (38_243_758, "str. 9 (AOP008 77.992.658 − AOP009 39.748.900)"),
        "total_operating_income": (199_058_160,
                                   "str. 9 (NII 154.027.866 + naknade 38.243.758 + fin.aktivnosti "
                                   "AOP010 5.620.130 + ostali op. AOP011 924.718 + vp AOP004 241.688)"),
    },
    29: {  # HT FY2025 — izvor: ht_2025.zip ESEF (Grupa, t€), str. 12-16
        "total_assets": (2_125_366 * K, "izvještaj o fin. položaju, str. 14"),
        "equity_parent": (1_632_105 * K, "str. 15 (kapital pripisiv vlasnicima)"),
        "minority_interests": (29_966 * K, "str. 15 (nekontrolirajući interes)"),
        "net_income": (144_579 * K, "RDG, str. 12 (dobit godine)"),
        "net_income_parent": (142_960 * K, "str. 13 (pripada redovnim dioničarima)"),
        "net_income_minority": (1_619 * K, "str. 13 (nekontrolirajući interes)"),
        "income_tax": (32_837 * K, "RDG, str. 12"),
        "cash_and_equivalents": (173_065 * K, "str. 14 (novac i novčani ekvivalenti)"),
        "debt_long": (61_701 * K, "str. 15 (dugoročne obveze za najam — jedini kamatonosni dug)"),
        "debt_short": (23_005 * K, "str. 15 (kratkoročne obveze za najam)"),
        "operating_cf": (407_490 * K, "novčani tok, str. 16"),
        "capex": (215_939 * K, "str. 16 (izdaci za kupnju dugotrajne imovine)"),
    },
}

SOURCES = {27: "HPB kons. FY2025 obrazac (data/reports/auto/hpb_2025.pdf)",
           29: "HT kons. GI FY2025 ESEF (data/reports/auto/ht_2025.zip)"}


def run() -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        for fid, items in FILLS.items():
            cur.execute("""SELECT f.company_id, f.fiscal_year, f.period_type, f.basis,
                                  c.ticker FROM filings f JOIN companies c ON c.id=f.company_id
                           WHERE f.id=%s""", (fid,))
            r = cur.fetchone()
            if not r:
                print(f"[fill] filing {fid} ne postoji — preskačem"); continue
            cid, fy, pt, basis, tick = r
            for item, (val, page) in items.items():
                cur.execute("""DELETE FROM financials
                               WHERE filing_id=%s AND item=%s""", (fid, item))
                stmt = _statement(item)
                cur.execute(
                    """INSERT INTO financials (filing_id, company_id, fiscal_year,
                           period_type, basis, statement, item, value_raw, value_eur,
                           confidence, source_page, is_reported)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0.90,%s,TRUE)""",
                    (fid, cid, fy, pt, basis, stmt, item, val, val,
                     f"{SOURCES[fid]}, {page} — ručna ekstrakcija u sesiji"))
            # rederivacija: obriši stare derivirane pa izvedi iz SVIH reported
            cur.execute("""SELECT item, value_eur FROM financials
                           WHERE filing_id=%s AND is_reported""", (fid,))
            rep = {i: float(v) for i, v in cur.fetchall() if v is not None}
            cur.execute("DELETE FROM financials WHERE filing_id=%s AND NOT is_reported", (fid,))
            from src import canonical
            for item, val in derive_items(rep).items():
                cur.execute(
                    """INSERT INTO financials (filing_id, company_id, fiscal_year,
                           period_type, basis, statement, item, value_raw, value_eur,
                           confidence, source_page, is_reported)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,NULL,%s,NULL,'computed',FALSE)""",
                    (fid, cid, fy, pt, basis, canonical.DERIVED_ITEMS[item], item, val))
            conn.commit()
            res = validate_filing(conn, fid)
            print(f"[fill] {tick} filing {fid}: dopunjeno {len(items)} stavki -> "
                  f"validacija: {res['status'].upper()}")
            for x in res["results"]:
                if x["status"] != "pass":
                    print(f"       [{x['status']}] {x['rule']}: {x['detail']}")
    return 0


def _statement(item: str) -> str:
    from src import canonical
    return canonical.STATEMENT_OF[item]


if __name__ == "__main__":
    sys.exit(run())
