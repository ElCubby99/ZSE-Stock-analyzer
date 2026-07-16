"""M-IDX: registar ZSE indeksa + dohvat povijesti i sastavnica.

TEMELJ (generalizacija instrumenta) — obrazloženje minimalnog zahvata:
tipovi instrumenata imaju disjunktne sheme (equity: financials/valuations;
indeks: serija + sastavnice; obveznica: master data + kuponi; fond: mjesečne
jedinice), pa polimorfna `instruments` tablica ne bi ništa dijelila osim
imena. Zato svaki tip dobiva SVOJE uske tablice, a zajednička površina je
na razini exporta (JSON po ruti) i route registryja. Equity tablice se NE
diraju.

Izvor: zse.hr javni web JSON (isti kao za cijene dionica):
  - /json/indexHistory/<isin>/<from>/<to>/hr   (serija)
  - /json/IndexComposition?isin=<isin>&lng=hr  (sastavnice s TEŽINAMA)
Registar imena/ISIN-a potvrđen na zse.hr/hr/indeksi/42 (16.07.2026.).
"""
from __future__ import annotations

from datetime import date

# ime -> (isin, slug za URL, kratki opis za SEO)
INDICES = {
    "CROBEX": ("HRZB00ICBEX6", "crobex", "glavni dionički indeks Zagrebačke burze"),
    "CROBEX10": ("HRZB00ICBE11", "crobex10", "10 najlikvidnijih dionica ZSE"),
    "CROBEX10tr": ("HRZB00ICB103", "crobex10tr", "CROBEX10 total return (s dividendama)"),
    "CROBEXtr": ("HRZB00ICBTR6", "crobextr", "CROBEX total return (s dividendama)"),
    "CROBEXprime": ("HRZB00ICBPR4", "crobexprime", "dionice Prime tržišta ZSE"),
    "CROBEXplus": ("HRZB00ICBEP2", "crobexplus", "širi dionički indeks ZSE"),
    "CROBEXindustrija": ("HRZB00ICBEI7", "crobexindustrija", "sektorski indeks — industrija"),
    "CROBEXkonstrukt": ("HRZB00ICBEK3", "crobexkonstrukt", "sektorski indeks — graditeljstvo"),
    "CROBEXnutris": ("HRZB00ICBEN7", "crobexnutris", "sektorski indeks — prehrana"),
    "CROBEXtransport": ("HRZB00ICBET4", "crobextransport", "sektorski indeks — promet"),
    "CROBEXturist": ("HRZB00ICBTU0", "crobexturist", "sektorski indeks — turizam"),
    "CROBIS": ("HRZB00ICRBS8", "crobis", "obveznički indeks Zagrebačke burze"),
    "CROBISTR": ("HRZB00ICRBT6", "crobistr", "CROBIS total return"),
    "ADRIAprime": ("HRZB00IADPR4", "adriaprime", "regionalni indeks (ZSE/LJSE partnerstvo)"),
}
HISTORY_FROM = "2024-07-01"  # ista dubina kao postojeći CROBEX backfill


def ensure_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS index_constituents (
                index_isin TEXT NOT NULL,
                ticker TEXT NOT NULL,
                name TEXT,
                weight_pct NUMERIC,
                free_float_factor NUMERIC,
                as_of DATE NOT NULL,
                source TEXT,
                PRIMARY KEY (index_isin, ticker));
        """)
    conn.commit()


def fetch_composition(isin: str) -> list[dict]:
    """Sastavnice s težinama iz zse.hr IndexComposition JSON-a."""
    import requests
    from .prices import _rest_base
    r = requests.get(
        "https://zse.hr/json/IndexComposition",
        params={"isin": isin, "lng": "hr", "restAPI": _rest_base()},
        headers={"X-Requested-With": "XMLHttpRequest"}, timeout=60)
    r.raise_for_status()
    d = r.json()
    rows = d.get("rows") if isinstance(d, dict) else d
    out = []
    for x in rows or []:
        w = str(x.get("weight_percentage") or "").replace("&nbsp;%", "").replace(",", ".")
        ff = str(x.get("free_float_factor") or "").replace(",", ".")
        try:
            w_val = float(w) if w and w != "-" else None
        except ValueError:
            w_val = None
        try:
            ff_val = float(ff) if ff and ff != "-" else None
        except ValueError:
            ff_val = None
        if x.get("symbol"):
            out.append({"ticker": x["symbol"], "name": x.get("name"),
                        "weight_pct": w_val, "free_float_factor": ff_val})
    return out


def refresh_constituents(conn, log=print) -> int:
    """Osvježi sastavnice SVIH indeksa (idempotentno; obveznički indeksi
    nemaju dioničke sastavnice u istom formatu pa se preskaču ako su prazni)."""
    ensure_tables(conn)
    today = date.today().isoformat()
    total = 0
    for name, (isin, _slug, _d) in INDICES.items():
        try:
            rows = fetch_composition(isin)
        except Exception as e:  # noqa: BLE001 — jedan indeks ne ruši ostale
            log(f"  [skip] {name}: {type(e).__name__}: {e}")
            continue
        if not rows:
            continue
        with conn.cursor() as cur:
            cur.execute("DELETE FROM index_constituents WHERE index_isin=%s", (isin,))
            for r in rows:
                cur.execute(
                    """INSERT INTO index_constituents
                         (index_isin, ticker, name, weight_pct, free_float_factor,
                          as_of, source)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (index_isin, ticker) DO UPDATE SET
                         name=EXCLUDED.name, weight_pct=EXCLUDED.weight_pct,
                         free_float_factor=EXCLUDED.free_float_factor,
                         as_of=EXCLUDED.as_of, source=EXCLUDED.source""",
                    (isin, r["ticker"], r["name"], r["weight_pct"],
                     r["free_float_factor"], today,
                     "zse.hr IndexComposition (web JSON)"))
        conn.commit()
        total += len(rows)
        log(f"  {name}: {len(rows)} sastavnica")
    return total


def update_index_eod(conn, lookback_days: int = 7, log=print) -> int:
    """Dopuni index_eod za sve indekse (idempotentno, ON CONFLICT update).
    M-IDX rupa #1: daily pipeline do sada NIJE ažurirao indekse."""
    from datetime import timedelta
    from .calibrate import fetch_index_history
    date_from = (date.today() - timedelta(days=lookback_days)).isoformat()
    n = 0
    for name, (isin, _slug, _d) in INDICES.items():
        try:
            rows = fetch_index_history(isin, date_from)
        except Exception as e:  # noqa: BLE001
            log(f"  [skip] {name}: {type(e).__name__}: {e}")
            continue
        with conn.cursor() as cur:
            for d, v in rows:
                cur.execute(
                    """INSERT INTO index_eod (index_isin, trade_date, close_value, source)
                       VALUES (%s,%s,%s,%s)
                       ON CONFLICT (index_isin, trade_date)
                       DO UPDATE SET close_value=EXCLUDED.close_value""",
                    (isin, d, v, f"zse.hr indexHistory ({name}, web JSON)"))
        conn.commit()
        n += len(rows)
    return n


def backfill_all(conn, log=print) -> None:
    """Jednokratni backfill povijesti svih indeksa od HISTORY_FROM."""
    from .calibrate import fetch_index_history
    for name, (isin, _slug, _d) in INDICES.items():
        try:
            rows = fetch_index_history(isin, HISTORY_FROM)
        except Exception as e:  # noqa: BLE001
            log(f"  [skip] {name}: {type(e).__name__}: {e}")
            continue
        with conn.cursor() as cur:
            for d, v in rows:
                cur.execute(
                    """INSERT INTO index_eod (index_isin, trade_date, close_value, source)
                       VALUES (%s,%s,%s,%s)
                       ON CONFLICT (index_isin, trade_date)
                       DO UPDATE SET close_value=EXCLUDED.close_value""",
                    (isin, d, v, f"zse.hr indexHistory ({name}, web JSON)"))
        conn.commit()
        log(f"  {name}: {len(rows)} zapisa" + (f" ({rows[0][0]}..{rows[-1][0]})" if rows else ""))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from .db import get_conn
    with get_conn() as conn:
        ensure_tables(conn)
        if "--backfill" in sys.argv:
            backfill_all(conn)
        else:
            print(f"index_eod: +{update_index_eod(conn)} zapisa")
        print(f"sastavnice: {refresh_constituents(conn)} redova")
