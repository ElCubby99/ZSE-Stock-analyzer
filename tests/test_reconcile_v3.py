"""v3 FAZA A: testovi triangulacije sidra (medijan kvalificiranih metoda),
demote pravila, dividendnog sanity flaga i INA-tip iznimke.

SINTETIČKI — bez baze (reconcile prima gotove rezultate i Ctx)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.valuation_methods import Ctx, Params, ValueRange, reconcile  # noqa: E402


def _ctx(**kw):
    p = Params(cost_of_equity=kw.pop("r", 0.08),
               terminal_growth=kw.pop("gt", 0.04))
    p.rates_calibrated = True
    return Ctx(ticker="TEST", sector=kw.pop("sector", "bank"), is_group=False,
               holdings=[], has_segments=False, data=lambda i: None,
               shares_ex_treasury=1.0, params=p, **kw)


def _res(spec):
    """{key: (low, base, high, conf)} -> results dict za reconcile."""
    return {k: {"label": k, "range": ValueRange(lo, b, hi, {}, conf)}
            for k, (lo, b, hi, conf) in spec.items()}


def test_zona_je_medijan_kvalificiranih():
    """3 kvalificirane metode -> sredina zone = medijan baza, oblik
    osjetljivosti iz primarnog sidra."""
    res = _res({
        "justified_pb_roe": (9.0, 10.0, 11.0, 0.7),   # sidro (bank)
        "residual_income": (19.0, 20.0, 21.0, 0.7),
        "ddm_gordon": (28.0, 30.0, 32.0, 0.7),
    })
    rec = reconcile(res, "bank", ctx=_ctx())
    assert rec["qualified_methods"] == sorted(
        ["justified_pb_roe", "residual_income", "ddm_gordon"])
    # medijan = 20; oblik sidra jPB: 0,9x–1,1x
    assert abs(rec["zone_low"] - 20 * 0.9) < 1e-9
    assert abs(rec["zone_high"] - 20 * 1.1) < 1e-9
    assert "MEDIJAN" in rec["zone_note"]


def test_demote_pravilo_zapisano():
    """>=2 metode konvergiraju (±20%) a sidro divergira >30% -> vidljiv
    DEMOTE zapis (medijan ionako preuzima)."""
    res = _res({
        "justified_pb_roe": (9.0, 10.0, 11.0, 0.7),   # sidro divergira
        "residual_income": (19.0, 20.0, 21.0, 0.7),
        "ddm_gordon": (21.0, 22.0, 23.0, 0.7),        # 20 vs 22 = ±10%
    })
    rec = reconcile(res, "bank", ctx=_ctx())
    assert "DEMOTE" in rec["zone_note"]
    assert abs(rec["zone_low"] - 20 * 0.9) < 1e-9   # medijan preuzeo


def test_placeholder_i_degenerirane_ne_kvalificiraju():
    res = _res({
        "justified_pb_roe": (9.0, 10.0, 11.0, 0.7),
        "comps": (90.0, 100.0, 110.0, 0.3),           # placeholder conf
        "dcf_fcf": (5.0, 50.0, 95.0, 0.7),            # raspon 180% baze
    })
    rec = reconcile(res, "bank", ctx=_ctx())
    assert rec["qualified_methods"] == ["justified_pb_roe"]


def test_dividendni_sanity_flag_preniska():
    """Umjetni slučaj: D_sust/donji rub > r − g_terminal -> zona
    'u rekalibraciji' (Borisov test, formaliziran)."""
    res = _res({"justified_pb_roe": (9.0, 10.0, 11.0, 0.7)})
    ctx = _ctx(dsust_hint={"d_sust_ps": 1.0, "payout_used": 0.6})
    # 1,0 / 9,0 = 11,1% > 8% − 4% = 4%
    rec = reconcile(res, "bank", ctx=ctx)
    assert rec["recalibrating"] and "PRENISKA" in rec["recalibrating"]


def test_dividendni_sanity_bez_flaga_kad_pokriveno():
    res = _res({"justified_pb_roe": (30.0, 33.0, 36.0, 0.7)})
    ctx = _ctx(dsust_hint={"d_sust_ps": 1.0, "payout_used": 0.6})
    # 1,0 / 30 = 3,3% < 4% -> bez flaga
    rec = reconcile(res, "bank", ctx=ctx)
    assert rec["recalibrating"] is None


def test_obrnuti_flag_previsoka_zona():
    """Payout ~100%, a prinos iz D_sust na gornjem rubu << r − gT."""
    res = _res({"justified_pb_roe": (90.0, 100.0, 110.0, 0.7)})
    ctx = _ctx(dsust_hint={"d_sust_ps": 1.0, "payout_used": 0.95})
    # 1,0 / 110 = 0,9% < 0,5 × 4% = 2%
    rec = reconcile(res, "bank", ctx=ctx)
    assert rec["recalibrating"] and "PREVISOKA" in rec["recalibrating"]


def test_ina_tip_niski_float():
    res = _res({"justified_pb_roe": (9.0, 10.0, 11.0, 0.7)})
    rec = reconcile(res, "bank", ctx=_ctx(free_float_proxy=4.0))
    assert rec["low_float_note"] and "NIJE informativan" in rec["low_float_note"]
    rec2 = reconcile(res, "bank", ctx=_ctx(free_float_proxy=35.0))
    assert rec2["low_float_note"] is None
