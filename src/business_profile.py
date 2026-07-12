"""Profil poslovanja (M9) — kratki ČINJENIČNI opis firme IZ IZVJEŠĆA.

PRAVILA (zahtjev):
- samo činjenice iz izvora, svaka sa source_page;
- epiteti ("lider", "jak brend") se NE generiraju — smiju ući JEDINO ako ih
  izdavatelj sam tvrdi u izvješću, i tada se spremaju ODVOJENO u issuer_claims
  s citatom (frontend ih označava kao tvrdnju izdavatelja);
- bez izvora -> polje ostaje null/prazno, ništa se ne izmišlja;
- MAR: opis djelatnosti i brojke DA; investicijska teza/preporuka NE.

Dvije rute punjenja:
  1. --extract  : API ekstrakcija (claude, structured output) iz početka
                  godišnjeg izvješća (izvještaj uprave / opis poslovanja).
  2. --load-json: deterministički upis ručno pripremljenog JSON-a s citatima
                  (verified-seed politika; koristi se i kad je API nedostupan).

CLI:
  python -m src.business_profile ADRS                 # ispiši iz baze
  python -m src.business_profile ADRS --extract       # API ekstrakcija + upis
  python -m src.business_profile ADRS --load-json f.json --source "opis izvora"
"""
from __future__ import annotations

import argparse
import json
import sys

from .db import get_conn

PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "fiscal_year": {"type": "integer"},
        "activity": {
            "type": ["string", "null"],
            "description": "djelatnost, 1-2 rečenice, ČINJENIČNO (bez epiteta)",
        },
        "activity_source_page": {"type": ["string", "null"]},
        "segments": {
            "type": "array",
            "items": {"type": "object", "properties": {
                "name": {"type": "string"},
                "description": {"type": ["string", "null"]},
                "source_page": {"type": ["string", "null"]},
            }, "required": ["name"], "additionalProperties": False},
        },
        "markets": {
            "type": "array",
            "items": {"type": "object", "properties": {
                "market": {"type": "string"},
                "source_page": {"type": ["string", "null"]},
            }, "required": ["market"], "additionalProperties": False},
        },
        "export_share": {
            "type": ["object", "null"],
            "properties": {
                "value": {"type": "number",
                          "description": "udio izvoza/inozemnih prihoda, decimalni razlomak"},
                "basis": {"type": "string",
                          "description": "na što se udio odnosi (prihodi grupe, segment...)"},
                "source_page": {"type": ["string", "null"]},
            },
            "required": ["value", "basis"], "additionalProperties": False,
        },
        "issuer_claims": {
            "type": "array",
            "description": "epiteti/kvalitativne tvrdnje IZDAVATELJA (npr. 'vodeći...'), "
                           "doslovno ili parafrazirano, UVIJEK s citatom stranice",
            "items": {"type": "object", "properties": {
                "claim": {"type": "string"},
                "source_page": {"type": ["string", "null"]},
            }, "required": ["claim"], "additionalProperties": False},
        },
    },
    "required": ["fiscal_year", "activity", "segments", "markets",
                 "export_share", "issuer_claims"],
    "additionalProperties": False,
}

PROFILE_SYSTEM = """\
Izvlačiš PROFIL POSLOVANJA izdavatelja iz isječaka godišnjeg izvješća
(izvještaj uprave / opis poslovanja), na hrvatskom.

STROGA PRAVILA:
1. SAMO činjenice koje doslovno stoje u tekstu; svaka sa source_page
   (broj stranice iz oznaka '===== STRANICA N =====' ili podnožja).
2. 'activity': 1-2 rečenice o djelatnosti — NEUTRALNO, bez epiteta i ocjena.
3. Epitete i kvalitativne tvrdnje ('vodeći', 'najveći', 'jak brend') NE
   uklapaj u activity/segments — ako ih IZDAVATELJ tvrdi, stavi ih ODVOJENO
   u issuer_claims s citatom. Ako ih nema u tekstu, issuer_claims je prazan.
4. export_share SAMO ako je udio izvoza / inozemnih prihoda IZRIJEKOM
   objavljen (broj + na što se odnosi); inače null. NE računaj ga sam.
5. Nema podatka -> null / prazna lista. NIŠTA ne izmišljaj i ne nadopunjuj
   općim znanjem o firmi.
6. Bez investicijskih teza, preporuka i procjena vrijednosti.
"""


def extract_profile(slice_text: str, max_tokens: int = 4000) -> dict:
    import anthropic

    from . import config
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY nije postavljen.")
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=PROFILE_SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": PROFILE_SCHEMA}},
        messages=[{"role": "user", "content": slice_text}],
    )
    text = next((b.text for b in resp.content
                 if getattr(b, "type", None) == "text"), None)
    if text is None:
        raise RuntimeError("ekstraktor profila nije vratio JSON")
    return json.loads(text)


def build_profile_slice(pdf_path: str, max_chars: int = 90_000) -> str:
    """Isječak za profil: POČETAK godišnjeg izvješća (izvještaj uprave, opis
    poslovanja) — deterministički, bez pogađanja rasporeda."""
    from .pdf_extract import pdf_to_text
    text = pdf_to_text(pdf_path)
    return text[:max_chars]


def load_profile(conn, ticker: str, p: dict, source: str) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM companies WHERE ticker=%s", (ticker,))
        r = cur.fetchone()
        if not r:
            raise ValueError(f"nepoznat ticker: {ticker}")
        cid = r[0]
        cur.execute(
            """INSERT INTO business_profiles (company_id, fiscal_year, activity,
                 activity_source_page, segments, markets, export_share,
                 issuer_claims, source)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (company_id) DO UPDATE SET
                 fiscal_year=EXCLUDED.fiscal_year, activity=EXCLUDED.activity,
                 activity_source_page=EXCLUDED.activity_source_page,
                 segments=EXCLUDED.segments, markets=EXCLUDED.markets,
                 export_share=EXCLUDED.export_share,
                 issuer_claims=EXCLUDED.issuer_claims,
                 source=EXCLUDED.source, extracted_at=now()""",
            (cid, p.get("fiscal_year"), p.get("activity"),
             p.get("activity_source_page"),
             json.dumps(p.get("segments") or [], ensure_ascii=False),
             json.dumps(p.get("markets") or [], ensure_ascii=False),
             (json.dumps(p["export_share"], ensure_ascii=False)
              if p.get("export_share") else None),
             json.dumps(p.get("issuer_claims") or [], ensure_ascii=False),
             source))
    conn.commit()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="profil poslovanja iz izvješća")
    ap.add_argument("ticker")
    ap.add_argument("--extract", action="store_true",
                    help="API ekstrakcija iz PDF-a (--pdf)")
    ap.add_argument("--pdf", default=None, help="put do godišnjeg izvješća")
    ap.add_argument("--load-json", default=None,
                    help="upiši ručno pripremljen JSON s citatima")
    ap.add_argument("--source", default=None,
                    help="opis izvora (dokument + metoda); obavezno uz --load-json")
    a = ap.parse_args(argv)
    t = a.ticker.upper()

    with get_conn() as conn:
        if a.extract:
            if not a.pdf:
                print("--extract traži --pdf put do izvješća"); return 1
            p = extract_profile(build_profile_slice(a.pdf))
            load_profile(conn, t, p,
                         source=f"API ekstrakcija ({a.pdf}, početak izvješća)")
            print(f"{t}: profil ekstrahiran i upisan")
        elif a.load_json:
            if not a.source:
                print("--load-json traži --source opis izvora"); return 1
            with open(a.load_json, encoding="utf-8") as f:
                p = json.load(f)
            load_profile(conn, t, p, source=a.source)
            print(f"{t}: profil upisan iz {a.load_json}")
        with conn.cursor() as cur:
            cur.execute(
                """SELECT bp.fiscal_year, bp.activity, bp.activity_source_page,
                          bp.segments, bp.markets, bp.export_share,
                          bp.issuer_claims, bp.source
                   FROM business_profiles bp JOIN companies c ON c.id=bp.company_id
                   WHERE c.ticker=%s""", (t,))
            r = cur.fetchone()
        if not r:
            print(f"{t}: nema profila u bazi"); return 0
        print(json.dumps({"fiscal_year": r[0], "activity": r[1],
                          "activity_source_page": r[2], "segments": r[3],
                          "markets": r[4], "export_share": r[5],
                          "issuer_claims": r[6], "source": r[7]},
                         ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
