"""M-BOND: registar uvrštenih obveznica ZSE + EOD cijene (u % nominale).

Izvori (sve deterministički, bez API troška):
- službena tečajnica (rest.zse.hr price-list): popis SVIH obveznica s
  tipom (STATE/CORP/MUNI-BOND), kuponom (debt_interest_rate), dospijećem
  (debt_maturity_date), valutom kotacije ("% EUR"/"% HRK") i EOD cijenom
- imena izdavatelja: državne -> Ministarstvo financija RH (ISIN prefiks
  RHMF); korporativne -> match ISIN prefiksa izdavatelja (znakovi 3-6) s
  ISIN-ima naših share_classes; CROBIS sastavnice daju puna imena serija
- povijest cijena: zse.hr securityHistory (isti izvor kao za dionice)

Što NEMAMO iz strojnih izvora: frekvenciju kupona i konvenciju dana (žive
u prospektu). Pretpostavka: godišnji kupon + ACT/ACT — OZNAČENO
`pretpostavka` badgeom u UI (isti obrazac kao kod dionica); izdavatelji bez
determinističkog imena nose status 'u obradi' (ne izmišlja se ništa).
"""
from __future__ import annotations

from datetime import date, timedelta

BOND_TYPES = {"STATE-BOND": "državna", "CORP-BOND": "korporativna",
              "MUNI-BOND": "municipalna"}
HISTORY_FROM = "2024-07-01"


def ensure_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bonds (
                symbol TEXT PRIMARY KEY,
                isin TEXT NOT NULL,
                issuer TEXT,             -- NULL = 'u obradi' (ne izmišljamo)
                series_name TEXT,        -- puno ime serije gdje postoji (CROBIS)
                btype TEXT NOT NULL,     -- državna | korporativna | municipalna
                coupon_pct NUMERIC,
                maturity_date DATE,
                price_currency TEXT,     -- '% EUR' | '% HRK' (kotacija u % nominale)
                coupon_freq INT,         -- 1 = godišnji (pretpostavka dok prospekt ne potvrdi)
                freq_assumed BOOLEAN DEFAULT TRUE,
                day_count TEXT DEFAULT 'ACT/ACT',
                day_count_assumed BOOLEAN DEFAULT TRUE,
                nominal_note TEXT,       -- nominala: n/p dok se ne ekstrahira iz prospekta
                status TEXT NOT NULL DEFAULT 'u obradi',  -- complete | u obradi
                source TEXT,
                updated_at TIMESTAMPTZ DEFAULT now());
            CREATE TABLE IF NOT EXISTS bond_prices_eod (
                symbol TEXT NOT NULL,
                trade_date DATE NOT NULL,
                clean_price_pct NUMERIC,  -- ČISTA cijena u % nominale
                turnover_eur NUMERIC,
                source TEXT,
                PRIMARY KEY (symbol, trade_date));
        """)
    conn.commit()


def _issuer_maps(conn) -> tuple[dict, dict]:
    with conn.cursor() as cur:
        cur.execute("""SELECT sc.isin, c.name FROM share_classes sc
                       JOIN companies c ON c.id = sc.company_id
                       WHERE sc.isin IS NOT NULL""")
        pref2name = {isin[2:6]: name for isin, name in cur.fetchall()}
        cur.execute("""SELECT ticker, name FROM index_constituents
                       WHERE index_isin IN ('HRZB00ICRBS8', 'HRZB00ICRBT6')""")
        series = dict(cur.fetchall())
    return pref2name, series


def _price_list(d: str) -> dict:
    import requests
    from .prices import _rest_base, _verify
    base = _rest_base()
    r = requests.get(f"{base.rstrip('/')}/price-list/XZAG/{d}/json",
                     timeout=90, verify=_verify())
    r.raise_for_status()
    return r.json()


def sync_master(conn, d: str | None = None, log=print) -> int:
    """Upsert master data svih uvrštenih obveznica iz službene tečajnice.
    Bez zadanog datuma uzima ZADNJU dostupnu tečajnicu (današnja izlazi tek
    nakon zatvaranja trgovine)."""
    ensure_tables(conn)
    data = None
    if d:
        data = _price_list(d)
    else:
        for i in range(8):
            try:
                data = _price_list((date.today() - timedelta(days=i)).isoformat())
                break
            except Exception:  # noqa: BLE001 — još nema/vikend
                continue
    if data is None:
        log("  tečajnica nedostupna zadnjih 8 dana — master preskočen")
        return 0
    pref2name, series = _issuer_maps(conn)
    n = 0
    for x in data.get("securities") or []:
        if x.get("security_type") not in BOND_TYPES:
            continue
        isin = x["isin"]
        pref = isin[2:6] if isin.startswith("HR") else None
        issuer = ("Ministarstvo financija Republike Hrvatske" if pref == "RHMF"
                  else pref2name.get(pref))
        srs = series.get(x["symbol"])
        status = "complete" if (issuer and x.get("debt_interest_rate")
                                and x.get("debt_maturity_date")) else "u obradi"
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO bonds (symbol, isin, issuer, series_name, btype,
                     coupon_pct, maturity_date, price_currency, coupon_freq,
                     status, source)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,1,%s,%s)
                   ON CONFLICT (symbol) DO UPDATE SET
                     isin=EXCLUDED.isin, issuer=COALESCE(EXCLUDED.issuer, bonds.issuer),
                     series_name=COALESCE(EXCLUDED.series_name, bonds.series_name),
                     btype=EXCLUDED.btype, coupon_pct=EXCLUDED.coupon_pct,
                     maturity_date=EXCLUDED.maturity_date,
                     price_currency=EXCLUDED.price_currency,
                     status=EXCLUDED.status, source=EXCLUDED.source,
                     updated_at=now()""",
                (x["symbol"], isin, issuer, srs, BOND_TYPES[x["security_type"]],
                 x.get("debt_interest_rate"), x.get("debt_maturity_date"),
                 x.get("price_currency"), status,
                 "ZSE službena tečajnica (price-list JSON) + ISIN matching izdavatelja"))
        n += 1
    conn.commit()
    return n


def update_prices(conn, lookback_days: int = 7, log=print) -> int:
    """EOD cijene obveznica (čiste, % nominale) iz tečajnice — idempotentno."""
    ensure_tables(conn)
    n = 0
    for i in range(lookback_days, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        try:
            data = _price_list(d)
        except Exception:  # noqa: BLE001 — vikend/praznik nema liste
            continue
        eff = data.get("date") or d
        with conn.cursor() as cur:
            for x in data.get("securities") or []:
                if x.get("security_type") not in BOND_TYPES:
                    continue
                px = x.get("close_price")
                if px is None:
                    continue
                cur.execute(
                    """INSERT INTO bond_prices_eod
                         (symbol, trade_date, clean_price_pct, turnover_eur, source)
                       VALUES (%s,%s,%s,%s,%s)
                       ON CONFLICT (symbol, trade_date) DO UPDATE SET
                         clean_price_pct=EXCLUDED.clean_price_pct,
                         turnover_eur=EXCLUDED.turnover_eur""",
                    (x["symbol"], x.get("trade_date") or eff, px,
                     x.get("turnover"), "ZSE službena tečajnica (price-list JSON)"))
                n += 1
        conn.commit()
    return n


def backfill_history(conn, log=print) -> None:
    """Povijest cijena po obveznici (securityHistory, isti izvor kao dionice)."""
    from .calibrate import fetch_security_history
    ensure_tables(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT symbol, isin FROM bonds ORDER BY symbol")
        rows = cur.fetchall()
    for sym, isin in rows:
        try:
            hist = fetch_security_history(isin, HISTORY_FROM)
        except Exception as e:  # noqa: BLE001
            log(f"  [skip] {sym}: {type(e).__name__}: {e}")
            continue
        with conn.cursor() as cur:
            for d, close, _vol, turnover in hist:
                cur.execute(
                    """INSERT INTO bond_prices_eod
                         (symbol, trade_date, clean_price_pct, turnover_eur, source)
                       VALUES (%s,%s,%s,%s,%s)
                       ON CONFLICT (symbol, trade_date) DO NOTHING""",
                    (sym, d, close, turnover, "zse.hr securityHistory (web JSON)"))
        conn.commit()
        log(f"  {sym}: {len(hist)} zapisa")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from .db import get_conn
    with get_conn() as conn:
        print(f"master: {sync_master(conn)} obveznica")
        if "--backfill" in sys.argv:
            backfill_history(conn)
        print(f"cijene: +{update_prices(conn)}")
