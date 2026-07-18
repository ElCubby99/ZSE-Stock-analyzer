"""M39: brana svježine valuacijskih ulaza.

Zahtjev (Boris): fer vrijednost i SVI parametri moraju se uvijek računati iz
ZADNJEG dostupnog izvješća — godišnjeg i kvartalnog. Ne smije se dogoditi da
u 2026. računamo s izvješćem iz 2024.

Korijenski uzrok koji ovo hvata (ADPL FY2025): valuacija čita "zadnju
GODIŠNJU vrijednost stavke". Ako zadnjem godišnjem filingu nedostaje neki
izvještaj (npr. novčani tok), ta se stavka razriješi na STARIJU godinu, a
razne zaštite je tamo i zaključaju — fer vrijednost tiho počiva na
zastarjelom ulazu.

Dvije klase nalaza:
  A) stale_input   — flow-stavka koju valuacija STVARNO koristi razrješava
                     se na godišnju bazu STARIJU od zadnjeg godišnjeg filinga
                     (introspekcija ctx.ttm_meta: entry['fy'] < latest_fy).
                     Ovo je izravna provjera "koristim li zadnje izvješće".
  B) incomplete_annual — zadnji godišnji filing nema temeljni izvještaj
                     (prihodi/bilanca za sve; novčani tok za nefinancijske) —
                     dijagnostika koja pokazuje IZVOR budućih stale_input
                     grešaka i prije nego što neka metoda posegne za stavkom.

Financijske firme (banke/osiguranje) NEMAJU standardni novčani tok u
valuaciji (RI/DDM nad kapitalom) — cashflow se za njih ne traži.
"""
from __future__ import annotations

from typing import Any

from .valuation_methods import FINANCIAL_SECTORS

# flow-stavke čija godišnja baza mora biti zadnja objavljena godina
_FLOW_ITEMS = {
    "net_income_parent", "net_income", "revenue", "total_operating_income",
    "ebitda", "ebit", "depreciation_amortization", "operating_cf", "capex",
    "free_cash_flow",
}
# temeljni izvještaji koje zadnji godišnji filing mora imati
_CORE_STATEMENTS_NONFIN = ("income", "balance", "cashflow")
_CORE_STATEMENTS_FIN = ("income", "balance")
# neki obveznici koriste alias 'cash_flow' (stari parser) — tretiraj isto
_CF_ALIASES = {"cashflow", "cash_flow"}


def _latest_annual_fy(cur, company_id: int) -> int | None:
    cur.execute(
        """SELECT max(fiscal_year) FROM filings
           WHERE company_id=%s AND doc_type='financial_report'
                 AND period_type='annual'""", (company_id,))
    return cur.fetchone()[0]


def _latest_annual_statements(cur, company_id: int) -> set[str]:
    cur.execute(
        """SELECT DISTINCT fin.statement
           FROM filings f JOIN financials fin ON fin.filing_id=f.id
           WHERE f.company_id=%s AND f.doc_type='financial_report'
                 AND f.period_type='annual'
                 AND f.fiscal_year=(SELECT max(fiscal_year) FROM filings
                     WHERE company_id=%s AND doc_type='financial_report'
                           AND period_type='annual')""",
        (company_id, company_id))
    return {r[0] for r in cur.fetchall() if r[0]}


def audit_company(conn, ticker: str) -> dict[str, Any]:
    """Vrati {ticker, sector, latest_fy, findings:[...]} za jednu firmu.
    findings su prazni kad je sve svježe."""
    from .params_calibrated import build_params
    from .valuation_methods import build_ctx, value_company

    findings: list[dict[str, Any]] = []
    with conn.cursor() as cur:
        cur.execute("SELECT id, sector FROM companies WHERE ticker=%s", (ticker,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"nepoznat ticker {ticker}")
        cid, sector = row
        latest_fy = _latest_annual_fy(cur, cid)
        if latest_fy is None:
            return {"ticker": ticker, "sector": sector,
                    "latest_fy": None, "findings": []}

        # A) introspekcija stvarno korištenih ulaza
        ctx = build_ctx(conn, ticker, params=build_params(ticker))
        value_company(ctx)   # popuni ttm_meta pozivima data()
        for item, meta in (ctx.ttm_meta or {}).items():
            if item not in _FLOW_ITEMS:
                continue
            base_fy = meta.get("fy")
            if base_fy is not None and base_fy < latest_fy:
                findings.append({
                    "type": "stale_input", "item": item,
                    "used_fy": base_fy, "latest_fy": latest_fy,
                    "basis": meta.get("basis"),
                    "detail": (f"{item}: valuacija koristi godišnju bazu "
                               f"FY{base_fy}, a zadnji godišnji filing je "
                               f"FY{latest_fy} (nedostaje mu ta stavka)")})

        # B) potpunost zadnjeg godišnjeg filinga
        stmts = _latest_annual_statements(cur, cid)
        has = {s if s != "cash_flow" else "cashflow" for s in stmts}
        required = (_CORE_STATEMENTS_FIN if sector in FINANCIAL_SECTORS
                    else _CORE_STATEMENTS_NONFIN)
        for st in required:
            present = st in has or (st == "cashflow" and (_CF_ALIASES & stmts))
            if not present:
                findings.append({
                    "type": "incomplete_annual", "statement": st,
                    "latest_fy": latest_fy,
                    "detail": (f"zadnji godišnji filing FY{latest_fy} nema "
                               f"'{st}' izvještaj")})
    return {"ticker": ticker, "sector": sector,
            "latest_fy": latest_fy, "findings": findings}


def audit_all(conn) -> list[dict[str, Any]]:
    """Audit svih live firmi; vrati samo firme s nalazima (prazno = sve OK)."""
    with conn.cursor() as cur:
        cur.execute("SELECT ticker FROM companies WHERE is_live ORDER BY ticker")
        tickers = [r[0] for r in cur.fetchall()]
    out = []
    for t in tickers:
        rep = audit_company(conn, t)
        if rep["findings"]:
            out.append(rep)
    return out


def _cli() -> int:
    import sys
    from .db import get_conn
    only = [a.upper() for a in sys.argv[1:] if not a.startswith("-")]
    with get_conn() as conn:
        reports = ([audit_company(conn, t) for t in only] if only
                   else audit_all(conn))
    bad = [r for r in reports if r["findings"]]
    if not bad:
        print("[freshness] svi valuacijski ulazi svježi (zadnje izvješće)")
        return 0
    for r in bad:
        print(f"\n{r['ticker']} (FY{r['latest_fy']}, {r['sector']}):")
        for f in r["findings"]:
            print(f"  [{f['type']}] {f['detail']}")
    stale = sum(1 for r in bad for f in r["findings"]
                if f["type"] == "stale_input")
    print(f"\n[freshness] {len(bad)} firmi s nalazima "
          f"({stale} stale_input — zastarjeli valuacijski ulaz)")
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(_cli())
