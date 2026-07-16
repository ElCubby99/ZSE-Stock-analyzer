"""M-BOND: deterministički izračuni za obveznice — bez pretpostavki o rastu,
bez fer-zone. Sve formule su dokumentirane na /metodologija (sekcija
"Obveznice").

Konvencije:
- cijene su ČISTE (clean), u % nominale — kako kotiraju na ZSE
- konvencija dana: ACT/ACT (ICMA) — udjel kuponskog razdoblja; gdje izvor
  konvencije nije potvrđen iz prospekta, UI nosi "pretpostavka" badge
- raspored kupona: unatrag od dospijeća u koracima 12/freq mjeseci
- YTM: bisekcija na dirty = Σ CF/(1+y)^t (t u godinama do isplate, ACT/ACT
  udjeli) — deterministična, konvergira za svaki y > -100%
"""
from __future__ import annotations

import datetime as dt


def _add_months(d: dt.date, months: int) -> dt.date:
    y, m = divmod(d.month - 1 + months, 12)
    y += d.year
    m += 1
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
                      else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return dt.date(y, m, day)


def coupon_schedule(maturity: dt.date, freq: int, settlement: dt.date) -> list[dt.date]:
    """Svi kuponski datumi NAKON settlementa, unatrag od dospijeća."""
    step = -12 // freq
    dates = [maturity]
    d = maturity
    # generiraj unatrag dovoljno duboko (do prije settlementa)
    while d > settlement:
        d = _add_months(d, step)
        dates.append(d)
    dates.sort()
    return [x for x in dates if x > settlement]


def _prev_coupon(maturity: dt.date, freq: int, settlement: dt.date) -> dt.date:
    step = -12 // freq
    d = maturity
    while d > settlement:
        prev = _add_months(d, step)
        if prev <= settlement:
            return prev
        d = prev
    return d


def accrued_interest(coupon_pct: float, freq: int, maturity: dt.date,
                     settlement: dt.date) -> float:
    """Obračunata kamata po ACT/ACT (ICMA): kupon/freq × dani od zadnjeg
    kupona / dani u kuponskom razdoblju. U % nominale."""
    nxt = coupon_schedule(maturity, freq, settlement)
    if not nxt:
        return 0.0
    next_c = nxt[0]
    prev_c = _prev_coupon(maturity, freq, settlement)
    period = (next_c - prev_c).days
    if period <= 0:
        return 0.0
    return (coupon_pct / freq) * ((settlement - prev_c).days / period)


def _cashflows(coupon_pct: float, freq: int, maturity: dt.date,
               settlement: dt.date) -> list[tuple[float, float]]:
    """[(t_godina, iznos_u_%_nominale)] — ACT/ACT vremena od settlementa."""
    dates = coupon_schedule(maturity, freq, settlement)
    out = []
    for d in dates:
        t = (d - settlement).days / 365.25
        cf = coupon_pct / freq + (100.0 if d == maturity else 0.0)
        out.append((t, cf))
    return out


def dirty_price(y: float, coupon_pct: float, freq: int, maturity: dt.date,
                settlement: dt.date) -> float:
    return sum(cf / (1 + y) ** t
               for t, cf in _cashflows(coupon_pct, freq, maturity, settlement))


def ytm(clean_price_pct: float, coupon_pct: float, freq: int,
        maturity: dt.date, settlement: dt.date,
        tol: float = 1e-8) -> float | None:
    """Prinos do dospijeća (godišnji, decimalno) bisekcijom. None ako ulazi
    nisu potpuni ili je obveznica dospjela."""
    if clean_price_pct is None or clean_price_pct <= 0 or maturity <= settlement:
        return None
    target = clean_price_pct + accrued_interest(coupon_pct, freq, maturity, settlement)
    lo, hi = -0.99, 5.0
    f = lambda y: dirty_price(y, coupon_pct, freq, maturity, settlement) - target  # noqa: E731
    if f(lo) < 0 or f(hi) > 0:  # cijena izvan raspona rješenja
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2


def durations(clean_price_pct: float, coupon_pct: float, freq: int,
              maturity: dt.date, settlement: dt.date) -> tuple[float, float] | None:
    """(Macaulay u godinama, modificirana). None bez potpunih ulaza."""
    y = ytm(clean_price_pct, coupon_pct, freq, maturity, settlement)
    if y is None:
        return None
    cfs = _cashflows(coupon_pct, freq, maturity, settlement)
    pv = [(t, cf / (1 + y) ** t) for t, cf in cfs]
    total = sum(p for _, p in pv)
    if total <= 0:
        return None
    mac = sum(t * p for t, p in pv) / total
    return mac, mac / (1 + y)


def current_yield(clean_price_pct: float, coupon_pct: float) -> float | None:
    """Tekući prinos = kupon / čista cijena."""
    if not clean_price_pct or clean_price_pct <= 0:
        return None
    return coupon_pct / clean_price_pct
