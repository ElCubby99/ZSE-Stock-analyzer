"""Točka 2 (extractor): tekst izvješća -> Anthropic API -> validan JSON.

System prompt je doslovno iz specifikacije (docs/koei_extraction_prompt.md).
Model: Opus 4.8. NE radi nikakvu procjenu ni izvođenje brojki — to je posao
validatora/derivacije nizvodno.
"""
from __future__ import annotations

import json
from typing import Any

from . import config

EXTRACTION_SYSTEM_PROMPT = """\
Ti si ekstraktor financijskih podataka. Dobivaš tekst jednog financijskog izvješća
hrvatskog izdavatelja. Vrati ISKLJUČIVO validan JSON po shemi dolje — bez ikakvog
teksta, objašnjenja ili markdown ograda.

ŽELJEZNA PRAVILA:
1. Izvlači SAMO brojke koje su doslovno u dokumentu. Ako stavka ne postoji, stavi
   null i confidence 0. NIKAD ne procjenjuj, ne izvodi i ne "popunjavaj" brojku.
   Izmišljena financijska brojka je gora od nedostajuće.
2. Odredi metapodatke i budi siguran:
   - basis: "consolidated" ili "standalone" (traži "konsolidirano"/"nekonsolidirano")
   - period_type: "annual" | "Q1" | "H1" | "9M"
   - cumulative: jesu li interim brojke kumulativne (YTD)? IFRS interim obično jest.
   - audited: revidirano?
   - currency: "EUR" ili "HRK"
   - reporting_scale: 1 / 1000 / 1000000 — u kojim su jedinicama brojke iskazane.
     Traži oznake "u tisućama EUR", "('000)", "u milijunima". OVO JE ČESTA GREŠKA —
     provjeri zaglavlja tablica, ne pretpostavljaj.
3. Predznak: revenue/expenses/imovina/kapital/dug/cash = pozitivna magnituda.
   Rezultati (ebit, net_financial_result, pretax_income, net_income*) zadrži s
   predznakom kako su iskazani (gubitak = negativan).
4. Za SVAKU stavku navedi source_page (broj stranice ili oznaku bilješke) i
   confidence 0..1 (koliko si siguran u očitanje i mapiranje).
5. Ako naiđeš na "prepravljeno"/"restated"/usporedne brojke za prošlu godinu,
   izvlači SAMO tekući period ovog izvješća. Prošle periode hvataju njihova izvješća.

KANONSKI item ključevi (mapiraj na ove, sve ostalo ignoriraj):
  income:  revenue, other_operating_income, operating_expenses,
           depreciation_amortization, ebit, ebitda, net_financial_result,
           pretax_income, income_tax, net_income, net_income_parent,
           net_income_minority
  balance: total_assets, total_equity, equity_parent, minority_interests,
           debt_short, debt_long, cash_and_equivalents
  cashflow: operating_cf, capex
  shares:  shares_outstanding, treasury_shares
NE izvlači net_debt, total_debt, ebitda(ako nije objavljen), free_cash_flow —
te izračuna kod.

IZLAZNA SHEMA:
{
  "meta": { "company_ticker": "KOEI", "fiscal_year": 2024, "period_type": "annual",
            "basis": "consolidated", "cumulative": false, "audited": true,
            "currency": "EUR", "reporting_scale": 1000 },
  "items": [
    { "statement": "income", "item": "revenue", "value_raw": 1234567,
      "source_page": "str. 12", "confidence": 0.98 }
  ],
  "flags": [ "tekstualni opis svega sumnjivog/dvosmislenog" ]
}
"""


# JSON schema za structured outputs (output_config.format). Jamči da model vrati
# točno ovu strukturu — nema parsiranja slobodnog teksta ni code-fence ograda.
# Ograničenja structured outputs: bez min/max, additionalProperties mora biti false.
_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "statement": {"type": "string", "enum": ["income", "balance", "cashflow", "shares"]},
        "item": {"type": "string"},
        "value_raw": {"anyOf": [{"type": "number"}, {"type": "null"}]},
        "source_page": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["statement", "item", "value_raw", "source_page", "confidence"],
    "additionalProperties": False,
}

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "meta": {
            "type": "object",
            "properties": {
                "company_ticker": {"type": "string"},
                "fiscal_year": {"type": "integer"},
                "period_type": {"type": "string", "enum": ["annual", "Q1", "H1", "9M"]},
                "basis": {"type": "string", "enum": ["consolidated", "standalone"]},
                "cumulative": {"type": "boolean"},
                "audited": {"type": "boolean"},
                "currency": {"type": "string", "enum": ["EUR", "HRK"]},
                "reporting_scale": {"type": "integer", "enum": [1, 1000, 1000000]},
            },
            "required": ["company_ticker", "fiscal_year", "period_type", "basis",
                         "cumulative", "audited", "currency", "reporting_scale"],
            "additionalProperties": False,
        },
        "items": {"type": "array", "items": _ITEM_SCHEMA},
        "flags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["meta", "items", "flags"],
    "additionalProperties": False,
}


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        # ukloni prvu i zadnju ogradu
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def parse_extraction(text: str) -> dict[str, Any]:
    """Parsiraj model output u dict; toleriraj slučajne code-fence ograde."""
    return json.loads(_strip_code_fences(text))


def extract_filing(report_text: str, *, model: str | None = None,
                   max_tokens: int = 16000) -> dict[str, Any]:
    """Pozovi Anthropic API (Opus 4.8) i vrati validiran extraction dict.

    - Structured outputs (output_config.format): model je vezan na EXTRACTION_SCHEMA,
      pa je prvi text blok zajamčeno validan JSON (nema parsiranja slobodnog teksta).
    - Adaptive thinking: ekstrakcija/mapiranje brojki je netrivijalno.
    - Streaming: izvješća su dug input → izbjegava HTTP timeout (get_final_message).

    Zahtijeva ANTHROPIC_API_KEY u okruženju. Za offline/testove koristi
    parse_extraction nad spremljenim JSON-om umjesto ovoga.
    """
    import anthropic  # lazy import da testovi rade bez paketa

    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY nije postavljen.")

    client = anthropic.Anthropic()  # razrješava ANTHROPIC_API_KEY iz okruženja
    with client.messages.stream(
        model=model or config.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=EXTRACTION_SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA}},
        messages=[{"role": "user", "content": report_text}],
    ) as stream:
        resp = stream.get_final_message()

    if resp.stop_reason == "refusal":
        raise RuntimeError(f"Model je odbio zahtjev (refusal): {resp.stop_details}")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError(
            "Izlaz odrezan na max_tokens — JSON je nepotpun. Povećaj max_tokens "
            "ili suzi ulazni tekst na stranice s financijskim izvještajima."
        )

    # output_config.format jamči da je prvi text blok validan JSON po shemi.
    text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), None)
    if text is None:
        raise RuntimeError("Odgovor ne sadrži text blok s JSON-om.")
    return json.loads(text)
