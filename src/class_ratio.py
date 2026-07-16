"""v3 FAZA S: raspodjela vrijednosti FIRME po klasama dionica.

Vrijednost firme (fer-zona iz FAZE A, klasno agnostična) raspoređuje se na
klase TRŽIŠNO OPAŽENIM omjerom cijena klasa:
  ratio = medijan dnevnog omjera close(redovna)/close(povlaštena) kroz
  zadnjih 5 g, SAMO za dane kad su OBJE klase stvarno trgovane (volume>0);
  min N=30 opažanja, inače fallback: omjer po dividendnim pravima (na ZSE
  parovima identična dividenda -> 1,0) uz oznaku `teorijski omjer`.

Formula (čuva ukupnu vrijednost firme):
  fer_povlaštena(bound) = bound × N_uk / (n_red × ratio + n_povl)
  fer_redovna(bound)    = ratio × fer_povlaštena(bound)
  => n_red×fer_red + n_povl×fer_povl = bound × N_uk  (identitet)

Premija redovne je POVIJESNI TRŽIŠNI MEDIJAN — naša raspodjela, ne
fundamentalna tvrdnja; obje klase iste firme imaju zone izvedene iz ISTE
vrijednosti firme (nemoguće je da jedna bude "u zoni" a druga "+58%" osim
ako današnji omjer klasa odstupa od povijesnog medijana — i tada je TA
razlika činjenica koju prikazujemo).
"""
from __future__ import annotations

RATIO_MIN_DAYS = 30
RATIO_WINDOW_DAYS = 1826   # ~5 godina


def measure_ratio(conn, class_a_id: int, class_b_id: int) -> dict:
    """Medijan omjera close(A)/close(B) na danima kad su OBJE trgovane."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT count(*),
                      percentile_cont(0.5) WITHIN GROUP
                          (ORDER BY p1.close_eur / p2.close_eur),
                      min(p1.trade_date)::text, max(p1.trade_date)::text
               FROM prices_eod p1
               JOIN prices_eod p2 ON p2.trade_date = p1.trade_date
               WHERE p1.share_class_id=%s AND p2.share_class_id=%s
                 AND p1.close_eur IS NOT NULL AND p2.close_eur IS NOT NULL
                 AND COALESCE(p1.volume, 0) > 0 AND COALESCE(p2.volume, 0) > 0
                 AND p1.trade_date > CURRENT_DATE - %s""",
            (class_a_id, class_b_id, RATIO_WINDOW_DAYS))
        n, med, d0, d1 = cur.fetchone()
    if n and n >= RATIO_MIN_DAYS and med:
        return {"ratio": round(float(med), 4), "n_days": int(n),
                "period": f"{d0}..{d1}", "basis": "tržišni medijan",
                "note": (f"medijan dnevnog omjera cijena klasa kroz {n} dana "
                         f"({d0}..{d1}) na kojima su OBJE klase trgovane")}
    return {"ratio": 1.0, "n_days": int(n or 0), "period": None,
            "basis": "teorijski omjer",
            "note": (f"premalo zajedničkih trgovanih dana ({n or 0} < "
                     f"{RATIO_MIN_DAYS}) — fallback na omjer dividendnih "
                     "prava (identična dividenda po dionici -> 1,0), "
                     "OZNAČENA pretpostavka")}


def class_zones(conn, company_id: int, zone_low, zone_high) -> dict | None:
    """Po-klasne fer-zone iz ISTE vrijednosti firme. None za jednu klasu
    ili bez zone. -> {class_ticker: {zone_low, zone_high}, _meta: {...}}"""
    if zone_low is None or zone_high is None:
        return None
    with conn.cursor() as cur:
        cur.execute(
            """SELECT sc.id, sc.ticker, sc.class_type,
                      (sc.shares_issued - COALESCE(sc.treasury_shares, 0))::float
               FROM share_classes sc WHERE sc.company_id=%s
                 AND sc.shares_issued IS NOT NULL
               ORDER BY (sc.class_type = 'ordinary') DESC, sc.ticker""",
            (company_id,))
        rows = cur.fetchall()
    if len(rows) != 2 or any(r[3] is None or r[3] <= 0 for r in rows):
        return None
    (id_a, tk_a, _ct_a, n_a), (id_b, tk_b, _ct_b, n_b) = rows
    m = measure_ratio(conn, id_a, id_b)
    ratio = m["ratio"]
    n_tot = n_a + n_b
    out = {}
    for bound_name, bound in (("zone_low", zone_low), ("zone_high", zone_high)):
        fer_b = bound * n_tot / (n_a * ratio + n_b)
        fer_a = ratio * fer_b
        out.setdefault(tk_a, {})[bound_name] = round(fer_a, 4)
        out.setdefault(tk_b, {})[bound_name] = round(fer_b, 4)
    out["_meta"] = {
        "ordinary": tk_a, "preferred": tk_b,
        "ratio": ratio, "ratio_basis": m["basis"], "ratio_n_days": m["n_days"],
        "ratio_period": m["period"], "ratio_note": m["note"],
        "premium_pct": round((ratio - 1) * 100, 1),
        "note": ("obje klase imaju zone izvedene iz ISTE vrijednosti firme, "
                 "raspoređene tržišnim omjerom klasa — premija redovne je "
                 "povijesni tržišni medijan (naša raspodjela, ne "
                 "fundamentalna tvrdnja)"),
    }
    return out
