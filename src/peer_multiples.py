"""Peer multiplikatori IZ BAZE (KORAK 2C): P/E, P/B, EV/EBITDA po peer skupu.

Ne izmišlja ništa: za svaki peer ticker čita zadnju cijenu (prices_eod),
dionice (v_shares_canonical, fallback financials.shares_outstanding) i zadnje
godišnje konsolidirane financije. Peer bez potrebnih ulaza se preskače uz
razlog. Rezultat je medijan po multiplu + pokrivenost — spreman za Params
(peer_pe/peer_pb/peer_ev_ebitda, placeholder=False tek kad pokrivenost valja).

Peer skupovi su odluka (vidi docs/peers.md); ovaj modul je samo mehanika.

CLI:
  python -m src.peer_multiples ATGR PODR RIVP PLAG ARNT   # ADRS peer skup
"""
from __future__ import annotations

import argparse
import statistics
import sys
from typing import Optional

from .db import get_conn


def _latest(cur, company_id: int, item: str) -> Optional[float]:
    cur.execute(
        """
        SELECT fin.value_eur
        FROM   financials fin JOIN filings f ON f.id = fin.filing_id
        WHERE  f.company_id = %s AND fin.item = %s
               AND f.period_type = 'annual' AND f.basis = 'consolidated'
        ORDER BY f.fiscal_year DESC LIMIT 1
        """,
        (company_id, item),
    )
    r = cur.fetchone()
    return float(r[0]) if r and r[0] is not None else None


def peer_row(cur, ticker: str) -> dict:
    cur.execute("SELECT id FROM companies WHERE ticker = %s", (ticker,))
    row = cur.fetchone()
    if not row:
        return {"ticker": ticker, "skip": "nije u companies (dodaj + ingestaj financije)"}
    cid = row[0]

    cur.execute("SELECT shares_ex_treasury FROM v_shares_canonical WHERE company_id=%s", (cid,))
    r = cur.fetchone()
    shares = float(r[0]) if r and r[0] else _latest(cur, cid, "shares_outstanding")

    cur.execute(
        "SELECT close_eur, trade_date FROM prices_eod WHERE company_id=%s "
        "AND close_eur IS NOT NULL ORDER BY trade_date DESC LIMIT 1", (cid,))
    r = cur.fetchone()
    price, price_date = (float(r[0]), r[1]) if r else (None, None)

    ni = _latest(cur, cid, "net_income_parent") or _latest(cur, cid, "net_income")
    eq = _latest(cur, cid, "equity_parent") or _latest(cur, cid, "total_equity")
    ebitda = _latest(cur, cid, "ebitda")
    net_debt = _latest(cur, cid, "net_debt")

    if price is None or not shares:
        return {"ticker": ticker, "skip": f"nema cijene/dionica (price={price}, shares={shares})"}
    mcap = price * shares
    out = {"ticker": ticker, "price": price, "price_date": str(price_date),
           "mcap": mcap, "skip": None}
    ebit = _latest(cur, cid, "ebit")
    out["pe"] = mcap / ni if ni and ni > 0 else None
    out["pb"] = mcap / eq if eq and eq > 0 else None
    out["ev_ebitda"] = ((mcap + net_debt) / ebitda
                        if ebitda and ebitda > 0 and net_debt is not None else None)
    # EV/EBIT: manje laska firmama s visokim D&A/dugom (doktrina v2 §2)
    out["ev_ebit"] = ((mcap + net_debt) / ebit
                      if ebit and ebit > 0 and net_debt is not None else None)
    # ROE peera: P/B je funkcija ROE (opravdani P/B) pa peer P/B bez peer ROE
    # konteksta nije prenosiv na firmu drugačije profitabilnosti
    out["roe"] = ni / eq if (ni and eq and ni > 0 and eq > 0) else None
    return out


def derive(tickers: list[str]) -> dict:
    with get_conn() as conn:
        cur = conn.cursor()
        rows = [peer_row(cur, t) for t in tickers]
    usable = [r for r in rows if not r.get("skip")]
    med = {}
    for k in ("pe", "pb", "ev_ebitda", "ev_ebit", "roe"):
        vals = [r[k] for r in usable if r.get(k)]
        med[k] = statistics.median(vals) if vals else None
        med[f"{k}_n"] = len(vals)
    return {"rows": rows, "median": med}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="peer multiplikatori iz baze")
    p.add_argument("tickers", nargs="+")
    a = p.parse_args(argv)
    res = derive(a.tickers)
    print(f"{'ticker':8} {'P/E':>8} {'P/B':>8} {'EV/EBITDA':>10}  napomena")
    for r in res["rows"]:
        if r.get("skip"):
            print(f"{r['ticker']:8} {'—':>8} {'—':>8} {'—':>10}  SKIP: {r['skip']}")
        else:
            f = lambda x: f"{x:.2f}" if x else "—"
            print(f"{r['ticker']:8} {f(r.get('pe')):>8} {f(r.get('pb')):>8} "
                  f"{f(r.get('ev_ebitda')):>10}  cijena {r['price']} ({r['price_date']})")
    m = res["median"]
    print(f"\nMEDIJAN:  P/E={m['pe'] and round(m['pe'],2)} (n={m['pe_n']})  "
          f"P/B={m['pb'] and round(m['pb'],2)} (n={m['pb_n']})  "
          f"EV/EBITDA={m['ev_ebitda'] and round(m['ev_ebitda'],2)} (n={m['ev_ebitda_n']})")
    print("-> unosi u Params(peer_pe=..., peer_pb=..., peer_ev_ebitda=..., placeholder=False)"
          " tek kad je n dovoljan (>=3) i pokrivenost prihvatljiva.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
