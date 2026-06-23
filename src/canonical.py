"""Kanonska taksonomija (`item` ključevi) iz specifikacije.

Extractor smije puniti SAMO ove ključeve. Derivirane stavke (DERIVED) ne
izvlači LLM — računa ih kod i upisuje s is_reported=FALSE.
"""
from __future__ import annotations

# Reported stavke po statementu.
INCOME = {
    "revenue",
    "other_operating_income",
    "operating_expenses",
    "depreciation_amortization",
    "ebit",
    "ebitda",
    "net_financial_result",
    "pretax_income",
    "income_tax",
    "net_income",
    "net_income_parent",
    "net_income_minority",
}

BALANCE = {
    "total_assets",
    "total_equity",
    "equity_parent",
    "minority_interests",
    "debt_short",
    "debt_long",
    "cash_and_equivalents",
}

CASHFLOW = {
    "operating_cf",
    "capex",
}

SHARES = {
    "shares_outstanding",
    "treasury_shares",
}

# item -> statement (samo reported)
STATEMENT_OF = {}
for _stmt, _items in (
    ("income", INCOME),
    ("balance", BALANCE),
    ("cashflow", CASHFLOW),
    ("shares", SHARES),
):
    for _it in _items:
        STATEMENT_OF[_it] = _stmt

REPORTED_ITEMS = set(STATEMENT_OF.keys())

# Derivirane stavke: (statement, item). Računa kod, is_reported=FALSE.
DERIVED_ITEMS = {
    "ebitda": "income",          # samo ako NIJE objavljen: ebit + d&a
    "total_debt": "balance",     # debt_short + debt_long
    "net_debt": "balance",       # total_debt - cash_and_equivalents
    "free_cash_flow": "cashflow",  # operating_cf - capex
}
