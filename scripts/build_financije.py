#!/usr/bin/env python3
"""M37: as-reported financijski izvještaji po dionici ->
frontend/public/data/fin/<TICKER>.json (tab FINANCIJE).

Pravila (nalog M37):
- SAMO is_reported=true stavke (izvedene veličine — ebitda, net_debt,
  total_debt, free_cash_flow — ostaju na Ključnim pokazateljima);
- vrijednosti su value_eur (HRK periodi već preračunati fiksnim tečajem
  7,5345 pri ingestu; filings.currency='HRK' -> badge na koloni);
- rupe su null (nikad 0); izvještaj koji ne postoji -> poštena poruka
  s linkom na izvorni dokument;
- restatement: godišnji filing vs 4Q kumulativ istog FY-a s razlikom
  >0,5 % -> prikazuje se godišnja (kasnija/revidirana) vrijednost,
  starija ide u "prev" (badge + klik u UI-ju);
- interim periodi su KUMULATIVI od početka godine (kako su objavljeni);
- kanonska nomenklatura sheme ekstrakcije, ne doslovni prijepis.
"""
import json
import os
import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402

OUT_DIR = "frontend/public/data/fin"
RESTATE_TOL = 0.005   # >0,5 % razlike = korigirano u kasnijem izvješću

# (item, hrvatska oznaka, indent, bold) — redoslijed = redoslijed prikaza
INCOME_ROWS = [
    ("revenue", "Poslovni prihodi", 0, True),
    ("other_operating_income", "Ostali poslovni prihodi", 1, False),
    ("operating_expenses", "Poslovni rashodi", 0, True),
    ("material_costs", "Materijalni troškovi", 1, False),
    ("depreciation_amortization", "Amortizacija", 1, False),
    ("ebit", "Operativna dobit (EBIT)", 0, True),
    ("net_financial_result", "Neto financijski rezultat", 0, False),
    ("interest_expense", "Rashodi od kamata", 1, False),
    ("net_interest_income", "Neto kamatni prihod", 0, True),
    ("net_fee_income", "Neto prihod od naknada i provizija", 0, False),
    ("total_operating_income", "Ukupni operativni prihod", 0, True),
    ("loan_loss_provisions", "Rezervacije za kreditne gubitke", 0, False),
    ("dividend_income_from_subsidiaries",
     "Prihod od dividendi ovisnih društava", 0, False),
    ("pretax_income", "Dobit prije poreza", 0, True),
    ("income_tax", "Porez na dobit", 0, False),
    ("net_income", "Neto dobit razdoblja", 0, True),
    ("net_income_parent", "pripada vlasnicima matice", 1, False),
    ("net_income_minority", "pripada manjinskim udjelima", 1, False),
]
BALANCE_ROWS = [
    ("total_assets", "Ukupna imovina", 0, True),
    ("current_assets", "Kratkotrajna imovina", 0, True),
    ("inventories", "Zalihe", 1, False),
    ("trade_receivables", "Potraživanja od kupaca", 1, False),
    ("short_term_fin_assets", "Kratkoročna financijska imovina", 1, False),
    ("cash_and_equivalents", "Novac i novčani ekvivalenti", 1, False),
    ("loans_to_customers", "Krediti i potraživanja od klijenata", 0, False),
    ("total_equity", "Ukupni kapital i rezerve", 0, True),
    ("equity_parent", "pripada vlasnicima matice", 1, False),
    ("minority_interests", "manjinski udjeli", 1, False),
    ("retained_earnings", "zadržana dobit", 1, False),
    ("current_liabilities", "Kratkoročne obveze", 0, True),
    ("trade_payables", "Obveze prema dobavljačima", 1, False),
    ("debt_short", "Kratkoročne financijske obveze (dug)", 0, False),
    ("debt_long", "Dugoročne financijske obveze (dug)", 0, False),
    ("deposits_from_customers", "Depoziti klijenata", 0, False),
]
CASHFLOW_ROWS = [
    ("operating_cf", "Novčani tok iz poslovnih aktivnosti", 0, True),
    ("investing_cf", "Novčani tok iz investicijskih aktivnosti", 0, True),
    ("capex", "Kapitalna ulaganja (capex)", 1, False),
    ("financing_cf", "Novčani tok iz financijskih aktivnosti", 0, True),
]
STATEMENTS = [("income", "Dobit i gubitak", INCOME_ROWS),
              ("balance", "Financijski položaj", BALANCE_ROWS),
              ("cashflow", "Novčani tok", CASHFLOW_ROWS)]
INTERIM_ORDER = {"q1": 1, "h1": 2, "9m": 3, "q4": 4}
INTERIM_LABEL = {"q1": "Q1", "h1": "H1", "9m": "9M", "q4": "4Q"}


def _fetch(cur, cid):
    """Sve is_reported vrijednosti firme + metapodaci filinga."""
    cur.execute(
        """SELECT f.statement, f.item, f.value_eur, f.basis,
                  fl.fiscal_year, fl.period_type, fl.currency,
                  fl.source_url, fl.published_at, fl.id
           FROM financials f JOIN filings fl ON fl.id = f.filing_id
           WHERE f.company_id = %s AND f.is_reported
             AND f.statement IN ('income','balance','cashflow','cash_flow')
           ORDER BY fl.fiscal_year, fl.period_type""", (cid,))
    out = []
    for st, item, v, basis, fy, pt, curr, url, pub, fid in cur.fetchall():
        out.append({
            "st": "cashflow" if st == "cash_flow" else st,
            "item": item, "v": float(v) if v is not None else None,
            "basis": basis or "consolidated", "fy": fy, "pt": pt,
            "hrk": curr == "HRK", "url": url,
            "pub": str(pub) if pub else None, "fid": fid,
        })
    return out


def _period_list(rows, kind):
    """[(fy, pt)] za prikaz, najnoviji prvi. kind: 'annual' | 'interim'."""
    if kind == "annual":
        keys = sorted({r["fy"] for r in rows if r["pt"] == "annual"},
                      reverse=True)
        return [(fy, "annual") for fy in keys]
    keys = {(r["fy"], r["pt"]) for r in rows if r["pt"] in INTERIM_ORDER}
    return sorted(keys, key=lambda k: (k[0], INTERIM_ORDER[k[1]]),
                  reverse=True)


def _cell_map(rows, basis, kind):
    """{(st, item, fy, pt): red} — za annual dodatno vraća q4 mapu
    (restatement usporedba)."""
    cells, q4 = {}, {}
    for r in rows:
        if r["basis"] != basis:
            continue
        if kind == "annual" and r["pt"] == "annual":
            cells[(r["st"], r["item"], r["fy"], "annual")] = r
        elif kind == "annual" and r["pt"] == "q4":
            q4[(r["st"], r["item"], r["fy"])] = r
        elif kind == "interim" and r["pt"] in INTERIM_ORDER:
            cells[(r["st"], r["item"], r["fy"], r["pt"])] = r
    return cells, q4


def _build_view(rows, basis, kind):
    periods = _period_list([r for r in rows if r["basis"] == basis], kind)
    if not periods:
        return None
    cells, q4 = _cell_map(rows, basis, kind)
    # meta kolone: filing po periodu (bilo koji red tog perioda)
    pmeta = []
    for fy, pt in periods:
        src = next((r for r in rows if r["basis"] == basis and r["fy"] == fy
                    and r["pt"] == pt), None)
        label = (f"FY{fy}" if pt == "annual"
                 else f"{INTERIM_LABEL[pt]} {fy}")
        pmeta.append({"key": f"{fy}-{pt}", "label": label, "fy": fy,
                      "pt": pt, "url": src["url"] if src else None,
                      "published": src["pub"] if src else None,
                      "hrk": bool(src and src["hrk"])})
    out = {}
    for st, st_label, registry in STATEMENTS:
        table_rows = []
        for item, label, indent, bold in registry:
            values, restated = {}, {}
            any_val = False
            for fy, pt in periods:
                r = cells.get((st, item, fy, pt))
                v = r["v"] if r else None
                values[f"{fy}-{pt}"] = v
                if v is not None:
                    any_val = True
                # restatement: godišnja objava vs 4Q kumulativ istog FY
                if kind == "annual" and r is not None and v is not None:
                    old = q4.get((st, item, fy))
                    if (old and old["v"] is not None
                            and abs(v - old["v"])
                            > RESTATE_TOL * max(abs(v), 1.0)):
                        restated[f"{fy}-{pt}"] = {
                            "prev": old["v"], "prev_url": old["url"],
                            "prev_label": "4Q kumulativ",
                        }
            if any_val:
                row = {"item": item, "label": label, "indent": indent,
                       "bold": bold, "values": values}
                if restated:
                    row["restated"] = restated
                table_rows.append(row)
        if table_rows:
            out[st] = {"label": st_label, "rows": table_rows}
    return {"periods": pmeta, "statements": out} if out else None


def build_company(cur, cid, ticker, name):
    rows = _fetch(cur, cid)
    if not rows:
        return None
    bases = sorted({r["basis"] for r in rows},
                   key=lambda b: 0 if b == "consolidated" else 1)
    views = {}
    for basis in bases:
        for kind in ("annual", "interim"):
            v = _build_view(rows, basis, kind)
            if v:
                views.setdefault(basis, {})[kind] = v
    if not views:
        return None
    # jedinica prikaza: dosljedna po firmi (mil. ako išta prelazi 100 M)
    mx = max((abs(r["v"]) for r in rows if r["v"] is not None), default=0)
    unit = "mil" if mx >= 100e6 else "tis"
    # izvještaji koji NISU u bazi (poštena poruka + link na zadnji filing)
    have = {r["st"] for r in rows}
    missing = []
    last = max(rows, key=lambda r: (r["fy"], r["pub"] or ""))
    for st, st_label, _reg in STATEMENTS:
        if st not in have:
            missing.append({"statement": st, "label": st_label,
                            "doc_url": last["url"]})
    return {
        "ticker": ticker, "name": name, "unit": unit,
        "bases": bases, "views": views, "missing": missing,
        "note": ("Stavke prema našoj standardiziranoj shemi ekstrakcije "
                 "(kanonska nomenklatura) — originalne oznake nalaze se u "
                 "izvornom dokumentu na koji vodi poveznica u zaglavlju "
                 "svake kolone. Periodi prije 2023. preračunati su iz HRK "
                 "po fiksnom tečaju 7,5345 HRK/EUR. Kvartalni prikaz "
                 "prikazuje kumulative od početka godine, kako su "
                 "objavljeni. Prazno polje (—) znači da stavka za taj "
                 "period nije ekstrahirana — nikad se ne prikazuje nula "
                 "umjesto nepoznate vrijednosti."),
    }


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    n = 0
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, ticker, name FROM companies WHERE is_live "
                    "ORDER BY ticker")
        companies = cur.fetchall()
        for cid, ticker, name in companies:
            data = build_company(cur, cid, ticker, name)
            if data is None:
                continue
            with open(f"{OUT_DIR}/{ticker}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            n += 1
    print(f"[financije] {n} firmi -> {OUT_DIR}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
