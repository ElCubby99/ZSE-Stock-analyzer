"""M18 KORAK 3: derivacijski sloj pokazatelja — DETERMINISTIČKI kod, ne LLM.

Formule i pravila: docs/indicators.md. Tvrda pravila (KORAK 4):
  - hijerarhija nazivnika: TTM (kad su kvartali u bazi) > FY s oznakom > "—";
    FY se NIKAD ne prikazuje kao TTM.
  - TTM SAMO za tokovne stavke (P&L, CF): TTM = FY_prošla + YTD_tekuća −
    YTD_lanjska_ista; bilanca = zadnje stanje ("Kvartalno dd.mm.").
  - diskretni kvartali: Q2=H1−Q1, Q3=9M−H1, Q4=FY−9M; negativan izvedeni
    kvartal tokovne stavke -> needs_review oznaka, kvartal se NE koristi.
  - YoY isključivo isti-na-isti period (sezonalnost).
  - sektorski guard: banka/osiguranje i holding -> n/p s razlogom.
Svaki pokazatelj nosi {v, unit, basis, formula} — izvor/izvedenica vidljiva.
"""
from __future__ import annotations

import datetime
from typing import Optional

FIN_SECTORS = {"bank", "insurance"}
PT_ORDER = {"q1": 1, "h1": 2, "9m": 3, "q4": 4, "annual": 4}
PT_END = {"q1": "31.03.", "h1": "30.06.", "9m": "30.09.", "q4": "31.12.",
          "annual": "31.12."}
FLOW_STMTS = {"income", "cashflow"}


def _load_periods(cur, company_id: int) -> dict:
    """{(fy, period_type): {item: value}} — konsolidirano, reported+derived."""
    cur.execute(
        """SELECT f.fiscal_year, f.period_type, fin.item, fin.value_eur
           FROM financials fin JOIN filings f ON f.id = fin.filing_id
           WHERE f.company_id=%s AND f.basis='consolidated'
                 AND f.period_type IN ('annual','q1','h1','9m','q4')
                 AND fin.value_eur IS NOT NULL""", (company_id,))
    out: dict = {}
    for fy, pt, item, val in cur.fetchall():
        out.setdefault((fy, pt), {})[item] = float(val)
    return out


class Ind:
    """Kontekst izračuna za jednu firmu."""

    def __init__(self, cur, company_id: int, sector: Optional[str], is_holding: bool):
        self.cur = cur
        self.cid = company_id
        self.sector = sector
        self.fin = sector in FIN_SECTORS
        self.holding = is_holding
        self.P = _load_periods(cur, company_id)
        self.flags: list[str] = []
        years = [fy for fy, pt in self.P if pt in ("annual", "q4")]
        self.fy_last = max(years) if years else None

    # ---------- nazivnici ----------
    def _fy_flow(self, item):
        """FY vrijednost tokovne stavke: annual ima prednost, pa q4 kumulativ."""
        if self.fy_last is None:
            return None, None
        for pt in ("annual", "q4"):
            v = self.P.get((self.fy_last, pt), {}).get(item)
            if v is not None:
                return v, f"FY{self.fy_last}"
        return None, None

    def flow(self, item):
        """-> (vrijednost, basis) uz TTM > FY > None. NIKAD FY kao TTM."""
        # najnoviji YTD nakon zadnje FY godine
        cands = [(fy, pt) for (fy, pt) in self.P
                 if pt in ("q1", "h1", "9m") and self.fy_last is not None
                 and fy > self.fy_last]
        if cands:
            fy, pt = max(cands, key=lambda x: (x[0], PT_ORDER[x[1]]))
            cur_v = self.P[(fy, pt)].get(item)
            prev_v = self.P.get((fy - 1, pt), {}).get(item)
            fy_v, _ = self._fy_flow(item)
            if None not in (cur_v, prev_v, fy_v):
                return fy_v + cur_v - prev_v, f"TTM (do {PT_END[pt]}{fy}.)"
        return self._fy_flow(item)

    def bal(self, item):
        """-> (vrijednost, basis) zadnjeg stanja bilance ('Kvartalno dd.mm.')."""
        cands = [(fy, pt) for (fy, pt) in self.P if self.P[(fy, pt)].get(item) is not None]
        if not cands:
            return None, None
        fy, pt = max(cands, key=lambda x: (x[0], PT_ORDER[x[1]]))
        label = (f"Kvartalno ({PT_END[pt]}{fy}.)" if pt in ("q1", "h1", "9m")
                 else f"FY{fy} (31.12.{fy}.)")
        return self.P[(fy, pt)][item], label

    def quarters(self, item):
        """Diskretni kvartali [(fy, q, vrijednost)]; negativan izvedeni ->
        flag + preskok (restatement/nesklad se ne prikazuje tiho)."""
        out = []
        years = sorted({fy for fy, _ in self.P})
        for fy in years:
            g = lambda pt: self.P.get((fy, pt), {}).get(item)
            fyv = g("annual") if g("annual") is not None else g("q4")
            seq = [("Q1", g("q1"), None), ("Q2", g("h1"), g("q1")),
                   ("Q3", g("9m"), g("h1")), ("Q4", fyv, g("9m"))]
            for q, cum, prev in seq:
                if cum is None or (q != "Q1" and prev is None):
                    continue
                v = cum if q == "Q1" else cum - prev
                if item in ("revenue", "total_operating_income") and v < 0:
                    self.flags.append(f"{item} {fy}{q}: negativan izvedeni kvartal "
                                      "(restatement?) -> isključen, needs_review")
                    continue
                out.append((fy, q, v))
        return out

    def yoy_last_quarter(self, item):
        """YoY zadnjeg diskretnog kvartala — ISKLJUČIVO isti-na-isti period."""
        qs = {(fy, q): v for fy, q, v in self.quarters(item)}
        if not qs:
            return None, None
        (fy, q) = max(qs, key=lambda k: (k[0], int(k[1][1])))
        prev = qs.get((fy - 1, q))
        if prev in (None, 0) or prev < 0:
            return None, f"{fy}{q}"
        return (qs[(fy, q)] / prev - 1), f"{fy}{q} vs {fy - 1}{q}"


def _i(k, v, unit, basis, formula, note=None):
    return {"k": k, "v": v, "unit": unit, "basis": basis, "formula": formula,
            **({"note": note} if note else {})}


def _np(k, reason):
    return {"k": k, "v": None, "unit": None, "basis": None, "formula": None,
            "np_reason": reason}


def _returns(cur, share_class_id):
    """Povrati po najbližem trgovanom danu <= ciljni datum + 52tj s datumima."""
    cur.execute("""SELECT trade_date, close_eur FROM prices_eod
                   WHERE share_class_id=%s AND close_eur IS NOT NULL
                   ORDER BY trade_date""", (share_class_id,))
    rows = cur.fetchall()
    if not rows:
        return None
    dates = [r[0] for r in rows]
    last_d, last_p = dates[-1], float(rows[-1][1])

    def at(target):
        lo, hi = 0, len(dates) - 1
        best = None
        while lo <= hi:
            mid = (lo + hi) // 2
            if dates[mid] <= target:
                best = mid; lo = mid + 1
            else:
                hi = mid - 1
        return float(rows[best][1]) if best is not None else None

    def ret(days=None, ytd=False, years=None):
        if ytd:
            target = datetime.date(last_d.year - 1, 12, 31)
        elif years:
            target = last_d - datetime.timedelta(days=365 * years)
            if target < dates[0]:
                return None                      # serija prekratka -> n/p
        else:
            target = last_d - datetime.timedelta(days=days)
            if target < dates[0]:
                return None
        base = at(target)
        return (last_p / base - 1) if base else None

    w52 = [(d, float(p)) for d, p in rows if d >= last_d - datetime.timedelta(days=365)]
    hi_d, hi_p = max(w52, key=lambda x: x[1])
    lo_d, lo_p = min(w52, key=lambda x: x[1])
    return {"last_date": str(last_d), "r1m": ret(30), "r3m": ret(91), "r6m": ret(182),
            "rytd": ret(ytd=True), "r1y": ret(365), "r3y": ret(years=3),
            "hi52": hi_p, "hi52_d": str(hi_d), "lo52": lo_p, "lo52_d": str(lo_d)}


def build_indicators(cur, company_id: int, ticker: str, sector: Optional[str],
                     is_holding: bool, shares: Optional[float],
                     mcap: Optional[float], primary_class_id: Optional[int],
                     illiquid: bool = False) -> dict:
    ix = Ind(cur, company_id, sector, is_holding)
    fin = ix.fin
    rev_item = "total_operating_income" if sector == "bank" else "revenue"

    groups = []

    # 1) IZVEDBA DIONICE ------------------------------------------------
    r = _returns(cur, primary_class_id) if primary_class_id else None
    g = []
    if r:
        pb = f"EOD do {r['last_date']}" + (" · ilikvidna (indikativno)" if illiquid else "")
        for key, lab in (("r1m", "Povrat 1M"), ("r3m", "Povrat 3M"), ("r6m", "Povrat 6M"),
                         ("rytd", "Povrat YTD"), ("r1y", "Povrat 1G"), ("r3y", "Povrat 3G")):
            v = r[key]
            g.append(_i(lab, v, "%", pb if v is not None else None,
                        "close_zadnji / close_najbliži_ciljnom_danu − 1",
                        None if v is not None or key != "r3y" else None)
                     if v is not None else
                     _np(lab, "serija cijena prekratka" if key == "r3y" else "nema podataka"))
        g.append(_i("52-tj maks", r["hi52"], "eur", r["hi52_d"], "max close 365 d"))
        g.append(_i("52-tj min", r["lo52"], "eur", r["lo52_d"], "min close 365 d"))
    groups.append({"key": "izvedba", "title": "Izvedba dionice", "items": g})

    # 2) VALUACIJA ------------------------------------------------------
    rev, rev_b = ix.flow(rev_item)
    ni, ni_b = ix.flow("net_income_parent")
    ebitda, ebitda_b = ix.flow("ebitda")
    ebit, ebit_b = ix.flow("ebit")
    ocf, ocf_b = ix.flow("operating_cf")
    fcf, fcf_b = ix.flow("free_cash_flow")
    if fcf is None:
        capex_v, cb = ix.flow("capex")
        if ocf is not None and capex_v is not None:
            fcf, fcf_b = ocf - capex_v, ocf_b
    eq, eq_b = ix.bal("equity_parent")
    if eq is None:
        eq, eq_b = ix.bal("total_equity")
    td, _tb = ix.bal("total_debt")
    if td is None:
        dl0, _ = ix.bal("debt_long"); ds0, _ = ix.bal("debt_short")
        td = (dl0 or 0) + (ds0 or 0) if (dl0 is not None or ds0 is not None) else None
    cash, _cb = ix.bal("cash_and_equivalents")
    stfa, _ = ix.bal("short_term_fin_assets")
    mi, _ = ix.bal("minority_interests")
    ev = (mcap + (td or 0) - (cash or 0) - (stfa or 0) + (mi or 0)) \
        if (mcap is not None and td is not None and cash is not None) else None
    ev_b = "trž.kap + dug − novac − kratk. fin. imovina + manjinski (zadnja bilanca)"
    g = [_i("Tržišna kap.", mcap, "meur", "zadnji EOD × dionice ex-trezor",
            "Σ close klase × dionice klase")]
    if fin:
        g += [_np("EV", "financijska firma — dug je posao, ne struktura"),
              _np("EV/Prihod", "n/p za banke/osiguranje"),
              _np("EV/EBITDA", "n/p za banke/osiguranje"),
              _np("EV/EBIT", "n/p za banke/osiguranje")]
    else:
        g.append(_i("EV", ev, "meur", ev_b,
                    "EV = trž. kap. + dug − novac − kratkoročna fin. imovina "
                    "+ manjinski udjeli"))
        for lab, num_v, num_b in (("EV/Prihod", rev, rev_b), ("EV/EBITDA", ebitda, ebitda_b),
                                  ("EV/EBIT", ebit, ebit_b)):
            g.append(_i(lab, (ev / num_v) if (ev and num_v and num_v > 0) else None,
                        "x", num_b, f"EV / {lab.split('/')[1]}")
                     if ev and num_v and num_v > 0 else _np(lab, "nema ulaza"))
    for lab, num_v, num_b, f in (("P/E", ni, ni_b, "trž.kap / neto dobit matici"),
                                 ("P/S", rev, rev_b, "trž.kap / prihod"),
                                 ("P/CF", ocf, ocf_b, "trž.kap / operativni CF"),
                                 ("P/FCF", fcf, fcf_b, "trž.kap / slobodni novčani tok")):
        if fin and lab in ("P/S",):
            g.append(_np(lab, "banka: prihod = operativni prihod (vidi P/TOI)"))
            continue
        g.append(_i(lab, (mcap / num_v) if (mcap and num_v and num_v > 0) else None,
                    "x", num_b, f) if mcap and num_v and num_v > 0 else _np(lab, "nema ulaza"))
    g.append(_i("EPS", (ni / shares) if (ni is not None and shares) else None,
                "eur", ni_b, "neto dobit matici / dionice ex-trezor")
             if ni is not None and shares else _np("EPS", "nema ulaza"))
    g.append(_i("Earnings yield", (ni / mcap) if (mcap and ni and ni > 0) else None,
                "%", ni_b, "neto dobit / trž.kap") if mcap and ni and ni > 0
             else _np("Earnings yield", "nema ulaza"))
    g.append(_i("P/B", (mcap / eq) if (mcap and eq and eq > 0) else None, "x", eq_b,
                "trž.kap / knjiga (matici)") if mcap and eq and eq > 0
             else _np("P/B", "nema ulaza"))
    g.append(_i("BVPS", (eq / shares) if (eq and eq > 0 and shares) else None,
                "eur", eq_b, "knjiga (matici) / dionice ex-trezor")
             if eq and eq > 0 and shares else _np("BVPS", "nema ulaza"))
    groups.append({"key": "valuacija", "title": "Valuacija", "items": g})

    # 3) RAST -----------------------------------------------------------
    g = []
    yq, yq_b = ix.yoy_last_quarter(rev_item)
    g.append(_i("Prihod YoY (kvartal)", yq, "%", yq_b,
                "diskretni kvartal vs isti lanjski (Q2=H1−Q1...)")
             if yq is not None else _np("Prihod YoY (kvartal)",
                                        "kvartali još nisu u bazi za usporedbu"))
    eq_yoy, eq_yb = ix.yoy_last_quarter("net_income_parent")
    g.append(_i("EPS YoY (kvartal)", eq_yoy, "%", eq_yb,
                "neto dobit matici po kvartalu / dionice — isti-na-isti")
             if eq_yoy is not None else _np("EPS YoY (kvartal)", "kvartali nedostupni"))
    g.append(_i("Prihod (TTM/FY)", rev, "meur", rev_b, "kumulativna derivacija")
             if rev is not None else _np("Prihod", "nema u bazi"))
    g.append(_i("EBITDA (TTM/FY)", ebitda, "meur", ebitda_b, "EBIT + amortizacija")
             if ebitda is not None else
             _np("EBITDA", "financijska firma" if fin else "nema u bazi"))
    groups.append({"key": "rast", "title": "Rast", "items": g})

    # 4) PROFITABILNOST ---------------------------------------------------
    ta, ta_b = ix.bal("total_assets")
    g = []
    for lab, num_v, num_b in (("EBITDA marža", ebitda, ebitda_b),
                              ("EBIT marža", ebit, ebit_b),
                              ("Neto marža", ni, ni_b)):
        if fin and lab != "Neto marža":
            g.append(_np(lab, "n/p za banke/osiguranje")); continue
        g.append(_i(lab, (num_v / rev) if (rev and num_v is not None and rev > 0) else None,
                    "%", num_b, f"{lab.split()[0]} / prihod")
                 if rev and num_v is not None else _np(lab, "nema ulaza"))
    g.append(_i("ROE", (ni / eq) if (ni is not None and eq and eq > 0) else None, "%",
                f"{ni_b or ''} / {eq_b or ''}", "neto dobit matici / knjiga matici")
             if ni is not None and eq and eq > 0 else _np("ROE", "nema ulaza"))
    g.append(_i("ROA", (ni / ta) if (ni is not None and ta and ta > 0) else None, "%",
                ta_b, "neto dobit / ukupna imovina")
             if ni is not None and ta and ta > 0 else _np("ROA", "nema ulaza"))
    groups.append({"key": "profit", "title": "Profitabilnost", "items": g})

    # 5) BILANCA (zadnje stanje) -----------------------------------------
    ca, ca_b = ix.bal("current_assets")
    cl, cl_b = ix.bal("current_liabilities")
    dl, dl_b = ix.bal("debt_long")
    ds, ds_b = ix.bal("debt_short")
    bvps = (eq / shares) if (eq and shares) else None
    g = [_i("Ukupna imovina", ta, "meur", ta_b, "bilanca"),
         _i("Novac", cash, "meur", _cb, "novac i ekvivalenti"),
         _i("BVPS", bvps, "eur", eq_b, "knjiga matici / dionice ex-trezor"),
         _i("Ukupne obveze", (ta - (ix.bal('total_equity')[0] or 0))
            if ta is not None and ix.bal('total_equity')[0] is not None else None,
            "meur", ta_b, "imovina − kapital (izvedeno)"),
         _i("Kratkoročni dug", ds, "meur", ds_b, "kamatonosni"),
         _i("Dugoročni dug", dl, "meur", dl_b, "kamatonosni"),
         _i("Kapital (ukupni)", ix.bal("total_equity")[0], "meur",
            ix.bal("total_equity")[1], "bilanca")]
    groups.append({"key": "bilanca", "title": "Bilanca", "items": g})

    # 6) NOVČANI TOK ------------------------------------------------------
    capex, capex_b = ix.flow("capex")
    icf, icf_b = ix.flow("investing_cf")
    fcf2, fcf2_b = ix.flow("financing_cf")
    g = [_i("Operativni CF", ocf, "meur", ocf_b, "NT izvještaj"),
         _i("Capex", capex, "meur", capex_b, "izdaci za dugotrajnu imovinu"),
         _i("FCF", fcf, "meur", fcf_b, "OCF − capex"),
         _i("Investicijski CF", icf, "meur", icf_b, "NT B)") if icf is not None
         else _np("Investicijski CF", "nema u bazi"),
         _i("Financijski CF", fcf2, "meur", fcf2_b, "NT C)") if fcf2 is not None
         else _np("Financijski CF", "nema u bazi")]
    groups.append({"key": "cf", "title": "Novčani tok", "items": g})

    # 7) LIKVIDNOST I SOLVENTNOST ----------------------------------------
    g = []
    if fin:
        g += [_np(x, "n/p za banke/osiguranje — struktura bilance je posao")
              for x in ("Tekući omjer", "Neto dug/EBITDA", "Pokriće kamata", "Altman Z'")]
        g.append(_i("Dug/kapital", (td / eq) if (td is not None and eq) else None, "x",
                    eq_b, "kamatonosni dug / knjiga") if td is not None and eq
                 else _np("Dug/kapital", "nema ulaza"))
    else:
        g.append(_i("Tekući omjer", (ca / cl) if (ca and cl) else None, "x", ca_b,
                    "kratkotrajna imovina / kratkoročne obveze")
                 if ca and cl else _np("Tekući omjer", "stavke još nisu u bazi"))
        g.append(_i("Dug/kapital", (td / eq) if (td is not None and eq) else None, "x",
                    eq_b, "kamatonosni dug / knjiga") if td is not None and eq
                 else _np("Dug/kapital", "nema ulaza"))
        nd = (td - (cash or 0)) if td is not None and cash is not None else None
        g.append(_i("Neto dug/EBITDA", (nd / ebitda) if (nd is not None and ebitda and ebitda > 0)
                    else None, "x", ebitda_b, "(dug − novac) / EBITDA")
                 if nd is not None and ebitda and ebitda > 0
                 else _np("Neto dug/EBITDA", "nema ulaza"))
        ie, ie_b = ix.flow("interest_expense")
        g.append(_i("Pokriće kamata", (ebit / ie) if (ebit and ie and ie > 0) else None,
                    "x", ie_b, "EBIT / rashodi od kamata")
                 if ebit and ie and ie > 0 else _np("Pokriće kamata", "trošak kamata nije u bazi"))
        re_, _rb = ix.bal("retained_earnings")
        tl = (ta - (ix.bal('total_equity')[0] or 0)) \
            if ta is not None and ix.bal('total_equity')[0] is not None else None
        if None not in (ca, cl, re_, ebit, eq, tl, rev, ta) and ta and tl:
            z = (0.717 * (ca - cl) / ta + 0.847 * re_ / ta + 3.107 * ebit / ta
                 + 0.420 * eq / tl + 0.998 * rev / ta)
            g.append(_i("Altman Z'", z, "x", f"{ta_b} + {ebit_b}",
                        "Z' (privatna varijanta): 0,717·WC/TA + 0,847·RE/TA + "
                        "3,107·EBIT/TA + 0,420·BVE/TL + 0,998·S/TA"))
        else:
            g.append(_np("Altman Z'", "nedostaju ulazi (WC/RE/EBIT/knjiga)"))
    groups.append({"key": "solvent", "title": "Likvidnost i solventnost", "items": g})

    # 8) UČINKOVITOST -----------------------------------------------------
    g = []
    if fin or is_holding:
        why = "n/p za financijske firme" if fin else "n/p za holding (nema robni ciklus)"
        g += [_np(x, why) for x in ("Obrtaj imovine", "DSO", "DIO", "DPO", "Novčani jaz")]
    else:
        g.append(_i("Obrtaj imovine", (rev / ta) if (rev and ta) else None, "x",
                    rev_b, "prihod / imovina") if rev and ta
                 else _np("Obrtaj imovine", "nema ulaza"))
        tr, _ = ix.bal("trade_receivables")
        inv, _ = ix.bal("inventories")
        tp, _ = ix.bal("trade_payables")
        mc, mc_b = ix.flow("material_costs")
        dso = (tr / rev * 365) if (tr and rev) else None
        dio = (inv / mc * 365) if (inv and mc) else None
        dpo = (tp / mc * 365) if (tp and mc) else None
        g.append(_i("DSO", dso, "days", rev_b, "kupci / prihod × 365") if dso
                 else _np("DSO", "stavke još nisu u bazi"))
        g.append(_i("DIO", dio, "days", mc_b, "zalihe / materijalni troškovi × 365 (COGS proxy)")
                 if dio else _np("DIO", "stavke još nisu u bazi"))
        g.append(_i("DPO", dpo, "days", mc_b, "dobavljači / materijalni troškovi × 365")
                 if dpo else _np("DPO", "stavke još nisu u bazi"))
        g.append(_i("Novčani jaz", (dso + dio - dpo) if None not in (dso, dio, dpo) else None,
                    "days", rev_b, "DSO + DIO − DPO")
                 if None not in (dso, dio, dpo) else _np("Novčani jaz", "nedostaju DSO/DIO/DPO"))
    groups.append({"key": "efik", "title": "Učinkovitost", "items": g})

    # 9) DIVIDENDE --------------------------------------------------------
    cur.execute("""SELECT amount_eur, ex_date, payment_date FROM dividends
                   WHERE company_id=%s ORDER BY COALESCE(ex_date, payment_date) DESC
                   LIMIT 1""", (company_id,))
    dv = cur.fetchone()
    cur.execute("""SELECT amount_eur, ex_date FROM dividends
                   WHERE company_id=%s AND ex_date > CURRENT_DATE
                   ORDER BY ex_date LIMIT 1""", (company_id,))
    nxt = cur.fetchone()
    g = []
    if dv:
        dps = float(dv[0])
        price = (mcap / shares) if (mcap and shares) else None
        g.append(_i("DPS (zadnja)", dps, "eur", str(dv[1] or dv[2] or ""), "dividends tablica"))
        g.append(_i("Dividendni prinos", (dps / price) if price else None, "%",
                    "zadnja isplata / zadnja cijena", "DPS / cijena")
                 if price else _np("Dividendni prinos", "nema cijene"))
        g.append(_i("Payout", (dps * shares / ni) if (ni and ni > 0 and shares) else None,
                    "%", ni_b, "DPS × dionice / neto dobit")
                 if ni and ni > 0 and shares else _np("Payout", "nema dobiti/dionica"))
        g.append(_i("Zadnja isplata", None, "date", str(dv[2] or ""), "dividends tablica",
                    note=str(dv[2] or "n/p")))
    else:
        g.append(_np("Dividenda", "nema zapisa u bazi"))
    g.append(_i("Sljedeći ex-datum", None, "date", str(nxt[1]) if nxt else None,
                "dividends tablica", note=str(nxt[1]) if nxt else "n/p")
             if nxt else _np("Sljedeći ex-datum", "nema najave"))
    groups.append({"key": "div", "title": "Dividende", "items": g})

    # 10) PO ZAPOSLENOM ----------------------------------------------------
    emp, emp_b = ix.bal("employees")
    g = []
    if emp:
        g.append(_i("Broj zaposlenih", emp, "count", emp_b, "TFI Opći podaci"))
        g.append(_i("Prihod/zaposlenom", (rev / emp) if rev else None, "eur", rev_b,
                    "prihod / broj zaposlenih") if rev else _np("Prihod/zaposlenom", "nema prihoda"))
        g.append(_i("Dobit/zaposlenom", (ni / emp) if ni is not None else None, "eur",
                    ni_b, "neto dobit matici / broj zaposlenih")
                 if ni is not None else _np("Dobit/zaposlenom", "nema dobiti"))
    else:
        g.append(_np("Po zaposlenom", "broj zaposlenih još nije u bazi za ovu firmu"))
    groups.append({"key": "emp", "title": "Po zaposlenom", "items": g})

    return {"groups": groups, "review_flags": ix.flags,
            "note": ("TTM = zadnji FY + tekući YTD − lanjski isti YTD (samo tokovne "
                     "stavke); bilanca = zadnje objavljeno stanje; FY se nikad ne "
                     "prikazuje kao TTM. Formule su opisane u Metodologiji.")}
