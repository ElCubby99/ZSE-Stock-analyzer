"""M15: onboard CIJELOG ZSE dioničkog univerzuma — bez API.

Izvor: službena tečajnica (rest.zse.hr price-list, EQTY klase svih segmenata i
modaliteta) + stranica papira zse.hr/hr/papir (ime izdavatelja iz <title>,
'Uvrštena količina', NACE šifra za grubi sektor). Firme se upisuju kao
'discovered' (is_live=FALSE) -> stranice su market_only dok financije ne
prođu ekstrakciju i promotion gate; NIŠTA se ne izmišlja.

Grupiranje klasa: simbol sa sufiksom '2' čija baza postoji na tečajnici
(npr. ADRS2) ide pod istu firmu kao povlaštena/druga klasa.

Sektor iz NACE (konzervativna mapa; nepoznato -> NULL = 'n/p'), uz
sector_confidence=0.5 (gruba klasifikacija s burze, ne iz izvješća).

Pokretanje:  python -m scripts.onboard_universe
"""
from __future__ import annotations

import datetime
import json
import re
import sys
import urllib.request

sys.path.insert(0, ".")

import requests  # noqa: E402

from src.db import get_conn  # noqa: E402

BASE = "https://rest.zse.hr/web/Bvt9fe2peQ7pwpyYqODM"

# NACE (2-4 znamenke) -> naš sektor; SAMO nedvosmislene grupe
NACE_SECTOR = [
    ("6419", "bank"), ("64.19", "bank"),
    ("6420", "holding"), ("64.20", "holding"),
    ("65", "insurance"),
    ("55", "tourism"),
    ("61", "telecom"),
    ("62", "technology"), ("63", "technology"),
    ("50", "shipping"),
    ("10", "consumer"), ("11", "consumer"), ("12", "consumer"),
    ("46", "consumer"), ("47", "consumer"),
    ("19", "industrial"), ("20", "industrial"), ("22", "industrial"),
    ("23", "industrial"), ("24", "industrial"), ("25", "industrial"),
    ("26", "industrial"), ("27", "industrial"), ("28", "industrial"),
    ("29", "industrial"), ("30", "industrial"), ("33", "industrial"),
    ("35", "industrial"), ("41", "industrial"), ("42", "industrial"),
    ("43", "industrial"), ("52", "industrial"),
]


def _verify():
    import os
    return os.getenv("REQUESTS_CA_BUNDLE") or os.getenv("SSL_CERT_FILE") or True


def fetch_price_list() -> list[dict]:
    today = datetime.date.today()
    for back in range(0, 10):
        d = (today - datetime.timedelta(days=back)).isoformat()
        req = urllib.request.Request(f"{BASE}/price-list/XZAG/{d}/json",
                                     headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.loads(r.read())
        except Exception:  # noqa: BLE001
            continue
        rows = data.get("securities") or []
        if rows:
            print(f"[universe] tečajnica {d}: {len(rows)} papira")
            return rows
    raise RuntimeError("tečajnica nedostupna (10 dana)")


def paper_page(isin: str) -> dict:
    """-> {name, qty, nace, nace_txt} sa zse.hr stranice papira."""
    r = requests.get("https://zse.hr/hr/papir/310", params={"isin": isin},
                     timeout=40, verify=_verify())
    r.raise_for_status()
    out: dict = {"name": None, "qty": None, "nace": None, "nace_txt": None}
    m = re.search(r"<title>\s*[^:<]+:\s*([^<]+?)\s*</title>", r.text)
    if m:
        out["name"] = m.group(1).strip()
    txt = re.sub(r"<[^>]+>", " ", r.text)
    m = re.search(r"Uvrštena\s+količina\s*([\d.]+)", txt)
    if m:
        out["qty"] = int(m.group(1).replace(".", ""))
    m = re.search(r"NACE\s+(\d{2,4})\s*(?:&nbsp;|\s|·)*([^\n<]{0,80})", txt)
    if m:
        out["nace"] = m.group(1)
        out["nace_txt"] = " ".join(m.group(2).split())[:80]
    return out


def sector_of(nace: str | None) -> str | None:
    if not nace:
        return None
    for pref, sec in NACE_SECTOR:
        if nace.startswith(pref.replace(".", "")):
            return sec
    return None


def main() -> int:
    rows = fetch_price_list()
    eq = [s for s in rows if s.get("security_class") == "EQTY"]
    symbols = {s["symbol"] for s in eq}
    new_classes = []
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT isin, ticker FROM share_classes")
        have_isin = {r[0] for r in cur.fetchall()}
        added_c = added_sc = 0
        for s in sorted(eq, key=lambda x: x["symbol"]):
            if s["isin"] in have_isin:
                continue
            sym = s["symbol"]
            basesym = sym[:-1] if (sym.endswith("2") and sym[:-1] in symbols) else sym
            try:
                pp = paper_page(s["isin"])
            except Exception as e:  # noqa: BLE001
                print(f"[universe] {sym}: stranica papira pala ({e}) — preskačem")
                continue
            name = pp["name"] or sym
            # firma: postojeća po baznom simbolu ili nova 'discovered'
            cur.execute("SELECT id FROM companies WHERE ticker=%s", (basesym,))
            r = cur.fetchone()
            if r:
                cid = r[0]
            else:
                sec = sector_of(pp["nace"])
                cur.execute(
                    """INSERT INTO companies (ticker, name, sector, is_group,
                           base_currency, tier, onboarding_status, is_live,
                           sector_confidence)
                       VALUES (%s,%s,%s,FALSE,'EUR',3,'discovered',FALSE,%s)
                       RETURNING id""",
                    (basesym, name, sec, 0.5 if sec else None))
                cid = cur.fetchone()[0]
                added_c += 1
                print(f"[universe] +firma {basesym}: {name[:50]} "
                      f"(NACE {pp['nace']} -> {sec or 'n/p'})")
            ctype = "preferred" if s.get("security_type") == "PREF-SHARE" else "ordinary"
            note = (f"masovni onboard (M15): ISIN i broj dionica sa zse.hr "
                    f"(Uvrštena količina{', NACE ' + pp['nace'] if pp['nace'] else ''}); "
                    f"trezorske NEPOZNATE (0 uz ogradu)")
            cur.execute(
                """INSERT INTO share_classes (company_id, ticker, isin, class_type,
                       shares_issued, treasury_shares, is_primary_line, dividend_note)
                   VALUES (%s,%s,%s,%s,%s,0,%s,%s)
                   ON CONFLICT DO NOTHING""",
                (cid, sym, s["isin"], ctype, pp["qty"], sym == basesym, note))
            added_sc += 1
            new_classes.append(sym)
        conn.commit()
    print(f"[universe] dodano firmi: {added_c}, klasa: {added_sc}")
    print("[universe] nove klase:", " ".join(new_classes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
