"""v3 FAZA G: testovi TTM sloja, faze rasta iz podataka i ROE pravila.

Rade nad lokalnom bazom (preskaču se bez nje). Očekivanja se računaju
NEOVISNO iz baze (SQL) pa uspoređuju s onim što build_ctx vrati — test ne
prepisuje logiku motora, nego je provjerava izvana.
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


def _annual(cur, ticker, item):
    cur.execute(
        """SELECT fin.value_eur::float, f.fiscal_year FROM financials fin
           JOIN filings f ON f.id=fin.filing_id
           JOIN companies c ON c.id=f.company_id
           WHERE c.ticker=%s AND fin.item=%s AND f.period_type='annual'
                 AND f.basis='consolidated' AND fin.value_eur IS NOT NULL
           ORDER BY f.fiscal_year DESC LIMIT 1""", (ticker, item))
    return cur.fetchone()


def _interim(cur, ticker, item, period, fy):
    cur.execute(
        """SELECT fin.value_eur::float FROM financials fin
           JOIN filings f ON f.id=fin.filing_id
           JOIN companies c ON c.id=f.company_id
           WHERE c.ticker=%s AND fin.item=%s AND f.period_type=%s
                 AND f.fiscal_year=%s AND f.basis='consolidated'""",
        (ticker, item, period, fy))
    r = cur.fetchone()
    return r[0] if r else None


def test_ttm_gradi_se_iz_annual_plus_kvartala(conn):
    """HT: TTM NI = FY2025 + q1'26 − q1'25 (nezavisno izračunato SQL-om)."""
    from src.params_calibrated import build_params
    from src.valuation_methods import build_ctx
    ctx = build_ctx(conn, "HT", params=build_params("HT"))
    with conn.cursor() as cur:
        ann, fy = _annual(cur, "HT", "net_income_parent")
        q_cur = _interim(cur, "HT", "net_income_parent", "q1", fy + 1)
        q_prev = _interim(cur, "HT", "net_income_parent", "q1", fy)
    if q_cur is None or q_prev is None:
        pytest.skip("HT nema q1 par u bazi")
    got = ctx.data("net_income_parent")
    assert got is not None and got[0] is not None
    assert abs(got[0] - (ann + q_cur - q_prev)) < 1.0, (
        f"TTM mora biti FY+q1'−q1: {got[0]} vs {ann + q_cur - q_prev}")
    assert ctx.ttm_meta["net_income_parent"]["basis"] == "ttm"


def test_nekonzistentan_q4_blokira_ttm(conn):
    """PODR revenue: q4 kumulativ odstupa >5% od godišnjeg -> TTM se NE
    gradi (gate), osnova ostaje godišnja s razlogom."""
    from src.params_calibrated import build_params
    from src.valuation_methods import build_ctx
    with conn.cursor() as cur:
        ann, fy = _annual(cur, "PODR", "revenue")
        q4 = _interim(cur, "PODR", "revenue", "q4", fy)
    if q4 is None or abs(q4 / ann - 1) <= 0.05:
        pytest.skip("PODR q4/annual više nije nekonzistentan — gate nije testabilan ovdje")
    ctx = build_ctx(conn, "PODR", params=build_params("PODR"))
    got = ctx.data("revenue")
    assert abs(got[0] - ann) < 1.0, "kod nekonzistentnog q4 mora ostati godišnje"
    meta = ctx.ttm_meta["revenue"]
    assert meta["basis"] == "annual" and "nekonzistentna" in meta["reason"]


def test_rast_procjena_odrzivosti_bez_capa(conn):
    """M47: g1 = PROCJENA ODRŽIVOG RASTA (bez slijepog capa 10%). Rast smije
    biti > 10% kad je samofinanciran; source raspisuje procjenu i verdikt;
    signali raspisani; kratka serija => g_obs (medijan) is None (jedna
    godišnja usporedba nije stopa rasta); sanity strop 25%."""
    from src.growth_assessment import SANITY_MAX
    from src.params_calibrated import build_params
    from src.valuation_methods import build_ctx
    for t in ("KOEI", "HT", "CROS"):
        ctx = build_ctx(conn, t, params=build_params(t))
        gh = ctx.growth_hint or {}
        if gh.get("g1") is not None:
            assert gh["g1"] <= SANITY_MAX + 1e-9, f"{t}: g1 iznad sanity stropa"
            assert "PROCJENA ODRŽIVOG RASTA" in gh["source"], \
                f"{t}: source mora raspisati procjenu"
            assert gh.get("verdict"), f"{t}: nedostaje verdikt održivosti"
            sig = (gh.get("signals") or {}).get("signals", {})
            assert "g_terminal" in sig, f"{t}: signali moraju biti raspisani"
            if gh.get("short_series"):
                assert sig.get("g_obs") is None, (
                    f"{t}: kratka serija ne smije imati g_obs (medijan)")

    # KOEI je školski primjer: samofinanciran rast MORA smjeti preko 10%
    koei = build_ctx(conn, "KOEI", params=build_params("KOEI")).growth_hint or {}
    if koei.get("g1") is not None:
        assert koei["g1"] > 0.10, ("KOEI samofinanciran rast prignječen na "
                                   f"≤10% — cap nije uklonjen ({koei['g1']})")


def test_roe_pravilo_max_medijan_ttm09(conn):
    """ROE za kapitalne metode = max(3g medijan, TTM×0,9) kad TTM postoji."""
    from src.params_calibrated import build_params
    from src.valuation_methods import build_ctx
    ctx = build_ctx(conn, "HT", params=build_params("HT"))
    rh = ctx.roe_hint
    if not rh or rh.get("basis") != "ttm":
        pytest.skip("HT trenutno bez TTM ROE — pravilo nije testabilno na HT")
    if rh.get("median_3y") is not None:
        assert abs(rh["used"] - max(rh["median_3y"], rh["ttm_or_annual"] * 0.9)) < 1e-6
    else:
        assert abs(rh["used"] - rh["ttm_or_annual"] * 0.9) < 1e-6
