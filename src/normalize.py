"""Normalizacija: value_raw -> value_eur (skala + HRK->EUR) i derivacije."""
from __future__ import annotations

from typing import Any

from . import config


def to_eur(value_raw: float | None, reporting_scale: int, currency: str,
           hrk_rate: float | None = None) -> float | None:
    """value_eur = value_raw * scale; HRK iznosi se dijele fiksnim tečajem."""
    if value_raw is None:
        return None
    val = float(value_raw) * float(reporting_scale)
    if (currency or "EUR").upper() == "HRK":
        val = val / float(hrk_rate if hrk_rate is not None else config.HRK_EUR_RATE)
    return val


def derive_items(reported_eur: dict[str, float]) -> dict[str, float]:
    """Izračunaj derivirane stavke iz već normaliziranih (EUR) reported vrijednosti.

    Vraća {item: value_eur} samo za stavke koje se mogu izračunati.
    Sve ove dobivaju is_reported=FALSE pri upisu.
    """
    g = reported_eur.get
    out: dict[str, float] = {}

    # ebitda samo ako NIJE objavljen, a imamo ebit i amortizaciju
    if g("ebitda") is None and g("ebit") is not None and g("depreciation_amortization") is not None:
        out["ebitda"] = g("ebit") + g("depreciation_amortization")

    # total_debt = kratkoročni + dugoročni kamatonosni dug
    if g("debt_short") is not None or g("debt_long") is not None:
        out["total_debt"] = (g("debt_short") or 0.0) + (g("debt_long") or 0.0)

    # net_debt = total_debt - cash
    if "total_debt" in out and g("cash_and_equivalents") is not None:
        out["net_debt"] = out["total_debt"] - g("cash_and_equivalents")

    # free_cash_flow = operating_cf - capex
    if g("operating_cf") is not None and g("capex") is not None:
        out["free_cash_flow"] = g("operating_cf") - g("capex")

    return out
