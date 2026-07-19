"""v3 FAZA K: testovi raspisa troška kapitala (r = rf + β×ERP + CRP + nelikv.).

Čuvaju tri stvari koje je forenzika (FAZA D) našla prekršene ili krhke:
1. NEMA dvostrukog counta rizika zemlje: rf je EUR bezrizični (ne HR
   krivulja sa spreadom), ERP je ZRELI (bez CRP-a), CRP je zaseban i
   ograničen na ≤ 1,5 p.b. — i pojavljuje se TOČNO JEDNOM.
2. r je doista zbroj vidljivih komponenti (raspis, ništa skriveno).
3. Premija nelikvidnosti postoji SAMO ispod Z1 praga likvidnosti —
   likvidna imena je ne smiju imati.

DB-ovisni testovi se preskaču ako lokalna baza nije dostupna.
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src import params_calibrated as pc  # noqa: E402


def _connect():
    """Sirova psycopg2 konekcija ili None (get_conn je context manager)."""
    try:
        import psycopg2

        from src import config
        c = psycopg2.connect(config.dsn())
        with c.cursor() as cur:
            cur.execute("SELECT 1")
        return c
    except Exception:  # noqa: BLE001
        return None


def test_konstante_bez_dvostrukog_counta_zemlje():
    # rf: EUR bezrizični (Bund) — HR 10g bi nosio spread zemlje u rf-u
    assert pc.RF < 0.035, "rf mora biti EUR bezrizični, ne HR krivulja sa spreadom"
    # ERP: zreli, bez skrivenog CRP-a (v2 je imao 5,7% = 4,23% + A3 CRP)
    assert pc.ERP < 0.045, "ERP mora biti ZRELI (bez premije zemlje)"
    # ERP tekst mora čitatelju jasno reći da ne uključuje premiju rizika zemlje
    # (bez internog žargona — M43 čišćenje javnog teksta)
    assert "ne uključuje premiju rizika zemlje" in pc.ERP_SRC.lower()
    # CRP: zaseban, mali, strop iz naloga v3
    assert 0 < pc.CRP <= 0.015, "CRP mora biti zaseban i ≤ 1,5 p.b."
    # javni tekst NE smije nositi interni žargon (v3 FAZA K / exact_unverified /
    # egress / TOČAN REDAK NEPROVJEREN) — Borisov nalog M43
    for src in (pc.RF_SRC, pc.ERP_SRC, pc.CRP_SRC):
        low = src.lower()
        assert "exact_unverified" not in low
        assert "faza k" not in low
        assert "egress" not in low
        assert "neprovjeren" not in low


def test_r_je_zbroj_vidljivih_komponenti():
    p = pc.build_params("HT")
    expected = p.rf + p.beta * p.erp + p.crp + p.illiq_premium
    assert abs(p.cost_of_equity - expected) < 1e-9, (
        "r mora biti TOČNO rf + β×ERP + CRP + nelikvidnost — ništa skriveno")
    assert p.wacc == p.cost_of_equity
    # raspis u izvoru: sve četiri komponente imenovane
    for needle in ("rf", "ERP", "CRP"):
        assert needle in p.sources["r"]
    for key in ("rf", "erp", "crp"):
        assert p.sources.get(key), f"komponenta '{key}' mora imati vlastiti izvor"


def test_likvidna_imena_nemaju_premiju_nelikvidnosti():
    conn = _connect()
    if conn is None:
        pytest.skip("lokalna baza nedostupna")
    from src.beta_discipline import (
        LIQ_MIN_RATIO, LIQ_MIN_TURNOVER, resolve_beta)
    with conn:
        for t in ("HT", "ADRS", "PODR", "ATGR", "ZABA", "CROS"):
            with conn.cursor() as cur:
                cur.execute("SELECT sector FROM companies WHERE ticker=%s", (t,))
                row = cur.fetchone()
            if not row:
                continue
            bd = resolve_beta(conn, t, row[0])
            liq = bd["liquidity"]
            liquid = (liq["ratio"] >= LIQ_MIN_RATIO
                      and liq["avg_turnover"] >= LIQ_MIN_TURNOVER)
            if liquid:
                assert bd["illiq_premium"] == 0.0, (
                    f"{t}: likvidno ime ne smije nositi premiju nelikvidnosti")
            else:
                assert bd["illiq_premium"] in (0.015, 0.025), (
                    f"{t}: ispod praga premija mora biti +1,5 ili +2,5 p.b. (M43)")
