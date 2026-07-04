"""Automatsko lociranje financijskih izvještaja u PDF tekstu (M6).

Deterministična heuristika (bez API-ja): nađi stranice s naslovima
konsolidiranih primarnih izvještaja / GFI obrazaca + stranice s brojem
dionica; vrati listu stranica (1-based) za slice. Ako se ništa ne nađe,
pozivatelj šalje firmu u needs_review (NE nagađa se raspon).
"""
from __future__ import annotations

import re

STATEMENT_RX = re.compile(
    r"^\s*(KONSOLIDIRANI\s+(I\s+NEKONSOLIDIRANI\s+)?)?(IZVJEŠTAJ|RAČUN)\s+"
    r"(O\s+)?(SVEOBUHVATNOJ\s+DOBITI|FINANCIJSKOM\s+POLOŽAJU|DOBITI\s+I\s+GUBITKA"
    r"|NOVČAN\w+\s+TOK\w*|NOVČANIM\s+TOKOVIMA|PROMJENAMA\s+(KAPITALA|GLAVNICE))",
    re.I | re.M)
GFI_RX = re.compile(r"\bBILANCA\b|\bGFI-IZD|\bGFI-POD|RAČUN DOBITI I GUBITKA", re.M)
SHARES_RX = re.compile(r"podijeljen\w?\s+(je\s+)?(na\s+)?[\d.,]{5,}\s+.{0,25}dionic"
                       r"|[Bb]roj\s+dionica\s+na\s+dan", re.S)
SMALL_DOC_PAGES = 40          # mali dokument (GFI set) -> uzmi cijeli
NEIGHBOR = 1                  # susjedne stranice oko pogodaka
MAX_CHARS = 120_000           # sigurnosni limit ulaza u ekstrakciju


def split_pages(pdf_text: str) -> list[tuple[int, str]]:
    parts = re.split(r"===== STRANICA (\d+) =====", pdf_text)
    return [(int(parts[i]), parts[i + 1]) for i in range(1, len(parts), 2)]


def locate_statement_pages(pdf_text: str) -> tuple[list[int], str]:
    """-> (stranice za slice, dijagnostika). Prazna lista = nije locirano."""
    pages = split_pages(pdf_text)
    n = len(pages)
    if n == 0:
        return [], "prazan tekst"
    if n <= SMALL_DOC_PAGES:
        return [p for p, _ in pages], f"mali dokument ({n} str) -> cijeli"

    hits, share_hits = [], []
    for num, body in pages:
        if STATEMENT_RX.search(body) or GFI_RX.search(body):
            hits.append(num)
        if SHARES_RX.search(body):
            share_hits.append(num)
    if not hits:
        return [], f"nema pogodaka naslova izvještaja u {n} str"

    wanted = set()
    for h in hits:
        for d in range(-NEIGHBOR, NEIGHBOR + 1):
            if 1 <= h + d <= n:
                wanted.add(h + d)
    wanted.update(share_hits[:4])
    return sorted(wanted), f"pogoci: {hits[:12]}{'...' if len(hits) > 12 else ''}; dionice: {share_hits[:4]}"


def build_slice(pdf_text: str) -> tuple[str, list[int], str]:
    """-> (slice tekst, stranice, dijagnostika). Prazan tekst ako nije locirano."""
    pages_wanted, diag = locate_statement_pages(pdf_text)
    if not pages_wanted:
        return "", [], diag
    keep = set(pages_wanted)
    out = []
    for num, body in split_pages(pdf_text):
        if num in keep:
            out.append(f"\n===== STRANICA {num} =====\n{body}")
    text = "".join(out)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]
        diag += f"; ODREZANO na {MAX_CHARS} znakova"
    return text, pages_wanted, diag
