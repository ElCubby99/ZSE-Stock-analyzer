"""M-FOND2: čiste funkcije exporta serija za graf fondova — prinosi
(YTD/1g/3g/5g/10g), mjesečni downsample (zadnja vrijednost u mjesecu) i
dnevni rep. Bez baze — sintetička serija."""
import datetime as dt

from scripts.build_fondovi import _daily_tail, _monthly, _returns


def _series(years=12, step_days=7, start_v=100.0, growth_per_year=0.05):
    """Tjedna serija koja raste growth_per_year godišnje."""
    end = dt.date(2026, 6, 30)
    start = end - dt.timedelta(days=int(365.25 * years))
    out, d = [], start
    while d <= end:
        t = (d - start).days / 365.25
        out.append((d, start_v * (1 + growth_per_year) ** t))
        d += dt.timedelta(days=step_days)
    return out


def test_returns_standardni_set():
    s = _series()
    r = _returns(s)
    for key, years in [("y1", 1), ("y3", 3), ("y5", 5), ("y10", 10)]:
        expect = 1.05 ** years - 1
        assert abs(r[key] - expect) < 0.01, f"{key}: {r[key]} vs {expect}"
    assert r["ytd"] is not None and 0 < r["ytd"] < 0.05


def test_returns_prekratka_serija_daje_none():
    s = _series(years=2)
    r = _returns(s)
    assert r["y1"] is not None
    assert r["y5"] is None and r["y10"] is None, "serija ne seže -> None, ne 0"


def test_monthly_zadnja_vrijednost_u_mjesecu():
    s = [(dt.date(2026, 1, 5), 10.0), (dt.date(2026, 1, 28), 11.0),
         (dt.date(2026, 2, 3), 12.0)]
    m = _monthly(s)
    assert m == [["2026-01-28", 11.0], ["2026-02-03", 12.0]]


def test_daily_tail_rez():
    s = _series(years=3, step_days=1)
    d = _daily_tail(s, days=400)
    assert d[0][0] >= "2025-05-01" and d[-1][0] == "2026-06-30"
    assert len(d) > 300
