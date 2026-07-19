"""v3 FAZA DIV: klasifikacija isplata + očekivana ODRŽIVA dividenda (D_sust).

Pravila (metodologija v3):
  KLASIFIKACIJA isplate (payout_type na dividends retku; prijedlozi se ne
  klasificiraju):
    - 'iz_zadrzane_dobiti' ako je payout ratio godine > 100% dobiti
      pripadne fiskalne godine (crpi zadržanu dobit — HPB slučaj);
    - 'jednokratna' ako je per-share iznos > 150% medijana PRETHODNIH
      redovnih isplata iste klase, ili EHO naslov sadrži
      izvanredna/jednokratna/zadržane dobiti (formulacija objave ima
      prednost pred heuristikom);
    - inače 'redovna'.
  payout_ratio se veže na company+fiscal_year: Σ(iznos × dionice klase bez
  trezorskih) / net_income_parent TE ISTE fiskalne godine — ako dobit te
  godine nije u bazi ili je ≤ 0, ratio je NULL s razlogom (NIKAD kriva
  godina, NIKAD kriva brojka).

  D_SUST (po dionici) = održivi payout × normalizirana dobit (NI TTM iz
  faze G) / dionice bez trezorskih.
    - održivi payout: objavljena politika (dividend_policies) ako postoji
      I pokrivenost ≥ 1,0; inače MEDIJAN povijesnih payout ratija
      računanih SAMO nad redovnim isplatama;
    - banke: payout > 80% → flag "ovisi o regulatornom odobrenju", a za
      bazu min(stvarni, 70%);
    - pokrivenost najave = NI_TTM / najavljena (izglasana) isplata;
      < 1,2 → "napeto pokrivena"; < 1,0 → najava se NE koristi.

  dividend_policies: mehanizam za RUČNU ekstrakciju politika iz godišnjih
  izvješća/statuta/objava (ista praksa kao profili poslovanja — u sesiji,
  bez API-ja). Bez izvora u repou/bazi tablica ostaje prazna — fallback je
  medijan, ništa se ne izmišlja.
"""
from __future__ import annotations

import json
import re
from statistics import median

ONE_OFF_TITLE_RE = re.compile(r"izvanredn|jednokratn|zadržan[eo]j? dobit", re.I)
ONE_OFF_FACTOR = 1.5
COVERAGE_TIGHT = 1.2
BANK_PAYOUT_FLAG = 0.80
BANK_PAYOUT_BASE = 0.70


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            ALTER TABLE dividends
                ADD COLUMN IF NOT EXISTS payout_type TEXT,
                ADD COLUMN IF NOT EXISTS payout_ratio NUMERIC,
                ADD COLUMN IF NOT EXISTS classified_reason TEXT;
            CREATE TABLE IF NOT EXISTS dividend_policies (
                company_id INT PRIMARY KEY REFERENCES companies(id),
                policy_type TEXT NOT NULL,  -- postotak_dobiti|progresivna|fiksna|nema
                params JSONB NOT NULL DEFAULT '{}'::jsonb,
                source TEXT NOT NULL,       -- dokument + stranica / URL
                extracted_on DATE NOT NULL);
        """)
    conn.commit()


def _ni_annual(cur, company_id: int, fiscal_year: int):
    cur.execute(
        """SELECT fin.value_eur::float FROM financials fin
           JOIN filings f ON f.id = fin.filing_id
           WHERE f.company_id=%s AND fin.item='net_income_parent'
                 AND f.period_type='annual' AND f.basis='consolidated'
                 AND f.fiscal_year=%s""", (company_id, fiscal_year))
    r = cur.fetchone()
    return r[0] if r else None


def classify_company(conn, company_id: int) -> int:
    """Klasificira sve isplate firme; vraća broj klasificiranih redaka."""
    cur = conn.cursor()
    cur.execute(
        """SELECT d.id, d.share_class_id, d.class_ticker, d.fiscal_year,
                  d.amount_eur::float, COALESCE(d.ex_date, d.payment_date),
                  sc.shares_issued - COALESCE(sc.treasury_shares, 0)
           FROM dividends d
           LEFT JOIN share_classes sc ON sc.id = d.share_class_id
           WHERE d.company_id=%s AND d.div_type NOT ILIKE '%%rijedlog%%'
                 AND d.amount_eur IS NOT NULL
           ORDER BY COALESCE(d.ex_date, d.payment_date) NULLS LAST""",
        (company_id,))
    rows = cur.fetchall()
    if not rows:
        return 0
    # EHO naslovi (imaju prednost pred heuristikom)
    cur.execute("SELECT title, published_at FROM announcements WHERE company_id=%s",
                (company_id,))
    one_off_titles = [(t, p) for t, p in cur.fetchall() if t and ONE_OFF_TITLE_RE.search(t)]

    # payout ratio po fiskalnoj godini (Σ svih isplata te godine / NI te godine)
    per_fy: dict = {}
    for _id, scid, ctk, fy, amt, dt, shares in rows:
        # M43: 'cash' isplate iz dnevnog pipelinea nemaju fiscal_year, ali imaju
        # ex/payment datum — isplata u godini N je (konvencija) za dobit godine
        # N-1; izvedi fiskalnu godinu iz datuma da payout ratio bude izračunljiv
        # (prije se cijeli red preskakao pa se D_sust rušio na fallback — PLAG).
        if fy is None and dt is not None:
            fy = dt.year - 1
        if fy is None:
            continue
        per_fy.setdefault(fy, {"total": 0.0, "known": True, "rows": []})
        if shares:
            per_fy[fy]["total"] += amt * float(shares)
        else:
            per_fy[fy]["known"] = False
        per_fy[fy]["rows"].append(_id)
    ratio_fy: dict = {}
    for fy, agg in per_fy.items():
        ni = _ni_annual(cur, company_id, fy)
        if ni is None:
            ratio_fy[fy] = (None, f"dobit FY{fy} nije u bazi")
        elif ni <= 0:
            ratio_fy[fy] = (None, f"dobit FY{fy} ≤ 0 — payout nedefiniran")
        elif not agg["known"]:
            ratio_fy[fy] = (None, "broj dionica klase nepoznat")
        else:
            ratio_fy[fy] = (agg["total"] / ni, None)

    # klasifikacija po retku (povijest medijana po KLASI, samo redovne)
    n = 0
    prior_regular: dict = {}   # class_ticker -> [per-share iznosi redovnih]
    for _id, scid, ctk, fy, amt, dt, shares in rows:
        if fy is None and dt is not None:
            fy = dt.year - 1   # M43: ista izvedba fiskalne godine iz datuma
        ratio, ratio_reason = ratio_fy.get(fy, (None, "bez fiskalne godine"))
        med = (median(prior_regular[ctk]) if prior_regular.get(ctk) else None)
        eho = next((t for t, p in one_off_titles
                    if dt and p and abs((p - dt).days) <= 120), None)
        if eho:
            ptype = ("iz_zadrzane_dobiti" if re.search(r"zadržan", eho, re.I)
                     else "jednokratna")
            reason = f"EHO formulacija: “{eho[:120]}”"
        elif ratio is not None and ratio > 1.0:
            ptype = "iz_zadrzane_dobiti"
            reason = (f"payout {ratio:.0%} > 100% dobiti FY{fy} — isplata "
                      "crpi zadržanu dobit")
        elif med is not None and amt > ONE_OFF_FACTOR * med:
            ptype = "jednokratna"
            reason = (f"{amt:.2f} € > 150% medijana prethodnih redovnih "
                      f"isplata ({med:.2f} €)")
        else:
            ptype = "redovna"
            reason = (f"unutar 150% medijana prethodnih redovnih ({med:.2f} €)"
                      if med is not None else "prva zabilježena isplata klase")
        if ptype == "redovna":
            prior_regular.setdefault(ctk, []).append(amt)
        # M43: perzistiraj izvedenu fiskalnu godinu (iz datuma) kad je stupac
        # bio NULL — d_sust grupira po fiscal_year, pa bez ovoga bi se isplate
        # bez godine (npr. više 'cash' isplata kroz godine) zbrajale u jednu
        cur.execute(
            """UPDATE dividends SET payout_type=%s, payout_ratio=%s,
                      classified_reason=%s,
                      fiscal_year=COALESCE(fiscal_year,%s) WHERE id=%s""",
            (ptype, ratio, reason if ratio_reason is None
             else f"{reason}; payout n/p: {ratio_reason}", fy, _id))
        n += 1
    conn.commit()
    return n


def d_sust(conn, company_id: int, ni_ttm: float | None) -> dict | None:
    """Očekivana održiva dividenda po dionici + PUNI raspis. None ako firma
    nema povijesti isplata ili nema normalizirane dobiti."""
    if not ni_ttm or ni_ttm <= 0:
        return None
    cur = conn.cursor()
    cur.execute("SELECT sector FROM companies WHERE id=%s", (company_id,))
    sector = (cur.fetchone() or [None])[0]
    cur.execute("SELECT shares_ex_treasury FROM v_shares_canonical WHERE company_id=%s",
                (company_id,))
    r = cur.fetchone()
    shares = float(r[0]) if r and r[0] else None
    if not shares:
        return None

    # payout medijan SAMO nad godinama čije su sve isplate redovne
    cur.execute(
        """SELECT fiscal_year,
                  BOOL_AND(payout_type='redovna') AS all_regular,
                  MAX(payout_ratio::float) AS ratio
           FROM dividends
           WHERE company_id=%s AND div_type NOT ILIKE '%%rijedlog%%'
                 AND payout_type IS NOT NULL
           GROUP BY fiscal_year""", (company_id,))
    yrs = cur.fetchall()
    reg_ratios = [x[2] for x in yrs if x[1] and x[2] is not None]
    excluded = [f"FY{x[0]}" for x in yrs if not x[1]]
    if not reg_ratios:
        return None
    payout = median(reg_ratios)
    basis = (f"medijan payout ratija redovnih isplata ({len(reg_ratios)} g.)"
             + (f"; isključene godine s jednokratnim/iz zadržane dobiti: "
                f"{', '.join(sorted(excluded))}" if excluded else ""))

    # objavljena politika ima prednost AKO postoji i AKO je pokrivena
    cur.execute("""SELECT policy_type, params, source FROM dividend_policies
                   WHERE company_id=%s""", (company_id,))
    pol = cur.fetchone()
    policy_note = None
    if pol and pol[0] == "postotak_dobiti":
        p_ratio = float((pol[1] or {}).get("payout", 0)) or None
        if p_ratio:
            payout, basis = p_ratio, f"objavljena politika ({pol[2]})"
            policy_note = pol[2]

    flags = []
    if sector == "bank" and payout > BANK_PAYOUT_FLAG:
        flags.append("isplata ovisi o regulatornom odobrenju (payout > 80%)")
        payout_used = min(payout, BANK_PAYOUT_BASE)
        basis += (f"; banka: za održivu bazu min(stvarni {payout:.0%}, "
                  f"{BANK_PAYOUT_BASE:.0%})")
    else:
        payout_used = payout

    # pokrivenost zadnje NAJAVLJENE (izglasane) isplate normaliziranom dobiti
    cur.execute(
        """SELECT d.amount_eur::float,
                  (sc.shares_issued - COALESCE(sc.treasury_shares,0))::float,
                  d.payout_type
           FROM dividends d JOIN share_classes sc ON sc.id=d.share_class_id
           WHERE d.company_id=%s AND d.div_type NOT ILIKE '%%rijedlog%%'
             AND d.fiscal_year = (SELECT MAX(fiscal_year) FROM dividends
                                  WHERE company_id=%s
                                    AND div_type NOT ILIKE '%%rijedlog%%')""",
        (company_id, company_id))
    last = cur.fetchall()
    announced = sum(a * s for a, s, _ in last if a and s) or None
    # v3 FAZA SOTP (točka 6): pokrivenost najave MATICE uključuje očekivane
    # priljeve dividendi od kćeri — ČINJENIČNO iz njihove povijesti isplata
    # (zadnja izglasana isplata kćeri × naš udio; bez procjena)
    inflows = 0.0
    inflow_notes = []
    cur.execute(
        """SELECT h.held_name, h.ownership_pct::float, h.held_company_id
           FROM holdings h
           WHERE h.parent_company_id=%s AND h.held_company_id IS NOT NULL""",
        (company_id,))
    for held_name, own_pct, held_cid in cur.fetchall():
        cur.execute(
            """SELECT SUM(d.amount_eur *
                          (sc.shares_issued - COALESCE(sc.treasury_shares,0)))::float
               FROM dividends d JOIN share_classes sc ON sc.id=d.share_class_id
               WHERE d.company_id=%s AND d.div_type NOT ILIKE '%%rijedlog%%'
                 AND d.fiscal_year = (SELECT MAX(fiscal_year) FROM dividends
                                      WHERE company_id=%s
                                        AND div_type NOT ILIKE '%%rijedlog%%')""",
            (held_cid, held_cid))
        tot = (cur.fetchone() or [None])[0]
        if tot and own_pct:
            inflows += tot * own_pct
            inflow_notes.append(f"{held_name}: {tot * own_pct:,.0f} €")
    base_for_coverage = ni_ttm + inflows if inflows else ni_ttm
    coverage = (base_for_coverage / announced) if announced else None
    if coverage is not None and coverage < 1.0:
        flags.append("najava nije pokrivena tekućom dobiti po našim ulazima "
                     f"(pokrivenost {coverage:.2f}) — koristi se medijan")
        if policy_note:
            payout_used = median(reg_ratios)
            basis = (f"medijan (politika '{policy_note}' nije pokrivena: "
                     f"{coverage:.2f} < 1,0)")
    elif coverage is not None and coverage < COVERAGE_TIGHT:
        flags.append(f"napeto pokrivena (pokrivenost {coverage:.2f} < 1,2)")

    ps = payout_used * ni_ttm / shares
    return {
        "d_sust_ps": round(ps, 4),
        "payout_used": round(payout_used, 4),
        "payout_basis": basis,
        "coverage_announced": round(coverage, 3) if coverage is not None else None,
        "flags": flags,
        "excluded_years": sorted(excluded),
        "subsidiary_inflows": (
            {"total_eur": round(inflows, 0), "per_holding": inflow_notes,
             "note": ("pokrivenost najave matice uključuje očekivane priljeve "
                      "dividendi kćeri — činjenično iz zadnje izglasane "
                      "isplate kćeri × naš udio (v3 FAZA SOTP)")}
            if inflows else None),
        "note": ("D_sust = održivi payout × normalizirana dobit (TTM) / broj "
                 "dionica; jednokratne isplate NE ulaze u bazu"),
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from src.db import get_conn
    with get_conn() as conn:
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT id, ticker FROM companies ORDER BY ticker")
            for cid, t in cur.fetchall():
                n = classify_company(conn, cid)
                if n:
                    print(f"{t}: {n} isplata klasificirano")
        print(json.dumps({"schema": "ok"}))
