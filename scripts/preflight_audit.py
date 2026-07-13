"""Pre-flight audit SVIH dionica — dijagnoza PRIJE trošenja API kredita.

Čisti kod nad bazom + javni zse.hr scrape (tečajnica, listing "Uvrštena
količina"). NE pokreće ekstrakciju i NE zove Anthropic API. Izlaz je tablica
po firmi (stdout + docs/preflight_audit.md): status + KONKRETAN razlog —
odluka što ekstrahirati ostaje urednička.

Provjere po firmi:
  1. sanity vs tržište   — fer-zona vs zadnja cijena; |odstupanje| > 40% se
                           označava; >70% firmi na istoj strani = sistemska
                           pristranost modela (glavni alarm na dnu).
  2. klasifikacija       — firma je roditelj u holdings grafu (materijalan
                           udjel >= MATERIAL_PCT) a arhetip joj NIJE holding
                           -> treba SOTP, krivo rutirana (KOEI-test).
  3. kompletnost ulaza   — 3g prihoda (signal rasta), broj dionica
                           (ex-trezor), peer skup, bilančne stavke; popis
                           TOČNO onoga što fali.
  4. konzistentnost      — računovodstveni identiteti zatvaraju (NI = matica
                           + manjine; EBITDA = EBIT + D&A; dug = kratki +
                           dugi; neto dug = dug - novac), per-share ima
                           nazivnik, sidrena zona < 20%, bez placeholder
                           pretpostavki u živim metodama.
  5. scrape (bez API)    — ISIN i broj dionica sa zse.hr (tečajnica +
                           "Uvrštena količina"), tržišne kap. uvrštenih
                           kćeri za SOTP.

Pokretanje:  python -m scripts.preflight_audit [--no-scrape] [--md PUTANJA]
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import urllib.request

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402
from src.params_calibrated import build_params  # noqa: E402
from src.valuation_methods import (  # noqa: E402
    ARCHETYPE_OF, MATERIAL_PCT, build_ctx, value_company,
)

EXTREME_GAP = 0.40        # |cijena vs sredina zone| iznad ovoga = ekstrem
SYSTEMIC_SHARE = 0.70     # udio firmi na istoj strani zone = sistemski alarm
ZONE_WIDTH_MAX = 0.20     # cilj M12: raspon sidra < ~20%
SHARES_TOL = 0.005        # dopušteno odstupanje broja dionica DB vs ZSE

ZSE_PRICE_LIST = "https://rest.zse.hr/web/Bvt9fe2peQ7pwpyYqODM/price-list/XZAG/{d}/json"


# ---------------------------------------------------------------- scrape
def fetch_price_list() -> dict:
    """Zadnja objavljena tečajnica: symbol -> {isin, close, date}. Bez API."""
    today = datetime.date.today()
    for back in range(0, 10):
        d = (today - datetime.timedelta(days=back)).isoformat()
        req = urllib.request.Request(ZSE_PRICE_LIST.format(d=d),
                                     headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
        except Exception:
            continue
        rows = data.get("securities") or []
        if rows:
            return {s["symbol"]: {
                "isin": s.get("isin"),
                "close": float(s["close_price"]) if s.get("close_price") else None,
                "date": s.get("trade_date") or d,
            } for s in rows}
    return {}


def fetch_listed_qty(isin: str):
    """'Uvrštena količina' sa zse.hr stranice papira; None ako nedostupno."""
    try:
        from src.onboard import fetch_listed_quantity
        return fetch_listed_quantity(isin)
    except Exception:
        return None


# ---------------------------------------------------------------- helpers
def _fy(cur, cid: int, item: str):
    """Zadnja FY konsolidirana vrijednost stavke ili None."""
    cur.execute(
        """SELECT fin.value_eur FROM financials fin JOIN filings f ON f.id=fin.filing_id
           WHERE f.company_id=%s AND fin.item=%s AND f.period_type='annual'
                 AND f.basis='consolidated' AND fin.value_eur IS NOT NULL
           ORDER BY f.fiscal_year DESC LIMIT 1""", (cid, item))
    r = cur.fetchone()
    return float(r[0]) if r else None


def _fy_years(cur, cid: int, item: str) -> list[int]:
    cur.execute(
        """SELECT DISTINCT f.fiscal_year FROM financials fin
           JOIN filings f ON f.id=fin.filing_id
           WHERE f.company_id=%s AND fin.item=%s AND f.period_type='annual'
                 AND f.basis='consolidated' AND fin.value_eur IS NOT NULL
           ORDER BY 1 DESC""", (cid, item))
    return [r[0] for r in cur.fetchall()]


def _identity(label: str, lhs, rhs, tol: float):
    """Provjera identiteta: None ako ulaza nema, poruka ako NE zatvara."""
    if lhs is None or rhs is None:
        return None
    denom = max(abs(lhs), abs(rhs), 1.0)
    if abs(lhs - rhs) / denom > tol:
        return f"{label}: {lhs:,.0f} vs {rhs:,.0f} (Δ {abs(lhs - rhs) / denom:.1%})"
    return ""


def audit_company(conn, cur, comp: dict, plist: dict, scrape: bool) -> dict:
    cid, ticker = comp["id"], comp["ticker"]
    tags, why = [], []          # kratki statusi + konkretni razlozi

    # --- klase, cijena, dionice iz DB
    cur.execute("""SELECT ticker, isin, shares_issued, treasury_shares
                   FROM share_classes WHERE company_id=%s ORDER BY is_primary_line DESC""",
                (cid,))
    classes = [{"ticker": r[0], "isin": r[1],
                "shares": float(r[2]) if r[2] is not None else None,
                "treasury": float(r[3]) if r[3] is not None else 0.0}
               for r in cur.fetchall()]

    # --- 2. klasifikacija: roditelj u holdings grafu, a arhetip nije holding
    cur.execute("""SELECT COUNT(*) FROM holdings
                   WHERE parent_company_id=%s AND ownership_pct >= %s""",
                (cid, MATERIAL_PCT))
    n_material = cur.fetchone()[0]
    arche = ARCHETYPE_OF.get(comp["sector"] or "", "operating")
    if n_material and arche != "holding":
        tags.append("TREBA SOTP")
        why.append(f"roditelj {n_material} materijalnih udjela u holdings grafu, "
                   f"a arhetip je '{arche}' (sektor {comp['sector']}) — krivo rutirana")

    # --- 3. kompletnost ulaza (radi i za ne-live firme: što IMA u bazi)
    rev_item = "total_operating_income" if comp["sector"] == "bank" else "revenue"
    years = _fy_years(cur, cid, rev_item)
    missing = []
    if len(years) < 3:
        missing.append(f"3g prihoda (ima {len(years)}: "
                       f"{','.join(map(str, years)) or 'ništa'}) -> rast se ne izvodi")
    cur.execute("SELECT shares_ex_treasury FROM v_shares_canonical WHERE company_id=%s", (cid,))
    r = cur.fetchone()
    shares_db = float(r[0]) if r and r[0] else None
    if not shares_db:
        so = _fy(cur, cid, "shares_outstanding")
        if so:
            shares_db = so
        else:
            missing.append("broj dionica (ni share_classes ni shares_outstanding)")
            tags.append("FALI BROJ DIONICA")
    for it, lbl in [("total_assets", "ukupna imovina"), ("total_equity", "kapital"),
                    ("net_income", "neto dobit")]:
        if _fy(cur, cid, it) is None:
            missing.append(f"bilanca/RDG: {lbl}")

    # --- 4a. računovodstveni identiteti (zatvaraju li)
    ident_fails = []
    ni, nip, nim = (_fy(cur, cid, "net_income"), _fy(cur, cid, "net_income_parent"),
                    _fy(cur, cid, "net_income_minority"))
    if nip is not None and nim is not None:
        m = _identity("NI ≠ matica+manjine", ni, nip + nim, 0.02)
        if m:
            ident_fails.append(m)
    m = _identity("EBITDA ≠ EBIT+D&A", _fy(cur, cid, "ebitda"),
                  (lambda e, d: e + d if e is not None and d is not None else None)(
                      _fy(cur, cid, "ebit"), _fy(cur, cid, "depreciation_amortization")),
                  0.05)
    if m:
        ident_fails.append(m)
    dl, ds, td = (_fy(cur, cid, "debt_long"), _fy(cur, cid, "debt_short"),
                  _fy(cur, cid, "total_debt"))
    if dl is not None and ds is not None:
        m = _identity("dug ≠ dugi+kratki", td, dl + ds, 0.02)
        if m:
            ident_fails.append(m)
    nd, cash = _fy(cur, cid, "net_debt"), _fy(cur, cid, "cash_and_equivalents")
    if td is not None and cash is not None and nd is not None:
        m = _identity("neto dug ≠ dug−novac", nd, td - cash, 0.05)
        if m:
            ident_fails.append(m)
    if ident_fails:
        tags.append("NE ZATVARA")
        why.extend(ident_fails)

    # --- valuacija (čisti kod nad bazom; bez API) — i za needs_review radi
    #     dijagnoze, ali status jasno kaže da firma NIJE live
    zone, vs_mkt, zone_w = None, None, None
    val_issues = []
    try:
        params = build_params(ticker)
        ctx = build_ctx(conn, ticker, params=params)
        res = value_company(ctx)
        rec = res["reconciliation"]
        if rec.get("status") != "no_value" and rec.get("zone_low") is not None:
            zone = (rec["zone_low"], rec["zone_high"])
            mid = (zone[0] + zone[1]) / 2
            zone_w = (zone[1] - zone[0]) / mid if mid else None
            vs_mkt = rec.get("vs_market_pct")
            if zone_w is not None and zone_w > ZONE_WIDTH_MAX:
                val_issues.append(f"raspon sidra {zone_w:.0%} > {ZONE_WIDTH_MAX:.0%} "
                                  "(osjetljivost na r — nije min-max)")
            for s in rec.get("anchor_inconsistency") or []:
                val_issues.append(f"nekonzistentno sidro: {s}")
            # placeholder pretpostavke u ŽIVIM metodama
            uses_peers = any(k in res["ran"] for k in ("multiples_relative", "ev_ebitda"))
            if uses_peers and not getattr(params, "peers_calibrated", False):
                val_issues.append("placeholder peer multipli (P/E 12, P/B 1,5) u živoj metodi")
            if not getattr(params, "beta_calibrated", False):
                val_issues.append("beta=1,0 pretpostavka (nije izmjerena iz serije)")
            if not ctx.growth_hint:
                tags.append("FALI RAST")
            if ctx.shares_ex_treasury is None:
                val_issues.append("per-share metode bez nazivnika (shares_ex_treasury=None)")
    except Exception as e:  # noqa: BLE001 — dijagnostika ne smije pasti na 1 firmi
        val_issues.append(f"valuacija pala: {type(e).__name__}: {e}")

    # --- 1. sanity vs tržište
    if vs_mkt is not None and abs(vs_mkt) > EXTREME_GAP * 100:
        tags.append("ODSTUPA OD TRŽIŠTA")
        why.append(f"cijena {vs_mkt:+.0f}% vs sredina fer-zone (prag ±{EXTREME_GAP:.0%})")
    if val_issues:
        why.extend(val_issues)
    if missing:
        why.extend(missing)
        if any("3g prihoda" in m for m in missing) and "FALI RAST" not in tags:
            tags.append("FALI RAST")

    # --- 5. scrape: ISIN + broj dionica sa ZSE, trž.kap. kćeri
    if scrape:
        for c in classes:
            pl = plist.get(c["ticker"])
            if pl and c["isin"] and pl["isin"] and pl["isin"] != c["isin"]:
                tags.append("ISIN MISMATCH")
                why.append(f"{c['ticker']}: ISIN u bazi {c['isin']} ≠ ZSE {pl['isin']}")
            qty = fetch_listed_qty(c["isin"]) if c["isin"] else None
            if qty:
                if c["shares"] is None:
                    why.append(f"{c['ticker']}: broj dionica FALI u bazi, a ZSE listing "
                               f"ga ima BESPLATNO: {qty:,.0f} ('Uvrštena količina')")
                elif abs(qty - c["shares"]) / qty > SHARES_TOL:
                    tags.append("DIONICE MISMATCH")
                    why.append(f"{c['ticker']}: dionice u bazi {c['shares']:,.0f} ≠ "
                               f"ZSE listing {qty:,.0f}")
        # trž.kap. uvrštenih kćeri (ulaz u SOTP)
        cur.execute("""SELECT h.held_name, h.held_company_id, c2.ticker
                       FROM holdings h LEFT JOIN companies c2 ON c2.id=h.held_company_id
                       WHERE h.parent_company_id=%s AND h.listed
                             AND h.ownership_pct >= %s""", (cid, MATERIAL_PCT))
        for held_name, held_id, held_tick in cur.fetchall():
            if not held_id:
                why.append(f"SOTP kći '{held_name}' uvrštena, ali NIJE povezana "
                           "na companies (held_company_id NULL) -> trž.kap. n/p")
                continue
            cur.execute("""SELECT COUNT(*) FROM share_classes sc
                           WHERE sc.company_id=%s AND sc.shares_issued IS NOT NULL""",
                        (held_id,))
            has_sh = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM prices_eod WHERE company_id=%s", (held_id,))
            has_px = cur.fetchone()[0]
            if not has_sh or not has_px:
                why.append(f"SOTP kći {held_tick or held_name}: trž.kap. nepotpuna "
                           f"(dionice: {'da' if has_sh else 'NE'}, "
                           f"cijene: {'da' if has_px else 'NE'})")

    # --- status
    if not comp["is_live"]:
        tags.insert(0, f"NEEDS EXTRACTION ({comp['onboarding_status']})")
    if not tags and any("nekonzistentno sidro" in w for w in why):
        tags.append("NEKONZISTENTNO")
    status = (" · ".join(dict.fromkeys(tags)) if tags
              else ("OK (uz ograde)" if why else "OK"))
    return {"ticker": ticker, "name": comp["name"], "sector": comp["sector"],
            "live": comp["is_live"], "status": status,
            "zone": zone, "zone_width": zone_w, "vs_market_pct": vs_mkt,
            "why": list(dict.fromkeys(why))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Pre-flight audit (bez API)")
    ap.add_argument("--no-scrape", action="store_true",
                    help="preskoči zse.hr scrape (samo baza)")
    ap.add_argument("--md", default="docs/preflight_audit.md")
    a = ap.parse_args(argv)

    plist = {} if a.no_scrape else fetch_price_list()
    rows = []
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""SELECT id, ticker, name, sector, is_live, onboarding_status
                       FROM companies ORDER BY ticker""")
        comps = [dict(zip(["id", "ticker", "name", "sector", "is_live",
                           "onboarding_status"], r)) for r in cur.fetchall()]
        for comp in comps:
            rows.append(audit_company(conn, cur, comp, plist, not a.no_scrape))
            print(f"[audit] {comp['ticker']}: {rows[-1]['status']}", file=sys.stderr)

    # sistemska pristranost: firme S valuacijom, na kojoj su strani zone
    valued = [r for r in rows if r["vs_market_pct"] is not None]
    above = [r for r in rows if r["vs_market_pct"] is not None and r["vs_market_pct"] > 0]
    below = [r for r in rows if r["vs_market_pct"] is not None and r["vs_market_pct"] < 0]
    systemic = None
    if valued:
        sh_above, sh_below = len(above) / len(valued), len(below) / len(valued)
        if sh_above >= SYSTEMIC_SHARE:
            systemic = (f"ALARM: {sh_above:.0%} firmi trguje IZNAD fer-zone "
                        f"(model sustavno PODcjenjuje) — prag {SYSTEMIC_SHARE:.0%}")
        elif sh_below >= SYSTEMIC_SHARE:
            systemic = (f"ALARM: {sh_below:.0%} firmi trguje ISPOD fer-zone "
                        f"(model sustavno PREcjenjuje) — prag {SYSTEMIC_SHARE:.0%}")

    # markdown izvještaj
    today = datetime.date.today().isoformat()
    L = [f"# Pre-flight audit — {today}", "",
         "Dijagnoza bez API poziva: baza + javni zse.hr scrape. Odluka o",
         "ekstrakciji je urednička; ovo je popis nalaza, ne plan.", "",
         "| Ticker | Status | Fer-zona € | Cijena vs zona | Nalazi |",
         "|---|---|---|---|---|"]
    for r in rows:
        zone = (f"{r['zone'][0]:,.2f}–{r['zone'][1]:,.2f}"
                + (f" ({r['zone_width']:.0%})" if r["zone_width"] else "")
                ) if r["zone"] else "n/p"
        vs = f"{r['vs_market_pct']:+.0f}%" if r["vs_market_pct"] is not None else "n/p"
        why = "<br>".join(r["why"]) if r["why"] else "—"
        L.append(f"| **{r['ticker']}** | {r['status']} | {zone} | {vs} | {why} |")
    L += ["", f"## Sistemska pristranost",
          f"- firmi s valuacijom: {len(valued)}; iznad zone: {len(above)}, "
          f"ispod: {len(below)}",
          f"- {systemic or 'nema alarma (nijedna strana ne prelazi ' + format(SYSTEMIC_SHARE, '.0%') + ')'}"]
    if not a.no_scrape and not plist:
        L.append("- NAPOMENA: tečajnica nedostupna u ovom prolazu (mrežna greška) "
                 "— ISIN cross-check preskočen")
    md = "\n".join(L) + "\n"
    if a.md:
        import os
        os.makedirs(os.path.dirname(a.md), exist_ok=True)
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"[audit] zapisano {a.md}", file=sys.stderr)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
