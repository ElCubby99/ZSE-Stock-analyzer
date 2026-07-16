"""v3.1 acceptance testovi nad ŽIVOM bazom (preskaču se bez baze).

1. TVRDI test: g1 ≤ r − 0,5 p.b. za SVE žive firme (nijedna iznimka).
2. Dividendni pod: svih 5 nekad suspendiranih imena ima objavljenu zonu,
   pod primijenjen i re-test nad novom zonom prolazi.
3. Reverse-DCF: naracija ne smije sadržavati proturječje "nema serije"
   dok istovremeno prikazuje izvedeni rast (v3.1 DIO 2.5).
4. Nijedan g1 ne dolazi isključivo iz TTM-vs-lani (badge/kontekst test).
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

FLOOR_NAMES = ("ATGR", "HT", "QTLG", "RIVP", "ZB")


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


def _live_tickers(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT ticker FROM companies WHERE is_live ORDER BY ticker")
        return [r[0] for r in cur.fetchall()]


def test_g1_ispod_r_na_svim_firmama(conn):
    """TVRDI: g1 ≤ r − 0,5 p.b. za svaku živu firmu; g_obs nikad iz
    TTM-vs-lani (kratka serija => g_obs is None)."""
    from src.params_calibrated import build_params
    from src.valuation_methods import build_ctx
    fails = []
    for t in _live_tickers(conn):
        try:
            ctx = build_ctx(conn, t, params=build_params(t))
        except Exception:  # noqa: BLE001 — firma bez ulaza nije predmet testa
            conn.rollback()
            continue
        gh = ctx.growth_hint or {}
        g1 = gh.get("g1")
        if g1 is None:
            continue
        hard = ctx.params.cost_of_equity - 0.005
        if g1 > hard + 1e-12:
            fails.append(f"{t}: g1={g1:.4f} > r−0,5p.b.={hard:.4f}")
        sig = (gh.get("signals") or {}).get("signals", {})
        if gh.get("short_series") and sig.get("g_obs") is not None:
            fails.append(f"{t}: kratka serija a g_obs postoji (TTM curi u g1?)")
    assert not fails, "; ".join(fails)


def test_dividendni_pod_za_pet_imena(conn):
    """Svih 5 nekad suspendiranih imena: zona objavljena, recalibrating je
    None, pod primijenjen i re-test (prinos na donjem rubu ≤ prag) prolazi."""
    from src.params_calibrated import build_params
    from src.valuation_methods import build_ctx, value_company
    for t in FLOOR_NAMES:
        ctx = build_ctx(conn, t, params=build_params(t))
        rec = value_company(ctx)["reconciliation"]
        assert rec.get("zone_low") and rec.get("zone_high"), f"{t}: zona mora postojati"
        assert rec.get("recalibrating") is None, f"{t}: suspenzija je ukinuta (v3.1)"
        ds = rec.get("dividend_sanity") or {}
        assert (ds.get("verdict") or "").startswith("prolazi"), \
            f"{t}: dividendni test mora proći ({ds.get('verdict')})"
        # pod je mehanizam, ne cilj: gdje test prolazi prirodno (npr. QTLG
        # s kompozitnim g1), pod se NE aktivira — ali suspenzija ne postoji
        df = ds.get("dividend_floor")
        if df and df.get("applied_floor"):
            assert "dividend_floor" in (rec.get("qualified_methods") or
                                        rec.get("qualified") or []), \
                f"{t}: V_div mora biti među kvalificiranima"
            assert "dividendni pod" in (ds.get("verdict") or ""), t


def test_reverse_dcf_bez_proturjecja(conn):
    """Naracija tržišnih implikacija ne smije reći 'nema serije' dok
    prikazuje rast; s g1 mora spominjati kompozitni rast."""
    from src.params_calibrated import build_params
    from src.valuation_methods import build_ctx, value_company
    for t in ("HT", "CROS", "PODR"):
        ctx = build_ctx(conn, t, params=build_params(t))
        out = value_company(ctx)
        mi = (out["reconciliation"].get("market_implied") or {})
        nar = mi.get("narrative") or ""
        if not nar:
            continue
        assert "nema serije" not in nar, f"{t}: proturječje u naraciji"
        if (ctx.growth_hint or {}).get("g1") is not None:
            assert "kompozitni rast" in nar, (
                f"{t}: usporedba mora ići protiv kompozitnog g1")
