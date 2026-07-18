"""Kanonska taksonomija (`item` ključevi) iz specifikacije.

Extractor smije puniti SAMO ove ključeve. Derivirane stavke (DERIVED) ne
izvlači LLM — računa ih kod i upisuje s is_reported=FALSE.
"""
from __future__ import annotations

# Reported stavke po statementu.
INCOME = {
    "revenue",
    "material_costs",        # M18: materijalni troškovi (COGS proxy za DIO/DPO)
    "interest_expense",      # M18: rashodi od kamata (pokriće kamata)
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
    "current_assets",        # M18: kratkotrajna imovina (tekući omjer, Altman)
    "current_liabilities",   # M18: kratkoročne obveze
    "short_term_fin_assets", # M18: kratkotrajna fin. imovina (točan EV)
    "retained_earnings",     # M18: zadržana dobit (Altman)
    "inventories",           # M18: zalihe (DIO)
    "trade_receivables",     # M18: potraživanja od kupaca (DSO)
    "trade_payables",        # M18: obveze prema dobavljačima (DPO)
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
    "investing_cf",          # M18: neto CF iz investicijskih aktivnosti
    "financing_cf",          # M18: neto CF iz financijskih aktivnosti
}

SHARES = {
    "shares_outstanding",
    "treasury_shares",
}

# M18: brojčane (nemonetarne) stavke — bez skale i FX konverzije u loaderu
COUNTS = {
    "employees",             # broj zaposlenih (TFI 'Opći podaci')
}

# --- BANKA (M5): zaseban skup stavki — bankovni FI se NE mapira na
# industrijsku taksonomiju (nema revenue/EBITDA/EBIT u tom smislu). ---
BANK_INCOME = {
    "net_interest_income",      # neto kamatni prihod
    "net_fee_income",           # neto prihod od naknada i provizija
    "total_operating_income",   # ukupni operativni prihod (NII + naknade + ostalo)
    "loan_loss_provisions",     # rezervacije/trošak rizika (s predznakom)
}
BANK_BALANCE = {
    "loans_to_customers",
    "deposits_from_customers",
}
# Regulatorni OMJERI (decimalni razlomci, npr. 0.235 = 23,5%): često u
# bilješkama o adekvatnosti kapitala / Pillar 3, NE u glavnim tablicama.
# Loader ih NE skalira i NE konvertira (kao 'shares').
REGULATORY = {
    "cet1_ratio",
    "total_capital_ratio",
    "npl_ratio",
    "npl_coverage",
    "cost_of_risk",
}

# item -> statement (samo reported)
STATEMENT_OF = {}
for _stmt, _items in (
    ("income", INCOME),
    ("income", BANK_INCOME),
    ("balance", BALANCE),
    ("balance", BANK_BALANCE),
    ("cashflow", CASHFLOW),
    ("regulatory", REGULATORY),
    ("shares", SHARES),
    ("counts", COUNTS),
):
    for _it in _items:
        STATEMENT_OF[_it] = _stmt

REPORTED_ITEMS = set(STATEMENT_OF.keys())

# Derivirane stavke: (statement, item). Računa kod, is_reported=FALSE.
DERIVED_ITEMS = {
    "ebit": "income",            # M39: prihod − poslovni rashodi (identitet)
    "ebitda": "income",          # samo ako NIJE objavljen: ebit + d&a
    "depreciation_amortization": "income",  # M39: identitet ebitda − ebit
    "total_debt": "balance",     # debt_short + debt_long
    "net_debt": "balance",       # total_debt - cash_and_equivalents
    "free_cash_flow": "cashflow",  # operating_cf - capex
}
