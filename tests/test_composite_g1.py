"""v3.1 DIO 2: kompozitna stopa rasta g1 — acceptance testovi iz naloga.

g1 = medijan {g_obs (≥3g serija), g_sust (ROE×(1−payout)), g_terminal};
cap NAKON medijana (10% sa serijom / 8% bez); g1 ≥ 0 osim negativan g_obs
iz ≥3g serije; TVRDI clamp g1 ≤ r − 0,5 p.b.; putanja fade bez skoka.
"""
import pytest

from src.valuation_methods import composite_g1

R = 0.09  # tipični trošak kapitala za testove — dovoljno visok da clamp ne smeta


def test_bez_serije_sredina_gsust_i_terminala():
    """Nalog: 'firma s ROE 12% i payoutom 40% bez serije → g_sust 7,2%,
    g1 = medijan(7,2%, terminal)' — medijan dvaju = sredina."""
    g_sust = 0.12 * (1 - 0.40)
    assert g_sust == pytest.approx(0.072)
    g1, meta = composite_g1(None, g_sust, 0.025, R)
    assert g1 == pytest.approx((0.072 + 0.025) / 2, abs=1e-4)  # 4,85%
    assert "kratka serija" in meta["origin"]
    assert meta["signals"]["g_obs"] is None


def test_sa_serijom_medijan_je_serija():
    """Nalog: 'firma s 5g CAGR 6%, g_sust 9%, terminal 2,5% → g1 = 6%'
    (medijan tri signala = srednji = serija)."""
    g1, meta = composite_g1(0.06, 0.09, 0.025, R)
    assert g1 == pytest.approx(0.06, abs=1e-9)
    assert meta["winner"] == "g_obs"
    assert meta["origin"] == "serija"
    assert meta["badges"] == []


def test_cap_10_posto_sa_serijom_nakon_medijana():
    g1, meta = composite_g1(0.25, 0.30, 0.04, 0.20)
    assert g1 == pytest.approx(0.10)
    assert any("cap 10%" in b for b in meta["badges"])


def test_cap_8_posto_bez_serije():
    g1, meta = composite_g1(None, 0.22, 0.04, 0.20)
    assert g1 == pytest.approx(0.08)
    assert any("cap 8%" in b for b in meta["badges"])


def test_negativan_g1_samo_uz_seriju():
    """Trajno skupljanje smije u g1 SAMO kad ga dokazuje ≥3g serija."""
    g1, meta = composite_g1(-0.06, -0.03, 0.025, R)
    assert g1 < 0
    assert any("skupljanje" in b for b in meta["badges"])
    # bez serije: donja granica 0
    g1b, metab = composite_g1(None, -0.10, -0.02, R)
    assert g1b == 0.0
    assert any("donja granica 0" in b for b in metab["badges"])


def test_tvrdi_clamp_ukljucivo_zaokruzivanje():
    """g1 ≤ r − 0,5 p.b. UVIJEK — ni round(·, 4) ne smije probiti clamp
    (regresija: PODR r=7,127% → hard 6,627%, round bi dao 6,63%)."""
    r = 0.07127
    g1, meta = composite_g1(None, 0.1064, 0.04, r)
    assert g1 <= r - 0.005 + 1e-12
    assert any("TVRDI clamp" in b for b in meta["badges"])


def test_ttm_vs_lani_nije_ulaz():
    """Kompozit uopće ne prima TTM-vs-lani — jedna godišnja usporedba
    strukturno NE MOŽE biti izvor g1 (v3.1 DIO 2)."""
    import inspect
    sig = inspect.signature(composite_g1)
    assert set(sig.parameters) == {"g_obs", "g_sust", "g_terminal", "r"}


def test_putanja_bez_skoka():
    """Fade formula g_yr = g1 + (gT − g1)(yr−1)/4 — putanja monotona,
    korak konstantan (nema skoka između godina)."""
    g1, _ = composite_g1(0.06, 0.09, 0.025, R)
    gT = 0.025
    path = [g1 + (gT - g1) * (yr - 1) / 4 for yr in range(1, 6)]
    steps = [path[i + 1] - path[i] for i in range(4)]
    assert path[0] == pytest.approx(g1)
    assert path[-1] == pytest.approx(gT)
    for s in steps:
        assert s == pytest.approx((gT - g1) / 4, abs=1e-12)
    # monotono: svi koraci istog predznaka
    assert all(s <= 0 for s in steps) or all(s >= 0 for s in steps)


def test_samo_terminal_dostupan():
    g1, meta = composite_g1(None, None, 0.025, R)
    assert g1 == pytest.approx(0.025)
    assert meta["winner"] == "g_terminal"
