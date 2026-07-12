"""Klasifikacija (M6): sektor firme + kategorija objave. API SAMO za ovo i
za ekstrakciju (spec: nema živog agenta u petlji).

Pravila:
- structured outputs -> zajamčen JSON {vrijednost, confidence, rationale};
- confidence < 0.85 ili dvojba -> pozivatelj šalje u needs_review, NE pretpostavlja;
- model: Haiku (jeftina klasifikacija), override env CLASSIFIER_MODEL.
"""
from __future__ import annotations

import json
import os
from typing import Any

from . import config

CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "claude-haiku-4-5-20251001")

# Sektori koje motor razumije (FINANCIAL_SECTORS + operativni + 'other').
SECTORS = ["bank", "insurance", "holding", "tourism", "consumer", "industrial",
           "energy", "telecom", "technology", "shipping", "aquaculture", "other"]

ANNOUNCEMENT_CATEGORIES = ["financial_report", "dividend", "gsa",
                           "manager_transaction", "buyback", "capital_change", "other"]

MIN_CONFIDENCE = 0.85


def _call(system: str, user: str, schema: dict) -> dict[str, Any]:
    import anthropic

    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY nije postavljen.")
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=CLASSIFIER_MODEL,
        max_tokens=500,
        system=system,
        output_config={"format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": user}],
    )
    text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), None)
    if text is None:
        raise RuntimeError("klasifikator nije vratio JSON")
    return json.loads(text)


SECTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "sector": {"type": "string", "enum": SECTORS},
        "confidence": {"type": "number"},
        "rationale": {"type": "string"},
    },
    "required": ["sector", "confidence", "rationale"],
    "additionalProperties": False,
}

SECTOR_SYSTEM = """\
Klasificiraš SEKTOR izdavatelja sa Zagrebačke burze za potrebe valuacijskog
motora. Dozvoljene vrijednosti i značenje:
- bank (kreditna institucija), insurance (osiguratelj),
- holding (krovno društvo s više različitih biznisa/udjela),
- tourism, consumer (hrana/piće/maloprodaja/FMCG), industrial (proizvodnja,
  strojevi, dijelovi, građenje), energy, telecom, shipping (brodarstvo),
  aquaculture, other.
PRAVILA: sudi ISKLJUČIVO iz danih dokaza (ime, opis, naslovi objava). Ako su
dokazi tanki ili firma jaše na granici dvaju sektora, vrati najbolji izbor s
NISKIM confidenceom (<0.85) i objasni dvojbu u rationale — NE nagađaj visoko.
Confidence je vjerojatnost da je klasifikacija točna za IZBOR extraction
templatea (banka vs industrijski) i valuacijskih metoda.
"""


def classify_sector(ticker: str, name: str, evidence: str) -> dict[str, Any]:
    user = (f"Ticker: {ticker}\nSlužbeno ime: {name}\n"
            f"Dokazi (naslovi objava / opis):\n{evidence}\n")
    return _call(SECTOR_SYSTEM, user, SECTOR_SCHEMA)


ANN_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": ANNOUNCEMENT_CATEGORIES},
        "confidence": {"type": "number"},
    },
    "required": ["category", "confidence"],
    "additionalProperties": False,
}

ANN_SYSTEM = """\
Klasificiraš naslove objava izdavatelja sa ZSE u kategorije:
financial_report (objava financijskog izvještaja), dividend (dividenda/isplata),
gsa (glavna skupština — poziv/odluke), manager_transaction (transakcije
rukovoditelja), buyback (vlastite dionice), capital_change (promjena kapitala,
broj dionica), other. Sudi samo iz naslova; nesigurno -> niži confidence.
"""


def classify_announcement(title: str, issuer: str | None = None) -> dict[str, Any]:
    user = f"Izdavatelj: {issuer or '—'}\nNaslov objave: {title}"
    return _call(ANN_SYSTEM, user, ANN_SCHEMA)
