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

# M64: kurirani opisi za stranicu fonda (SEO) — ČINJENIČNO prepričani
# ulagateljski ciljevi iz službenog mjesečnog izvještaja/prospekta fonda
# (izvor: EHO objave izdavatelja); bez ocjena i preporuka.
DESCRIPTIONS = {
    "7CRO": {
        "hr": ("Fond pasivno replicira dionički indeks CROBEX10tr — fizički "
               "kupuje dionice u sastavu indeksa (u pravilu 10 najlikvidnijih "
               "dionica Zagrebačke burze). Primljene dividende automatski se "
               "reinvestiraju; fond ne isplaćuje dividendu."),
        "en": ("The fund passively replicates the CROBEX10tr equity index — it "
               "physically buys the index constituents (as a rule the 10 most "
               "liquid stocks on the Zagreb Stock Exchange). Dividends received "
               "are automatically reinvested; the fund pays no dividend."),
    },
    "7SLO": {
        "hr": ("Fond pasivno replicira SBITOP TR, total-return indeks "
               "Ljubljanske burze — fizički drži dionice u sastavu indeksa, a "
               "primljene dividende se reinvestiraju."),
        "en": ("The fund passively replicates SBITOP TR, the total-return index "
               "of the Ljubljana Stock Exchange — it physically holds the index "
               "constituents and reinvests dividends received."),
    },
    "7BET": {
        "hr": ("Fond pasivno replicira BET-TRN, total-return indeks vodećih "
               "dionica Burze u Bukureštu (Rumunjska); dividende se "
               "reinvestiraju."),
        "en": ("The fund passively replicates BET-TRN, the total-return index "
               "of leading Bucharest Stock Exchange (Romania) stocks; dividends "
               "are reinvested."),
    },
    "7POL": {
        "hr": ("Fond pasivno replicira WIG30TR, total-return indeks 30 vodećih "
               "dionica Varšavske burze (Poljska); dividende se reinvestiraju."),
        "en": ("The fund passively replicates WIG30TR, the total-return index "
               "of 30 leading Warsaw Stock Exchange (Poland) stocks; dividends "
               "are reinvested."),
    },
    "7GROM": {
        "hr": ("Aktivno upravljan obveznički fond (ne replicira indeks): ulaže "
               "u obveznice i druge dužničke papire Rumunjske denominirane u "
               "euru, s prosječnim vaganim trajanjem imovine ograničenim na "
               "raspon 5-10 godina."),
        "en": ("An actively managed bond fund (it does not replicate an index): "
               "it invests in euro-denominated Romanian government bonds and "
               "other debt securities, with the weighted average life of assets "
               "kept within a 5-10 year range."),
    },
    "7CASH": {
        "hr": ("Aktivno upravljan novčani fond: ulaže u instrumente tržišta "
               "novca (primarno trezorske zapise RH, Francuske i drugih članica "
               "EU/OECD-a) i depozite, s ciljem prinosa iznad kratkoročnih "
               "stopa tržišta novca uz visoku likvidnost; referentna vrijednost "
               "je €STR indeks ECB-a."),
        "en": ("An actively managed money-market fund: it invests in "
               "money-market instruments (primarily treasury bills of Croatia, "
               "France and other EU/OECD members) and deposits, aiming for "
               "returns above short-term money-market rates with high "
               "liquidity; the benchmark is the ECB's €STR index."),
    },
}


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


# ---- M64: mjesečni factsheet (EHO) -> etf_facts ----
# Prepoznavanje pod-fonda iz naslova objave "… - Mjesečni izvještaj …"
FUND_TOKENS = {
    "7CRO": "CROBEX10", "7SLO": "SBITOP", "7BET": "BET-TRN",
    "7POL": "WIG30", "7GROM": "Romania Govt Bond", "7CASH": "Euro Money Market",
}
HR_MONTHS = {"siječanj": 1, "veljača": 2, "ožujak": 3, "travanj": 4,
             "svibanj": 5, "lipanj": 6, "srpanj": 7, "kolovoz": 8,
             "rujan": 9, "listopad": 10, "studeni": 11, "prosinac": 12}


def ensure_facts_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS etf_facts (
                symbol TEXT PRIMARY KEY REFERENCES etfs(symbol),
                report_period TEXT,      -- 'YYYY-MM' iz naslova izvještaja
                payload JSONB NOT NULL,  -- parse_factsheet izlaz (gateovi prošli)
                source_url TEXT NOT NULL,
                published_at DATE,
                updated_at TIMESTAMPTZ DEFAULT now());
        """)
    conn.commit()


def sync_facts(conn, lookback_days: int = 45, log=print) -> int:
    """Najnoviji 'Mjesečni izvještaj' po pod-fondu s EHO-a -> etf_facts.
    Idempotentno: već obrađen source_url se preskače (bez downloada)."""
    import json as _json
    import re as _re

    import requests

    from . import eho
    from .etf_factsheet import parse_factsheet
    ensure_facts_table(conn)
    d = eho.feed("issuerNews", ticker="ICAM",
                 date_from=(date.today() - timedelta(days=lookback_days)).isoformat(),
                 date_to=date.today().isoformat())
    newest: dict[str, dict] = {}
    for it in d.get("items") or []:      # feed je najnoviji-prvi
        title = it.get("title") or ""
        if "mjese" not in title.lower():
            continue
        for sym, token in FUND_TOKENS.items():
            if token.lower() in title.lower() and sym not in newest:
                newest[sym] = it
    n = 0
    with conn.cursor() as cur:
        for sym, it in sorted(newest.items()):
            link = it.get("link")
            cur.execute("SELECT source_url FROM etf_facts WHERE symbol=%s", (sym,))
            r = cur.fetchone()
            if r and r[0] == link:
                continue      # već obrađeno — mjesečni ritam, ne dnevni posao
            try:
                from .prices import _verify
                page = requests.get(link, timeout=60, verify=_verify()).text
                pdfs = _re.findall(r'href="(/fileadmin/[^"]+\.pdf[^"]*)"', page, _re.I)
                if not pdfs:
                    log(f"  [skip] {sym}: objava bez PDF-a ({link})")
                    continue
                pdf = requests.get("https://eho.zse.hr" + pdfs[0], timeout=90,
                                   verify=_verify()).content
                parsed = parse_factsheet(pdf)
            except Exception as e:  # noqa: BLE001 — jedan fond ne ruši sync
                log(f"  [skip] {sym}: {type(e).__name__}: {e}")
                continue
            if not (parsed.get("fees_pct") or parsed.get("holdings")):
                log(f"  [skip] {sym}: parser nije prošao gateove ({parsed.get('skipped')})")
                continue
            period = None
            m = _re.search(r"(\w+)\s+(20\d\d)", parsed.get("report_period") or "")
            if m and m.group(1).lower() in HR_MONTHS:
                period = f"{m.group(2)}-{HR_MONTHS[m.group(1).lower()]:02d}"
            cur.execute(
                """INSERT INTO etf_facts (symbol, report_period, payload,
                     source_url, published_at)
                   VALUES (%s,%s,%s,%s,%s)
                   ON CONFLICT (symbol) DO UPDATE SET
                     report_period=EXCLUDED.report_period,
                     payload=EXCLUDED.payload, source_url=EXCLUDED.source_url,
                     published_at=EXCLUDED.published_at, updated_at=now()""",
                (sym, period, _json.dumps(parsed, ensure_ascii=False), link,
                 (it.get("publishDate") or "")[:10] or None))
            n += 1
            log(f"  {sym}: factsheet {period} obrađen "
                f"({len(parsed.get('holdings') or [])} pozicija)")
    conn.commit()
    return n


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from .db import get_conn
    with get_conn() as conn:
        print(f"master: {sync_master(conn)} ETF-ova")
        if "--backfill" in sys.argv:
            backfill_history(conn)
        print(f"cijene: +{update_prices(conn)}")
        print(f"factsheeti: +{sync_facts(conn)}")
