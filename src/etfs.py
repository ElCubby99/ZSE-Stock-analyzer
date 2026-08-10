"""M63: registar ETF-ova uvrštenih na ZSE + EOD cijene.

Izvori (deterministički, bez API troška — isti obrazac kao M-BOND):
- službena tečajnica (rest.zse.hr price-list): popis SVIH ETF-ova
  (security_type='ETF') s ISIN-om, valutom i EOD cijenom/prometom
- imena fondova i indeksi koje prate: KURIRANO iz službenih objava
  izdavatelja na EHO-u (KIID dokumenti + odluke Burze o uvrštenju s
  ISIN-om — izvor uz svaki zapis); novi ETF bez kuriranog zapisa dobiva
  status 'u obradi' (ništa se ne izmišlja)
- povijest cijena: zse.hr securityHistory (isti izvor kao dionice)

ETF replicira indeks — fer-vrijednost analiza se NE radi (vrijednost je
košarica indeksa); stranica prikazuje činjenice: cijenu, promet,
likvidnost i podatke indeksa koji fond prati (gdje ih imamo — ZSE
indeksi; za strane indekse nemamo izvor serije pa stoji samo naziv).
"""
from __future__ import annotations

from datetime import date, timedelta

HISTORY_FROM = "2024-07-01"

# Kurirani registar: ime fonda + indeks koji prati, SVE iz službenih objava
# izdavatelja (InterCapital ETF d.o.o. / ranije INTERCAPITAL ASSET
# MANAGEMENT d.o.o.) na EHO-u — KIID po pod-fondu i odluke o uvrštenju.
# index_isin = naš ZSE indeks (index_eod serija) kad postoji; None = strani
# indeks bez našeg izvora serije.
CURATED = {
    "7CRO": {
        "isin": "HRICAMFCR102",
        "name": "InterCapital CROBEX10tr UCITS ETF",
        "index_name": "CROBEX10tr",
        "index_isin": "HRZB00ICB103",
        "category": "dionički (Hrvatska)",
        "source": ("KIID pod-fonda, EHO objave izdavatelja InterCapital ETF "
                   "d.o.o. (npr. eho.zse.hr, 'Dokument s ključnim "
                   "informacijama … INTERCAPITAL CROBEX10tr UCITS ETF')"),
    },
    "7SLO": {
        "isin": "HRICAMFSBI06",
        "name": "InterCapital SBITOP TR UCITS ETF",
        "index_name": "SBITOP TR (Ljubljanska burza)",
        "index_isin": None,
        "category": "dionički (Slovenija)",
        "source": "KIID pod-fonda, EHO objave izdavatelja InterCapital ETF d.o.o.",
    },
    "7BET": {
        "isin": "HRICAMFBETR5",
        "name": "InterCapital BET-TRN UCITS ETF",
        "index_name": "BET-TRN (Burza u Bukureštu)",
        "index_isin": None,
        "category": "dionički (Rumunjska)",
        "source": "KIID pod-fonda, EHO objave izdavatelja InterCapital ETF d.o.o.",
    },
    "7POL": {
        "isin": "HRICAMFPWIG3",
        "name": "InterCapital Poland WIG30TR UCITS ETF",
        "index_name": "WIG30TR (Varšavska burza)",
        "index_isin": None,
        "category": "dionički (Poljska)",
        "source": ("Odluka Burze o uvrštenju HRICAMFPWIG3 (EHO, 13.5.2026.) + "
                   "Prezentacija o uvrštenju (EHO, 20.5.2026.)"),
    },
    "7GROM": {
        "isin": "HRICAMFERGB2",
        "name": "InterCapital EUR Romania Govt Bond 5-10yr UCITS ETF",
        "index_name": "košarica rumunjskih državnih obveznica u EUR (5-10 g.)",
        "index_isin": None,
        "category": "obveznički (Rumunjska)",
        "source": ("Odluka Burze o uvrštenju HRICAMFERGB2 (EHO, 3.6.2024.) + "
                   "KIID pod-fonda (EHO objave izdavatelja)"),
    },
    "7CASH": {
        "isin": "HRICAMFEUMM1",
        "name": "InterCapital Euro Money Market UCITS ETF",
        "index_name": "novčano tržište eurozone (nema dioničkog indeksa)",
        "index_isin": None,
        "category": "novčani (eurozona)",
        "source": "KIID pod-fonda, EHO objave izdavatelja InterCapital ETF d.o.o.",
    },
}
ISSUER = "InterCapital ETF d.o.o."


def ensure_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS etfs (
                symbol TEXT PRIMARY KEY,
                isin TEXT NOT NULL,
                name TEXT,               -- NULL = 'u obradi' (ne izmišljamo)
                issuer TEXT,
                index_name TEXT,         -- indeks/košarica koju fond prati
                index_isin TEXT,         -- naš ZSE indeks (index_eod) ili NULL
                category TEXT,
                price_currency TEXT,
                status TEXT NOT NULL DEFAULT 'u obradi',  -- complete | u obradi
                source TEXT,
                updated_at TIMESTAMPTZ DEFAULT now());
            CREATE TABLE IF NOT EXISTS etf_prices_eod (
                symbol TEXT NOT NULL,
                trade_date DATE NOT NULL,
                close_eur NUMERIC,
                volume NUMERIC,
                turnover_eur NUMERIC,
                source TEXT,
                PRIMARY KEY (symbol, trade_date));
        """)
    conn.commit()


def _price_list(d: str) -> dict:
    import requests
    from .prices import _rest_base, _verify
    base = _rest_base()
    r = requests.get(f"{base.rstrip('/')}/price-list/XZAG/{d}/json",
                     timeout=90, verify=_verify())
    r.raise_for_status()
    return r.json()


def sync_master(conn, d: str | None = None, log=print) -> int:
    """Upsert master podataka svih uvrštenih ETF-ova iz službene tečajnice;
    kurirani zapis (ime/indeks iz EHO objava) mora potvrditi ISIN — inače
    'u obradi' (novi fond dok se ne kurira, ili promjena ISIN-a)."""
    ensure_tables(conn)
    data = None
    if d:
        data = _price_list(d)
    else:
        for i in range(8):
            try:
                data = _price_list((date.today() - timedelta(days=i)).isoformat())
                break
            except Exception:  # noqa: BLE001 — vikend/praznik nema liste
                continue
    if data is None:
        log("  tečajnica nedostupna zadnjih 8 dana — ETF master preskočen")
        return 0
    n = 0
    for x in data.get("securities") or []:
        if x.get("security_type") != "ETF":
            continue
        sym, isin = x["symbol"], x["isin"]
        cur_meta = CURATED.get(sym)
        if cur_meta and cur_meta["isin"] != isin:
            log(f"  [WARN] {sym}: ISIN tečajnice {isin} != kurirani "
                f"{cur_meta['isin']} — zapis ide u 'u obradi'")
            cur_meta = None
        status = "complete" if cur_meta else "u obradi"
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO etfs (symbol, isin, name, issuer, index_name,
                     index_isin, category, price_currency, status, source)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (symbol) DO UPDATE SET
                     isin=EXCLUDED.isin,
                     name=COALESCE(EXCLUDED.name, etfs.name),
                     issuer=COALESCE(EXCLUDED.issuer, etfs.issuer),
                     index_name=COALESCE(EXCLUDED.index_name, etfs.index_name),
                     index_isin=EXCLUDED.index_isin,
                     category=COALESCE(EXCLUDED.category, etfs.category),
                     price_currency=EXCLUDED.price_currency,
                     status=EXCLUDED.status, source=EXCLUDED.source,
                     updated_at=now()""",
                (sym, isin,
                 cur_meta["name"] if cur_meta else None,
                 ISSUER if cur_meta else None,
                 cur_meta["index_name"] if cur_meta else None,
                 cur_meta["index_isin"] if cur_meta else None,
                 cur_meta["category"] if cur_meta else None,
                 x.get("price_currency"), status,
                 (cur_meta["source"] if cur_meta
                  else "ZSE službena tečajnica (price-list JSON); ime/indeks čekaju kuriranje iz EHO objava")))
        n += 1
    conn.commit()
    return n


def update_prices(conn, lookback_days: int = 7, log=print) -> int:
    """EOD cijene ETF-ova iz tečajnice — idempotentno. Tečajnica za dan bez
    trgovine ponavlja ZADNJI trade_date retka, pa se upisuje x['trade_date']
    (stvarni dan trgovanja), ne datum liste."""
    ensure_tables(conn)
    n = 0
    for i in range(lookback_days, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        try:
            data = _price_list(d)
        except Exception:  # noqa: BLE001 — vikend/praznik nema liste
            continue
        with conn.cursor() as cur:
            for x in data.get("securities") or []:
                if x.get("security_type") != "ETF":
                    continue
                px, td = x.get("close_price"), x.get("trade_date")
                if px is None or td is None:
                    continue
                if (x.get("price_currency") or "EUR") != "EUR":
                    continue
                cur.execute(
                    """INSERT INTO etf_prices_eod
                         (symbol, trade_date, close_eur, volume, turnover_eur, source)
                       VALUES (%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (symbol, trade_date) DO UPDATE SET
                         close_eur=EXCLUDED.close_eur, volume=EXCLUDED.volume,
                         turnover_eur=EXCLUDED.turnover_eur""",
                    (x["symbol"], td, px, x.get("volume"), x.get("turnover"),
                     "ZSE službena tečajnica (price-list JSON)"))
                n += 1
        conn.commit()
    return n


def backfill_history(conn, log=print) -> None:
    """Povijest cijena po ETF-u (securityHistory, isti izvor kao dionice)."""
    from .calibrate import fetch_security_history
    ensure_tables(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT symbol, isin FROM etfs ORDER BY symbol")
        rows = cur.fetchall()
    for sym, isin in rows:
        try:
            hist = fetch_security_history(isin, HISTORY_FROM)
        except Exception as e:  # noqa: BLE001
            log(f"  [skip] {sym}: {type(e).__name__}: {e}")
            continue
        with conn.cursor() as cur:
            for d, close, vol, turnover in hist:
                cur.execute(
                    """INSERT INTO etf_prices_eod
                         (symbol, trade_date, close_eur, volume, turnover_eur, source)
                       VALUES (%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (symbol, trade_date) DO NOTHING""",
                    (sym, d, close, vol, turnover, "zse.hr securityHistory (web JSON)"))
        conn.commit()
        log(f"  {sym}: {len(hist)} zapisa")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from .db import get_conn
    with get_conn() as conn:
        print(f"master: {sync_master(conn)} ETF-ova")
        if "--backfill" in sys.argv:
            backfill_history(conn)
        print(f"cijene: +{update_prices(conn)}")
