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
                   max_tokens: int = 8000) -> dict[str, Any]:
    """Pozovi Anthropic API i vrati parsiran extraction dict.

    Zahtijeva ANTHROPIC_API_KEY u okruženju. Za offline/testove koristi
    parse_extraction nad spremljenim JSON-om umjesto ovoga.
    """
    import anthropic  # lazy import da testovi rade bez paketa

    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY nije postavljen.")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=model or config.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": report_text}],
    )
    text = "".join(
        block.text for block in resp.content if getattr(block, "type", None) == "text"
    )
    return parse_extraction(text)
