"""Kalibracija parametara IZ TRŽIŠNIH SERIJA (M10) — zaseban korak.

Sada kad prices_eod ima ~2 godine povijesti (zse.hr securityHistory), dvije
dosad OZNAČENE pretpostavke postaju izračunljive:

1. BETA po firmi: tjedni log-prinosi klase vs CROBEX (zse.hr indexHistory,
   ISIN HRZB00ICBEX6, isti javni web REST token kao tečajnica). OLS nagib
   (cov/var), uz R² i broj tjednih parova. Prag: >= MIN_WEEKS parova inače
   beta OSTAJE pretpostavka 1,0 (nelikvidne serije ne daju smislen nagib).
2. POVIJESNI ADRS HOLDING DISKONT: dnevna serija diskonta
   1 − trž.kap(ADRS+ADRS2) / NAV_proxy(t), gdje je
   NAV_proxy(t) = 0.6747×mcap_CROS(t) + 0.9354×mcap_MAIS(t) + FIKSNI dio
   (neuvršteni segmenti po FY2025 multiplama + neto dug FY2025 — konstanta!).
   Kalibrirani raspon diskonta = p25–p75 opažene serije.

OGRADE (idu i u izvore parametara):
- NAV proxy drži neuvrštene dijelove i neto dug KONSTANTNIMA (FY2025) kroz
  cijeli prozor — serija mjeri odnos prema uvrštenim dijelovima, ne pun NAV;
- CROS je nelikvidan -> zadnji poznati close se prenosi naprijed (max 60 d);
- udjeli (67,47% / 93,54%) konstantni po FY2025 godišnjem izvješću.

Rezultati se PERZISTIRAJU u tablicu calibrations (key -> JSONB s metodom,
brojkama i izvorom); params_calibrated ih čita i tek TADA skida oznaku
"pretpostavka" s bete / holding diskonta.

CLI:
  python -m src.calibrate --all          # index + MAIS backfill + bete + diskont
  python -m src.calibrate --beta ADRS2 PODR ...
  python -m src.calibrate --discount
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta

from .db import get_conn

CROBEX_ISIN = "HRZB00ICBEX6"      # CROBEX (široki) — zse.hr /hr/indeks
CROBEX10_ISIN = "HRZB00ICB103"
HISTORY_FROM = "2024-07-01"        # dubina backfilla (2 g)
MIN_WEEKS = 40                     # min tjednih parova prinosa za kalibraciju bete
FFILL_MAX_DAYS = 60                # koliko dugo se zadnji close smije prenositi

# ADRS NAV proxy — FY2025 konstante (izvor: compute_sotp breakdown / GI 2025):
ADRS_STAKE_CROS = 0.6747           # GI 2025 str. 4
ADRS_STAKE_MAIS = 0.9354           # GI 2025 str. 4
ADRS_UNLISTED_FIXED = 301_900_000  # HUP 169,5M + Cromaris 90,4M + Energetika 42,0M
#   (segment EBITDA × placeholder multiple 7,5/8,0/7,0 — kao u SOTP-u)
ADRS_NET_CASH_FIXED = -170_690_000  # −neto dug FY2025 (grupni agregat)


# ---------- dohvat serija (javni zse.hr web JSON; isti izvor kao graf) ----------
def _hr_num(s):
    if s in (None, ""):
        return None
    return float(str(s).replace(".", "").replace(",", "."))


def _hr_date(s):
    d, m, y = str(s).strip(". ").split(".")[:3]
    return f"{y}-{int(m):02d}-{int(d):02d}"


def _rest():
    from .prices import _rest_base
    return _rest_base()


def fetch_index_history(isin: str, date_from: str, date_to: str | None = None):
    """-> [(iso_date, close_value)] uzlazno. zse.hr /json/indexHistory."""
    import requests
    date_to = date_to or date.today().isoformat()
    r = requests.get(
        f"https://zse.hr/json/indexHistory/{isin}/{date_from}/{date_to}/hr",
        params={"restAPI": _rest()},
        headers={"X-Requested-With": "XMLHttpRequest"}, timeout=90)
    r.raise_for_status()
    rows = (r.json() or {}).get("rows") or []
    out = [(_hr_date(x["date"]), _hr_num(x.get("last_value"))) for x in rows]
    return sorted((d, v) for d, v in out if v)


def fetch_security_history(isin: str, date_from: str, date_to: str | None = None,
                           model: str = "CT"):
    """-> [(iso_date, close, volume, turnover)] uzlazno (zse.hr securityHistory)."""
    import requests
    date_to = date_to or date.today().isoformat()
    r = requests.get(
        f"https://zse.hr/json/securityHistory/{isin}/{date_from}/{date_to}/hr",
        params={"trading_model_id": model, "restAPI": _rest()},
        headers={"X-Requested-With": "XMLHttpRequest"}, timeout=90)
    r.raise_for_status()
    rows = (r.json() or {}).get("rows") or []
    out = []
    for x in rows:
        d = x.get("date_yyyy_MM_dd") or _hr_date(x["date"])
        c = x.get("last_price_n") or _hr_num(x.get("last_price"))
        if c:
            out.append((d, float(c), x.get("volume_n"), x.get("turnover_n")))
    return sorted(out)


def ensure_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS index_eod (
                index_isin TEXT NOT NULL,
                trade_date DATE NOT NULL,
                close_value NUMERIC NOT NULL,
                source TEXT,
                PRIMARY KEY (index_isin, trade_date));
            CREATE TABLE IF NOT EXISTS calibrations (
                key TEXT PRIMARY KEY,
                value JSONB NOT NULL,
                source TEXT,
                computed_at TIMESTAMPTZ DEFAULT now());
        """)
    conn.commit()


def backfill_index(conn, isin: str = CROBEX_ISIN, name: str = "CROBEX") -> int:
    rows = fetch_index_history(isin, HISTORY_FROM)
    with conn.cursor() as cur:
        for d, v in rows:
            cur.execute(
                """INSERT INTO index_eod (index_isin, trade_date, close_value, source)
                   VALUES (%s,%s,%s,%s)
                   ON CONFLICT (index_isin, trade_date)
                   DO UPDATE SET close_value=EXCLUDED.close_value""",
                (isin, d, v, f"zse.hr indexHistory ({name}, web JSON)"))
    conn.commit()
    print(f"  {name}: {len(rows)} dnevnih vrijednosti ({rows[0][0]}..{rows[-1][0]})")
    return len(rows)


def backfill_class(conn, class_ticker: str) -> int:
    """Povijest za klasu koja fali u prices_eod (npr. MAIS — SOTP ulaz)."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, company_id, isin FROM share_classes WHERE ticker=%s",
                    (class_ticker,))
        r = cur.fetchone()
        if not r or not r[2]:
            print(f"  [skip] {class_ticker}: nema klase/ISIN-a")
            return 0
        scid, cid, isin = r
        rows = fetch_security_history(isin, HISTORY_FROM)
        for d, c, vol, tov in rows:
            cur.execute(
                """INSERT INTO prices_eod (company_id, share_class_id, trade_date,
                                           close_eur, volume, source)
                   VALUES (%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (company_id, trade_date, COALESCE(share_class_id, 0))
                   DO UPDATE SET close_eur=EXCLUDED.close_eur,
                                 volume=EXCLUDED.volume, source=EXCLUDED.source""",
                (cid, scid, d, c, vol, "zse.hr securityHistory (web JSON)"))
    conn.commit()
    print(f"  {class_ticker}: {len(rows)} EOD zapisa")
    return len(rows)


# ---------- beta (tjedni log-prinosi vs CROBEX) ----------
def _weekly_last(series: list[tuple]) -> dict:
    """[(iso_date, close)] -> {(iso_year, iso_week): zadnji close u tjednu}."""
    out = {}
    for d, v in series:
        y, w, _ = date.fromisoformat(d).isocalendar()
        out[(y, w)] = v            # uzlazni redoslijed -> zadnji pregazi
    return out


def calc_beta(conn, class_ticker: str, index_isin: str = CROBEX_ISIN) -> dict | None:
    import math
    with conn.cursor() as cur:
        cur.execute(
            """SELECT p.trade_date::text, p.close_eur FROM prices_eod p
               JOIN share_classes sc ON sc.id=p.share_class_id
               WHERE sc.ticker=%s AND p.close_eur IS NOT NULL
               ORDER BY p.trade_date""", (class_ticker,))
        stock = [(d, float(c)) for d, c in cur.fetchall()]
        cur.execute(
            """SELECT trade_date::text, close_value FROM index_eod
               WHERE index_isin=%s ORDER BY trade_date""", (index_isin,))
        idx = [(d, float(c)) for d, c in cur.fetchall()]
    if len(stock) < 10 or len(idx) < 10:
        return None
    sw, iw = _weekly_last(stock), _weekly_last(idx)
    weeks = sorted(set(sw) & set(iw))
    pairs = []
    for w0, w1 in zip(weeks, weeks[1:]):
        # prinos SAMO preko susjednih ISO tjedana (rupe u nelikvidnoj seriji
        # ne smiju postati višetjedni "prinosi")
        if (w1[0] == w0[0] and w1[1] == w0[1] + 1) or \
           (w1[0] == w0[0] + 1 and w1[1] == 1):
            pairs.append((math.log(sw[w1] / sw[w0]), math.log(iw[w1] / iw[w0])))
    n = len(pairs)
    if n < MIN_WEEKS:
        return {"class_ticker": class_ticker, "n_weeks": n, "calibrated": False,
                "reason": f"premalo tjednih parova ({n} < {MIN_WEEKS}) — "
                          f"nelikvidna/kratka serija"}
    ms = sum(p[0] for p in pairs) / n
    mi = sum(p[1] for p in pairs) / n
    cov = sum((p[0] - ms) * (p[1] - mi) for p in pairs) / (n - 1)
    var = sum((p[1] - mi) ** 2 for p in pairs) / (n - 1)
    if var == 0:
        return None
    beta = cov / var
    var_s = sum((p[0] - ms) ** 2 for p in pairs) / (n - 1)
    r2 = (cov * cov) / (var * var_s) if var_s else 0.0
    return {"class_ticker": class_ticker, "beta": round(beta, 3),
            "r2": round(r2, 3), "n_weeks": n, "calibrated": True,
            "period": f"{stock[0][0]}..{stock[-1][0]}",
            "index": "CROBEX", "index_isin": index_isin,
            "method": "OLS nagib tjednih log-prinosa (zadnji close u ISO tjednu; "
                      "samo susjedni tjedni)"}


# ---------- povijesni ADRS holding diskont ----------
def discount_series(conn) -> dict | None:
    cur = conn.cursor()

    def series(tk):
        cur.execute(
            """SELECT p.trade_date::text, p.close_eur FROM prices_eod p
               JOIN share_classes sc ON sc.id=p.share_class_id
               WHERE sc.ticker=%s AND p.close_eur IS NOT NULL
               ORDER BY p.trade_date""", (tk,))
        return {d: float(c) for d, c in cur.fetchall()}

    def shares(tk):
        cur.execute("""SELECT shares_issued - COALESCE(treasury_shares, 0)
                       FROM share_classes WHERE ticker=%s""", (tk,))
        r = cur.fetchone()
        return float(r[0]) if r and r[0] else None

    px = {tk: series(tk) for tk in ("ADRS", "ADRS2", "CROS", "CROS2", "MAIS")}
    sh = {tk: shares(tk) for tk in px}
    cur.close()
    if any(v is None for v in sh.values()) or any(not v for v in px.values()):
        return None

    all_days = sorted(set().union(*[set(s) for s in px.values()]))
    last, last_d = {}, {}
    rows = []
    for d in all_days:
        for tk in px:
            if d in px[tk]:
                last[tk], last_d[tk] = px[tk][d], d
        if len(last) < len(px):
            continue                    # čekaj da SVE serije imaju prvi close
        # staleness guard: predugo prenošen close -> dan se preskače
        dd = date.fromisoformat(d)
        if any((dd - date.fromisoformat(last_d[tk])).days > FFILL_MAX_DAYS
               for tk in px):
            continue
        mcap_adrs = last["ADRS"] * sh["ADRS"] + last["ADRS2"] * sh["ADRS2"]
        mcap_cros = last["CROS"] * sh["CROS"] + last["CROS2"] * sh["CROS2"]
        mcap_mais = last["MAIS"] * sh["MAIS"]
        nav = (ADRS_STAKE_CROS * mcap_cros + ADRS_STAKE_MAIS * mcap_mais
               + ADRS_UNLISTED_FIXED + ADRS_NET_CASH_FIXED)
        if nav <= 0:
            continue
        rows.append((d, 1.0 - mcap_adrs / nav))
    if len(rows) < 60:
        return None
    vals = sorted(v for _, v in rows)
    q = lambda p: vals[min(len(vals) - 1, int(p * len(vals)))]
    return {
        "n_days": len(rows), "period": f"{rows[0][0]}..{rows[-1][0]}",
        "p25": round(q(0.25), 4), "median": round(q(0.50), 4),
        "p75": round(q(0.75), 4),
        "min": round(vals[0], 4), "max": round(vals[-1], 4),
        "latest": round(rows[-1][1], 4), "latest_date": rows[-1][0],
        "method": ("1 − mcap(ADRS+ADRS2)/NAV_proxy(t); NAV_proxy = "
                   f"{ADRS_STAKE_CROS}×mcap(CROS+CROS2) + {ADRS_STAKE_MAIS}×"
                   f"mcap(MAIS) + {ADRS_UNLISTED_FIXED / 1e6:.1f}M (neuvršteni, "
                   f"FY2025 multiple) {ADRS_NET_CASH_FIXED / 1e6:+.1f}M (neto dug "
                   "FY2025) — KONSTANTE kroz prozor; nelikvidni zadnji close "
                   f"prenosi se max {FFILL_MAX_DAYS} d"),
    }


def store(conn, key: str, value: dict, source: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO calibrations (key, value, source)
               VALUES (%s,%s,%s)
               ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value,
                 source=EXCLUDED.source, computed_at=now()""",
            (key, json.dumps(value, ensure_ascii=False), source))
    conn.commit()


# primarna LIKVIDNA klasa po firmi za betu (ADRS: povlaštena nosi ~93% prometa)
BETA_CLASS_OF = {
    "ADRS": "ADRS2", "CROS": "CROS", "ZABA": "ZABA", "PODR": "PODR",
    "ATGR": "ATGR", "KOEI": "KOEI", "KODT": "KODT", "RIVP": "RIVP",
    "ADPL": "ADPL", "SPAN": "SPAN", "ARNT": "ARNT", "DLKV": "DLKV",
    "IG": "IG", "ZITO": "ZITO", "TOK": "TOK", "HT": "HT", "HPB": "HPB",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="kalibracija bete i holding diskonta")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--beta", nargs="*", default=None,
                    help="tickeri FIRMI za betu (default: sve iz BETA_CLASS_OF)")
    ap.add_argument("--discount", action="store_true", help="ADRS holding diskont")
    a = ap.parse_args(argv)

    with get_conn() as conn:
        ensure_tables(conn)
        if a.all:
            print("== backfill serija ==")
            backfill_index(conn)
            backfill_class(conn, "MAIS")
        do_beta = a.all or a.beta is not None
        do_disc = a.all or a.discount

        if do_beta:
            print("== beta (tjedni log-prinosi vs CROBEX) ==")
            tickers = a.beta if a.beta else sorted(BETA_CLASS_OF)
            for t in tickers:
                cls = BETA_CLASS_OF.get(t.upper(), t.upper())
                res = calc_beta(conn, cls)
                if res is None:
                    print(f"  {t}: serija prekratka — beta ostaje pretpostavka 1,0")
                    continue
                store(conn, f"beta:{t.upper()}", res,
                      "zse.hr securityHistory + indexHistory (CROBEX), OLS")
                if res.get("calibrated"):
                    print(f"  {t}: beta={res['beta']} (R²={res['r2']}, "
                          f"n={res['n_weeks']} tj., klasa {cls})")
                else:
                    print(f"  {t}: NEKALIBRIRANO — {res['reason']}")

        if do_disc:
            print("== ADRS povijesni holding diskont ==")
            res = discount_series(conn)
            if res is None:
                print("  nedovoljno serija (ADRS/ADRS2/CROS/CROS2/MAIS + dionice)")
            else:
                store(conn, "holding_discount:ADRS", res,
                      "prices_eod (2 g) + FY2025 SOTP konstante — proxy serija")
                print(f"  n={res['n_days']} d ({res['period']}): "
                      f"p25={res['p25']:.1%} med={res['median']:.1%} "
                      f"p75={res['p75']:.1%} (min {res['min']:.1%}, "
                      f"max {res['max']:.1%}; zadnji {res['latest']:.1%} "
                      f"na {res['latest_date']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
