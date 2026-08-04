"""M59: dividenda isplativa u više rata (HPB FY2025) — čuvari bez baze.

Zbirni EHO blok (jedan iznos, zadnji datum isplate) zamjenjuje se kuriranim
ratama; zbroj rata MORA biti jednak ukupnom iznosu, svaka rata nosi svoj
datum isplate i napomenu čitatelju, a SQL fix u migraciji mora odgovarati
kuriranoj podjeli (ista dva retka nastaju i kroz scrape i kroz migraciju).
"""
import pathlib
import re
from datetime import date

from src.dividends import CURATED_SPLITS

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_rate_zbroj_i_polja():
    assert CURATED_SPLITS, "kurirana podjela u rate mora postojati (HPB)"
    for (klasa, ex, total), rate in CURATED_SPLITS.items():
        assert len(rate) >= 2, f"{klasa}: podjela s <2 rate nema smisla"
        assert abs(sum(r["amount_eur"] for r in rate) - total) < 0.005, \
            f"{klasa}: zbroj rata != ukupni iznos {total}"
        date.fromisoformat(ex)  # ex-datum mora biti ISO datum
        pays = [r["payment_date"] for r in rate]
        assert all(pays) and len(set(pays)) == len(pays), \
            f"{klasa}: svaka rata mora imati SVOJ datum isplate"
        for r in rate:
            date.fromisoformat(r["payment_date"])
            assert r["note"], f"{klasa}: rata bez napomene čitatelju"


def test_hpb_rate_cinjenice():
    """Izvor: Odluke GS HPB 24.7.2026. (EHO #67878) — 17,54 € u 2 x 8,77 €."""
    rate = CURATED_SPLITS[("HPB", "2026-07-29", 17.54)]
    assert [r["amount_eur"] for r in rate] == [8.77, 8.77]
    assert [r["payment_date"] for r in rate] == ["2026-08-04", "2027-01-28"]
    assert "čl. 324" in rate[1]["note"]  # 2. rata je uvjetovana (ZKI)


def test_migracija_usklajena_s_kuriranom_podjelom():
    """SQL fix (v3_1) i CURATED_SPLITS moraju upisivati ISTE retke — inače
    scrape i migracija proizvode različite podatke na produkciji."""
    sql = (ROOT / "db" / "zse_schema_v3_1.sql").read_text(encoding="utf-8")
    assert "uq_dividends_event" in sql          # novi dedup ključ (payment_date)
    assert "DROP CONSTRAINT IF EXISTS dividends_class_ticker_ex_date_amount_eur_key" in sql
    for r in CURATED_SPLITS[("HPB", "2026-07-29", 17.54)]:
        iso = r["payment_date"]
        assert re.search(rf"DATE '{iso}'", sql), f"rata {iso} nije u migraciji"
        assert r["note"] in sql, f"napomena rate {iso} nije ista u migraciji"


def test_en_prijevod_napomena():
    """Svaka napomena rate mora imati EN prijevod u dataText.mjs (exact mapa)."""
    dt = (ROOT / "frontend" / "src" / "i18n" / "dataText.mjs").read_text(encoding="utf-8")
    for rate in CURATED_SPLITS.values():
        for r in rate:
            assert r["note"] in dt, f"napomena bez EN prijevoda: {r['note'][:60]}…"
