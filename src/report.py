"""Točka 5: usporedna tablica za N godina iz v_financials_current.

Redovi: revenue, ebit, ebitda, neto dobit (ukupna + matica), kapital (ukupni +
matica), net_debt, shares. Ukupna neto dobit/kapital su grupne brojke koje se
poklapaju sa sidrima iz priopćenja; "matica" je dio pripisan vlasnicima matice
(za valuaciju dioničara). Boris ovo provjerava očima protiv stvarnosti.
"""
from __future__ import annotations

ROWS = [
    ("revenue", "Prihodi (revenue)"),
    ("ebit", "EBIT"),
    ("ebitda", "EBITDA"),
    ("net_income", "Neto dobit (ukupna)"),
    ("net_income_parent", "Neto dobit (matica)"),
    ("total_equity", "Kapital (ukupni)"),
    ("equity_parent", "Kapital (matica)"),
    ("net_debt", "Neto dug"),
    ("shares_outstanding", "Broj dionica"),
]


def build_comparison(conn, ticker: str, years: list[int], *,
                     basis: str = "consolidated", period_type: str = "annual"):
    """Vrati {item: {year: value_eur}} za tražene godine."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM companies WHERE ticker = %s", (ticker,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Nepoznat ticker: {ticker}")
        company_id = row[0]
        cur.execute(
            """
            SELECT item, fiscal_year, value_eur
            FROM v_financials_current
            WHERE company_id = %s AND basis = %s AND period_type = %s
              AND fiscal_year = ANY(%s)
            """,
            (company_id, basis, period_type, years),
        )
        data: dict[str, dict[int, float]] = {}
        for item, year, value_eur in cur.fetchall():
            if value_eur is not None:
                data.setdefault(item, {})[year] = float(value_eur)
    return data


def _fmt(val):
    if val is None:
        return "—"
    if abs(val) >= 1000:
        return f"{val:,.0f}".replace(",", ".")
    return f"{val:,.2f}"


def render_comparison(conn, ticker: str, years: list[int], **kw) -> str:
    data = build_comparison(conn, ticker, years, **kw)
    years = sorted(years)
    w_label = max(len(lbl) for _, lbl in ROWS) + 2
    w_col = 18

    header = "Stavka".ljust(w_label) + "".join(str(y).rjust(w_col) for y in years)
    sep = "-" * len(header)
    lines = [header, sep]
    for item, label in ROWS:
        cells = "".join(_fmt(data.get(item, {}).get(y)).rjust(w_col) for y in years)
        lines.append(label.ljust(w_label) + cells)
    note = (f"\n{ticker} | {kw.get('basis', 'consolidated')} | "
            f"{kw.get('period_type', 'annual')} | iznosi u EUR")
    return "\n".join(lines) + "\n" + note
