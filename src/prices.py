"""EOD cijene -> prices_eod (po KLASI: ADRS vs ADRS2). KORAK 2B, dio "cijene".

STANJE IZVORA (ažurirano 2026-07-02, nakon što je zse.hr ušao u allowlist):
  - zse.hr                 -> 200. Stranica "Cijene vrijednosnih papira" puni se s
    /json/TradingPriceList, a "Preuzmi JSON" gumb vodi na SLUŽBENU tečajnicu:
    rest.zse.hr/web/<javni-web-token>/price-list/XZAG/<datum>/json.
    Web token NIJE tajna (ugrađen je u zse.hr za sve posjetitelje) i vraća ga
    TradingPriceList odgovor u polju "RestApi" — odatle ga i čitamo.
  - rest.zse.hr (API s korisničkim ZSE_API_KEY) -> i dalje opcija (zse-rest skeleton).
  - eho.zse.hr             -> nema podatke o cijenama (samo objave).
  - mojedionice.com        -> fallback ako ZSE ponovno postane nedosegljiv.

Modul nudi:
  1. zse-json — dohvat SLUŽBENE EOD tečajnice (vidi gore) za zadane datume i
     upis po KLASI u prices_eod. Uzima samo retke iz knjige naloga (model CT/CTLL);
     BLOCK/OTC transakcije se preskaču. ISIN iz tečajnice se provjerava protiv
     share_classes.isin — nesklad znači krivo mapiranje i redak se NE upisuje.
  2. import-csv — deterministički uvoz EOD zapisa (ručni export/dostava),
     format: class_ticker,trade_date,close_eur[,volume]  (ISO datum).
     Ticker se razrješava preko share_classes (klasa!) pa companies (bez klasa).
  3. zse-rest — skeleton za ZSE REST API čim ZSE_API_KEY postoji u okruženju;
     endpoint/format se konfigurira env varom ZSE_REST_URL jer služeni format
     bez ključa nije provjerljiv. NE pogađamo brojke ni format.

CLI:
  python -m src.prices zse-json ADRS ADRS2 CROS CROS2 --date 2026-07-02
  python -m src.prices import-csv data/prices_eod.csv --source "zse.hr tečajnica (ručno)"
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import date as _date

from .db import get_conn

ZSE_TPL_URL = "https://zse.hr/json/TradingPriceList"
# Zadnja poznata javna REST baza (fallback ako TradingPriceList ne odgovori).
# Ovo je javni "web" token sa zse.hr download gumba, ne korisnički ZSE_API_KEY.
ZSE_WEB_REST_FALLBACK = "https://rest.zse.hr/web/Bvt9fe2peQ7pwpyYqODM/"
ORDERBOOK_MODELS = {"CT", "CTLL"}   # BLOCK/OTC nisu službeni close knjige naloga


def _verify():
    return (os.getenv("ZSE_CA_BUNDLE") or os.getenv("REQUESTS_CA_BUNDLE")
            or os.getenv("SSL_CERT_FILE") or True)


def _rest_base(timeout: int = 40) -> str:
    """Javna REST baza iz zse.hr odgovora (polje RestApi); fallback na poznatu."""
    import requests

    try:
        r = requests.get(
            ZSE_TPL_URL,
            params={"lng": "hr", "market_segment_ids": "RP,RO,RR", "type": "EQTY",
                    "model": "ALL", "date": "", "only_traded": "0"},
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=timeout, verify=_verify(),
        )
        r.raise_for_status()
        base = (r.json() or {}).get("RestApi")
        if base:
            return base
    except Exception as e:  # noqa: BLE001 — dijagnostika pa fallback
        print(f"  [warn] TradingPriceList nedostupan ({e}); koristim poznatu REST bazu",
              file=sys.stderr)
    return ZSE_WEB_REST_FALLBACK


def fetch_zse_json(tickers: list[str], dates: list[str],
                   source: str = "zse.hr sluzbena tecajnica (web REST JSON)") -> int:
    """Službena EOD tečajnica -> prices_eod po klasi. Vraća broj upisanih redaka."""
    import requests

    base = _rest_base()
    n = 0
    with get_conn() as conn:
        cur = conn.cursor()
        for d in dates:
            url = f"{base.rstrip('/')}/price-list/XZAG/{d}/json"
            r = requests.get(url, timeout=60, verify=_verify())
            r.raise_for_status()
            data = r.json()
            eff_date = data.get("date") or d
            by_sym: dict[str, dict] = {}
            for row in data.get("securities") or []:
                if row.get("model") not in ORDERBOOK_MODELS:
                    continue
                sym = row.get("symbol")
                if sym in tickers:
                    if sym in by_sym:
                        print(f"  [warn] {d} {sym}: više order-book redaka, zadržavam prvi",
                              file=sys.stderr)
                        continue
                    by_sym[sym] = row
            for t in tickers:
                row = by_sym.get(t)
                if row is None:
                    print(f"  [skip] {d} {t}: nema retka u tečajnici")
                    continue
                if (row.get("price_currency") or "EUR") != "EUR":
                    print(f"  [skip] {d} {t}: valuta {row.get('price_currency')} != EUR")
                    continue
                close = row.get("close_price")
                if close is None:
                    print(f"  [skip] {d} {t}: nema close_price")
                    continue
                company_id, class_id = _resolve(cur, t)
                if class_id is not None and row.get("isin"):
                    cur.execute("SELECT isin FROM share_classes WHERE id = %s", (class_id,))
                    db_isin = cur.fetchone()[0]
                    if db_isin and db_isin != row["isin"]:
                        print(f"  [SKIP-ISIN] {d} {t}: tečajnica {row['isin']} != baza {db_isin}",
                              file=sys.stderr)
                        continue
                volume = float(row["volume"]) if row.get("volume") not in (None, "") else None
                cur.execute(
                    """
                    INSERT INTO prices_eod (company_id, share_class_id, trade_date,
                                            close_eur, volume, source)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (company_id, trade_date, COALESCE(share_class_id, 0))
                    DO UPDATE SET close_eur = EXCLUDED.close_eur,
                                  volume    = EXCLUDED.volume,
                                  source    = EXCLUDED.source
                    """,
                    (company_id, class_id, eff_date, float(close), volume, source),
                )
                print(f"  {eff_date} {t}: close {float(close):.2f} EUR (vol {volume or 0:.0f})")
                n += 1
    return n


ZSE_HISTORY_URL = "https://zse.hr/json/securityHistory"


def fetch_zse_history(tickers: list[str], date_from: str, date_to: str | None = None,
                      source: str = "zse.hr securityHistory (web JSON)") -> int:
    """Povijesni EOD po KLASI sa službenog zse.hr securityHistory endpointa
    (isti izvor koji puni graf na stranici papira; javni web REST token).
    ISIN se čita iz share_classes — bez ISIN-a klasa se preskače (ne pogađamo).
    Upis: close = last_price_n, volume = volume_n, turnover_eur = turnover_n.
    Retci bez trgovanja (last_price_n null) se NE upisuju."""
    import requests

    rest = _rest_base()
    date_to = date_to or _date.today().isoformat()
    n = 0
    with get_conn() as conn:
        cur = conn.cursor()
        for t in tickers:
            cur.execute("SELECT company_id, id, isin FROM share_classes WHERE ticker=%s", (t,))
            r = cur.fetchone()
            if not r or not r[2]:
                print(f"  [skip] {t}: nema share_classes retka s ISIN-om — dodaj klasu prvo",
                      file=sys.stderr)
                continue
            company_id, class_id, isin = r
            rows = []
            for model in sorted(ORDERBOOK_MODELS):   # CT pa CTLL
                resp = requests.get(
                    f"{ZSE_HISTORY_URL}/{isin}/{date_from}/{date_to}/hr",
                    params={"trading_model_id": model, "restAPI": rest},
                    headers={"X-Requested-With": "XMLHttpRequest"},
                    timeout=90, verify=_verify())
                resp.raise_for_status()
                rows = (resp.json() or {}).get("rows") or []
                if rows:
                    break
            if not rows:
                print(f"  [skip] {t}: securityHistory prazan za {date_from}..{date_to}")
                continue
            written = 0
            for row in rows:
                d = row.get("date_yyyy_MM_dd")
                close = row.get("last_price_n")
                if not d or close in (None, 0):
                    continue    # dan bez trgovanja — nema close, ne izmišljamo
                cur.execute(
                    """
                    INSERT INTO prices_eod (company_id, share_class_id, trade_date,
                                            close_eur, volume, turnover_eur, source)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (company_id, trade_date, COALESCE(share_class_id, 0))
                    DO UPDATE SET close_eur    = EXCLUDED.close_eur,
                                  volume       = EXCLUDED.volume,
                                  turnover_eur = EXCLUDED.turnover_eur,
                                  source       = EXCLUDED.source
                    """,
                    (company_id, class_id, d, float(close), row.get("volume_n"),
                     row.get("turnover_n"), source))
                written += 1
            print(f"  {t}: {written} EOD zapisa ({date_from}..{date_to}, "
                  f"model {rows[0].get('trading_model_id')})")
            n += written
    return n


def _resolve(cur, ticker: str) -> tuple[int, int | None]:
    """ticker (klasa ili firma) -> (company_id, share_class_id|None)."""
    cur.execute("SELECT company_id, id FROM share_classes WHERE ticker = %s", (ticker,))
    r = cur.fetchone()
    if r:
        return r[0], r[1]
    cur.execute("SELECT id FROM companies WHERE ticker = %s", (ticker,))
    r = cur.fetchone()
    if not r:
        raise ValueError(f"nepoznat ticker (ni klasa ni firma): {ticker}")
    return r[0], None


def import_csv(path: str, source: str) -> int:
    n = 0
    with get_conn() as conn, open(path, newline="", encoding="utf-8") as f:
        cur = conn.cursor()
        for row in csv.DictReader(f):
            company_id, class_id = _resolve(cur, row["class_ticker"].strip())
            cur.execute(
                """
                INSERT INTO prices_eod (company_id, share_class_id, trade_date,
                                        close_eur, volume, source)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (company_id, trade_date, COALESCE(share_class_id, 0))
                DO UPDATE SET close_eur = EXCLUDED.close_eur,
                              volume    = EXCLUDED.volume,
                              source    = EXCLUDED.source
                """,
                (company_id, class_id, row["trade_date"].strip(),
                 float(row["close_eur"]), float(row["volume"]) if row.get("volume") else None,
                 source),
            )
            n += 1
    return n


def fetch_zse_rest(tickers: list[str]) -> int:
    key = os.getenv("ZSE_API_KEY")
    if not key:
        raise SystemExit(
            "ZSE_API_KEY nije postavljen — rest.zse.hr vraća 401 bez ključa.\n"
            "Postavi ZSE_API_KEY (i ZSE_REST_URL predložak) pa pokušaj ponovno."
        )
    raise SystemExit(
        "zse-rest dohvat još nije umrežen: format odgovora rest.zse.hr nije "
        "provjerljiv bez ključa pa ga ne pogađamo. Uz postavljen ZSE_API_KEY "
        "javi format (ili daj primjer odgovora) i ovdje se dovrši parser."
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="EOD cijene -> prices_eod")
    sub = p.add_subparsers(dest="cmd", required=True)

    pz = sub.add_parser("zse-json", help="službena EOD tečajnica (javni web REST JSON) -> prices_eod")
    pz.add_argument("tickers", nargs="+", help="tickere KLASA (ADRS ADRS2 CROS CROS2 ...)")
    pz.add_argument("--date", dest="dates", action="append", default=None,
                    help="YYYY-MM-DD, može više puta; default: danas")
    pz.add_argument("--source", default="zse.hr sluzbena tecajnica (web REST JSON)")

    ph = sub.add_parser("zse-history", help="povijesni EOD (zse.hr securityHistory) -> prices_eod")
    ph.add_argument("tickers", nargs="+", help="tickere KLASA (ADRS ADRS2 ...)")
    ph.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD")
    ph.add_argument("--to", dest="date_to", default=None, help="YYYY-MM-DD; default danas")

    pc = sub.add_parser("import-csv", help="uvoz iz CSV-a (class_ticker,trade_date,close_eur[,volume])")
    pc.add_argument("csv_path")
    pc.add_argument("--source", required=True, help="opis izvora zapisa (audit trail)")

    pr = sub.add_parser("zse-rest", help="dohvat s rest.zse.hr (traži ZSE_API_KEY)")
    pr.add_argument("tickers", nargs="+")

    a = p.parse_args(argv)
    if a.cmd == "zse-json":
        dates = a.dates or [_date.today().isoformat()]
        n = fetch_zse_json(a.tickers, dates, source=a.source)
        print(f"Upisano/ažurirano {n} EOD zapisa ({', '.join(dates)})")
    elif a.cmd == "zse-history":
        n = fetch_zse_history(a.tickers, a.date_from, a.date_to)
        print(f"Upisano/ažurirano {n} povijesnih EOD zapisa")
    elif a.cmd == "import-csv":
        n = import_csv(a.csv_path, a.source)
        print(f"Upisano/ažurirano {n} EOD zapisa iz {a.csv_path}")
    else:
        fetch_zse_rest(a.tickers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
