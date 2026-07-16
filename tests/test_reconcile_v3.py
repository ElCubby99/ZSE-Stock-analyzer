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


def test_dividendni_pod_umjesto_suspenzije():
    """v3.1: umjetni slučaj gdje bi test pao -> V_div ulazi u medijan,
    donji rub se diže na pod, re-test PROLAZI, zona OBJAVLJENA."""
    res = _res({"justified_pb_roe": (9.0, 10.0, 11.0, 0.7)})
    ctx = _ctx(dsust_hint={"d_sust_ps": 1.0, "payout_used": 0.6})
    # prag: r 8% − g kapitalni 2,5% = 5,5%; V_div = 1,0/0,055 = 18,18
    rec = reconcile(res, "bank", ctx=ctx)
    assert rec["recalibrating"] is None, "suspenzija je ukinuta (v3.1)"
    ds = rec["dividend_sanity"]
    df = ds["dividend_floor"]
    assert df and df["applied_floor"]
    assert abs(df["v_div"] - 1.0 / 0.055) < 0.01
    assert rec["zone_low"] >= df["v_div"] - 1e-9, "donji rub = pod"
    # re-test nad novom zonom prolazi po konstrukciji
    assert ds["d_sust_ps"] / rec["zone_low"] <= ds["threshold"] + 1e-9
    assert ds["verdict"] == "prolazi (uz dividendni pod)"
    assert "dividend_floor" in rec["qualified_methods"]


def test_dividendni_sanity_bez_flaga_kad_pokriveno():
    res = _res({"justified_pb_roe": (30.0, 33.0, 36.0, 0.7)})
    ctx = _ctx(dsust_hint={"d_sust_ps": 1.0, "payout_used": 0.6})
    # 1,0 / 30 = 3,3% < 4% -> bez flaga
    rec = reconcile(res, "bank", ctx=ctx)
    assert rec["recalibrating"] is None


def test_previsoka_bez_suspenzije():
    """v3.1: payout ~100% i premalen prinos na gornjem rubu -> V_div u
    medijan (vuče dolje), bez suspenzije."""
    res = _res({"justified_pb_roe": (90.0, 100.0, 110.0, 0.7)})
    ctx = _ctx(dsust_hint={"d_sust_ps": 1.0, "payout_used": 0.95})
    rec = reconcile(res, "bank", ctx=ctx)
    assert rec["recalibrating"] is None
    assert "dividend_floor" in rec["qualified_methods"]
    ds = rec["dividend_sanity"]
    assert ds["dividend_floor"]["applied_floor"] is False
    assert rec["zone_low"] < 90.0, "V_div u medijanu mora povući zonu naniže"


def test_ina_tip_niski_float():
    res = _res({"justified_pb_roe": (9.0, 10.0, 11.0, 0.7)})
    rec = reconcile(res, "bank", ctx=_ctx(free_float_proxy=4.0))
    assert rec["low_float_note"] and "NIJE informativan" in rec["low_float_note"]
    rec2 = reconcile(res, "bank", ctx=_ctx(free_float_proxy=35.0))
    assert rec2["low_float_note"] is None


def test_pod_se_ne_aktivira_gdje_test_prolazi():
    """v3.1 regresija (ZABA/CROS princip): kad sanity prolazi, V_div se NE
    uključuje i zona je identična kao bez dsust_hinta."""
    spec = {"justified_pb_roe": (30.0, 33.0, 36.0, 0.7)}
    rec_bez = reconcile(_res(spec), "bank", ctx=_ctx())
    rec_s = reconcile(_res(spec), "bank",
                      ctx=_ctx(dsust_hint={"d_sust_ps": 1.0,
                                           "payout_used": 0.6}))
    assert rec_s["dividend_sanity"]["verdict"] == "prolazi"
    assert "dividend_floor" not in rec_s["qualified_methods"]
    assert abs(rec_s["zone_low"] - rec_bez["zone_low"]) < 1e-9
    assert abs(rec_s["zone_high"] - rec_bez["zone_high"]) < 1e-9
