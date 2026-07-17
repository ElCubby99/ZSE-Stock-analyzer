"""M-FOND: mirovinski fondovi (OMF) — vrijednosti obračunskih jedinica i
Mirex, izvor HANFA (javne objave, MJESEČNI ritam — zaseban workflow, ne
dio dnevnog EOD-a).

VAŽNO o okruženju: hanfa.hr NIJE na mrežnoj allowlisti Claude Code
okruženja, pa se dohvat ovdje ne može testirati — fetch_hanfa() je pisan
za GitHub Actions runner (otvorena mreža). Parser je STROG: na nepoznat
format baca grešku s uputom (workflow tada otvara issue) — radije pad s
razlogom nego kriva brojka ("ništa izmišljeno"). CLI podržava i ručni
uvoz datoteke (--import-file) za prvi run / popravak formata.

Matching OMF-ova u shareholders tablici (dokumentirana pravila, koristi ih
build_fondovi.py):
  1. odbaci custodian prefiks (tekst prije zadnjeg '/')
  2. normaliziraj (velika slova, ligature ﬀ->FF, dijakritici)
  3. obitelj: 'AZ' | 'ERSTE PLAVI' | 'PBZ CO'/'PBZ CROATIA OSIGURANJE' |
     'RAIFFEISEN'; mora sadržavati 'OMF' ili 'OBVEZNI MIROVINSKI'
     (dobrovoljni fondovi se NE broje u OMF prikaz)
  4. kategorija: 'KATEGORIJ(A|E) A/B/C'
"""
from __future__ import annotations

import re
import unicodedata

FUNDS = ["AZ", "Erste Plavi", "PBZ CO", "Raiffeisen"]
CATEGORIES = ["A", "B", "C"]


def ensure_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fund_units (
                fund TEXT NOT NULL,        -- AZ | Erste Plavi | PBZ CO | Raiffeisen
                category TEXT NOT NULL,    -- A | B | C
                value_date DATE NOT NULL,
                unit_value NUMERIC NOT NULL,
                source TEXT,
                PRIMARY KEY (fund, category, value_date));
            CREATE TABLE IF NOT EXISTS mirex (
                category TEXT NOT NULL,    -- A | B | C (Mirex indeksi po kategoriji)
                value_date DATE NOT NULL,
                value NUMERIC NOT NULL,
                source TEXT,
                PRIMARY KEY (category, value_date));
        """)
    conn.commit()


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.upper().strip()


def match_omf(holder_name: str) -> tuple[str, str] | None:
    """(obitelj, kategorija) iz naziva dioničara ili None (dokumentirana
    pravila u docstringu modula). Dobrovoljni fondovi -> None."""
    n = _norm(holder_name.split("/")[-1])
    if "OMF" not in n and "OBVEZNI MIROVINSKI" not in n:
        return None
    fam = None
    if re.search(r"\bAZ\b", n):
        fam = "AZ"
    elif "ERSTE PLAVI" in n:
        fam = "Erste Plavi"
    elif "PBZ CO" in n or "PBZ CROATIA OSIGURANJE" in n:
        fam = "PBZ CO"
    elif "RAIFFEISEN" in n:
        fam = "Raiffeisen"
    if not fam:
        return None
    m = re.search(r"KATEGORIJ[AE]\s*([ABC])\b", n)
    return (fam, m.group(1) if m else "B")  # bez oznake: B je najveća/default


def import_rows(conn, rows: list[dict], source: str) -> int:
    """Idempotentan upis [{fund, category, value_date, unit_value}] — ponovni
    run s istim podacima ne mijenja ništa (ON CONFLICT DO NOTHING)."""
    ensure_tables(conn)
    n = 0
    with conn.cursor() as cur:
        for r in rows:
            cur.execute(
                """INSERT INTO fund_units (fund, category, value_date, unit_value, source)
                   VALUES (%s,%s,%s,%s,%s)
                   ON CONFLICT (fund, category, value_date) DO NOTHING""",
                (r["fund"], r["category"], r["value_date"], r["unit_value"], source))
            n += cur.rowcount
    conn.commit()
    return n


def fetch_hanfa(conn, log=print) -> int:
    """Dohvat zadnjih objavljenih vrijednosti jedinica s HANFA-e.
    Pokreće se iz MJESEČNOG workflowa (GitHub Actions — otvorena mreža).
    STROG parser redova (nikad kriva brojka), ali TOLERANTAN prema
    strukturi stranice: HANFA datoteke poslužuje kroz /getfile/?fileId=N
    (bez .xlsx u URL-u; prvi run 17.07.2026. pao na 404 stare putanje i
    krivom href obrascu). Kandidati se probaju redom dok jedan ne prođe
    parser; nijedan -> RuntimeError s razlogom.
    Vraća broj NOVIH zapisa (0 = nema novih objava, idempotentno)."""
    import requests
    listings = (
        "https://www.hanfa.hr/statistika/mirovinski-fondovi/",
        "https://www.hanfa.hr/statistika/",
    )
    html, listing = None, None
    for cand_listing in listings:
        try:
            r = requests.get(cand_listing, timeout=90,
                             headers={"User-Agent": "Mozilla/5.0 (podaci; burzovnilist.com)"})
            r.raise_for_status()
            html, listing = r.text, cand_listing
            break
        except Exception as e:  # noqa: BLE001 — probaj sljedeći listing
            log(f"[hanfa] {cand_listing}: {type(e).__name__}: {e}")
    if html is None:
        raise RuntimeError(
            "HANFA: nijedna listing stranica nije dostupna "
            f"({', '.join(listings)}) — provjeri strukturu sajta")
    # <a href="..."> čiji href ILI tekst upućuje na statistiku mirovinskih
    # fondova; datoteke su .xlsx ILI /getfile/?fileId=N
    cands = []
    for m in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.I | re.S):
        href, text = m.group(1), re.sub(r"<[^>]+>", " ", m.group(2))
        if not re.search(r"\.xlsx|/getfile/", href, re.I):
            continue
        blob = f"{href} {text}"
        if re.search(r"mirovin|omf|mirex|obra[čc]unsk", blob, re.I):
            cands.append(href if href.startswith("http")
                         else f"https://www.hanfa.hr{href}")
    if not cands:
        raise RuntimeError(
            f"HANFA: nijedna XLSX/getfile poveznica s 'mirovin' na {listing} "
            "— provjeri strukturu stranice i prilagodi fetch_hanfa()")
    errors = []
    for url in cands[:6]:
        try:
            raw = requests.get(url, timeout=120).content
            if not raw.startswith(b"PK"):     # XLSX = zip; sve drugo preskoči
                errors.append(f"{url}: nije XLSX (magic bytes)")
                continue
            rows = parse_hanfa_xlsx(raw)
            log(f"[hanfa] parsirano {len(rows)} redova iz {url}")
            return import_rows(conn, rows, f"HANFA statistika ({url})")
        except Exception as e:  # noqa: BLE001 — probaj sljedeći kandidat
            errors.append(f"{url}: {type(e).__name__}: {str(e)[:120]}")
    raise RuntimeError(
        "HANFA: nijedan od kandidata nije prošao strogi parser:\n  "
        + "\n  ".join(errors))


def parse_hanfa_xlsx(raw: bytes) -> list[dict]:
    """Parsiranje HANFA XLSX-a s vrijednostima jedinica OMF-ova. STROGO:
    očekuje stupce s nazivom fonda (AZ/Erste Plavi/PBZ CO/Raiffeisen),
    kategorijom i vrijednošću jedinice; sve drugo -> RuntimeError."""
    import io
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    out = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) if c is not None else "" for c in row]
            joined = " ".join(cells)
            m = match_omf(joined)
            if not m:
                continue
            # heuristika: prvi datum + prva decimalna vrijednost u retku
            import datetime as dt
            date_v = next((c for c in row if isinstance(c, dt.datetime | dt.date)), None)
            num_v = next((c for c in row if isinstance(c, int | float) and 1 < float(c) < 10000), None)
            if date_v is None or num_v is None:
                continue
            out.append({"fund": m[0], "category": m[1],
                        "value_date": date_v.date() if hasattr(date_v, "date") else date_v,
                        "unit_value": float(num_v)})
    if not out:
        raise RuntimeError(
            "HANFA XLSX: nijedan red nije prepoznat kao OMF jedinica — format "
            "se promijenio ili je datoteka kriva; prilagodi parse_hanfa_xlsx()")
    return out


if __name__ == "__main__":
    import argparse
    import sys
    sys.path.insert(0, ".")
    from .db import get_conn
    ap = argparse.ArgumentParser()
    ap.add_argument("--import-file", help="ručni uvoz HANFA XLSX datoteke")
    a = ap.parse_args()
    with get_conn() as conn:
        ensure_tables(conn)
        if a.import_file:
            rows = parse_hanfa_xlsx(open(a.import_file, "rb").read())
            print(f"novo: {import_rows(conn, rows, f'HANFA XLSX (ručni uvoz: {a.import_file})')}")
        else:
            print(f"novo: {fetch_hanfa(conn)}")
