"""v3 FAZA S: testovi raspodjele vrijednosti firme po klasama dionica.

- identitet: n_red×fer_red + n_povl×fer_povl = bound × N_uk (vrijednost
  firme se raspodjelom NE mijenja);
- omjer fer cijena klasa = tržišni medijan omjera;
- konzistentnost pozicija: nemoguće da jedna klasa bude duboko iznad svoje
  zone a druga unutar, osim ako DANAŠNJI omjer odstupa od povijesnog
  medijana (test to provjerava kroz identitet omjera);
- PLAG fallback: premalo zajedničkih dana -> teorijski omjer 1,0 + oznaka.
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


def _connect():
    try:
        import psycopg2

        from src import config
        c = psycopg2.connect(config.dsn())
        with c.cursor() as cur:
            cur.execute("SELECT 1")
        return c
    except Exception:  # noqa: BLE001
        return None


@pytest.fixture(scope="module")
def conn():
    c = _connect()
    if c is None:
        pytest.skip("lokalna baza nedostupna")
    yield c
    c.close()


def _company(cur, ticker):
    cur.execute("SELECT id FROM companies WHERE ticker=%s", (ticker,))
    return cur.fetchone()[0]


def _shares(cur, class_ticker):
    cur.execute("""SELECT (shares_issued - COALESCE(treasury_shares,0))::float
                   FROM share_classes WHERE ticker=%s""", (class_ticker,))
    return cur.fetchone()[0]


def test_identitet_vrijednosti_firme(conn):
    """ADRS: raspodjela čuva ukupnu vrijednost i tržišni omjer klasa."""
    from src.class_ratio import class_zones
    with conn.cursor() as cur:
        cid = _company(cur, "ADRS")
        cz = class_zones(conn, cid, 80.0, 100.0)
        if cz is None:
            pytest.skip("ADRS bez dvije klase s dionicama")
        n_a = _shares(cur, "ADRS")
        n_b = _shares(cur, "ADRS2")
    meta = cz["_meta"]
    for bound_name, bound in (("zone_low", 80.0), ("zone_high", 100.0)):
        total = (n_a * cz["ADRS"][bound_name] + n_b * cz["ADRS2"][bound_name])
        assert abs(total - bound * (n_a + n_b)) / (bound * (n_a + n_b)) < 1e-3, \
            "raspodjela mora čuvati ukupnu vrijednost firme"
        r = cz["ADRS"][bound_name] / cz["ADRS2"][bound_name]
        assert abs(r - meta["ratio"]) < 1e-3, \
            "omjer fer cijena klasa mora biti tržišni medijan"
    assert meta["ratio_basis"] == "tržišni medijan"
    assert meta["ratio_n_days"] >= 30


def test_konzistentne_pozicije_klasa(conn):
    """ADRS/ADRS2 naspram SVOJIH zona: raskorak klasa smije se razlikovati
    SAMO onoliko koliko današnji omjer cijena odstupa od povijesnog
    medijana (to je činjenica koja se prikazuje, ne nekonzistentnost)."""
    import json
    d = json.loads(pathlib.Path("frontend/public/data/ADRS.json")
                   .read_text(encoding="utf-8"))
    rec = (d.get("valuation") or {}).get("reconciliation") or {}
    cz = rec.get("class_zones")
    if not cz or rec.get("zone_low") is None:
        pytest.skip("ADRS bez class_zones u exportu (regen potreban?)")
    px = {c["class_ticker"]: (c.get("last") or {}).get("close_eur")
          for c in (d.get("price_summary") or {}).get("classes", [])}
    if not px.get("ADRS") or not px.get("ADRS2"):
        pytest.skip("nema cijena obje klase")
    gap = {t: px[t] / ((cz[t]["zone_low"] + cz[t]["zone_high"]) / 2) - 1
           for t in ("ADRS", "ADRS2")}
    ratio_today = px["ADRS"] / px["ADRS2"]
    ratio_hist = cz["_meta"]["ratio"]
    # (1+gap_red)/(1+gap_povl) == ratio_danas/ratio_povijesni (identitet)
    lhs = (1 + gap["ADRS"]) / (1 + gap["ADRS2"])
    rhs = ratio_today / ratio_hist
    assert abs(lhs - rhs) < 1e-6, \
        "razlika raskoraka klasa mora biti TOČNO odstupanje omjera od medijana"


def test_plag_fallback_teorijski_omjer(conn):
    from src.class_ratio import class_zones
    with conn.cursor() as cur:
        cid = _company(cur, "PLAG")
    cz = class_zones(conn, cid, 10.0, 12.0)
    if cz is None:
        pytest.skip("PLAG bez dvije klase s dionicama")
    m = cz["_meta"]
    assert m["ratio_basis"] == "teorijski omjer"
    assert m["ratio"] == 1.0
    assert "pretpostavka" in m["ratio_note"]
