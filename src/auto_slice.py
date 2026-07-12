"""Automatsko lociranje financijskih izvještaja u PDF tekstu (M6).

Deterministična heuristika (bez API-ja): nađi stranice s naslovima
konsolidiranih primarnih izvještaja / GFI obrazaca + stranice s brojem
dionica; vrati listu stranica (1-based) za slice. Ako se ništa ne nađe,
pozivatelj šalje firmu u needs_review (NE nagađa se raspon).
"""
from __future__ import annotations

import re

STATEMENT_RX = re.compile(
    r"^\s*((ODVOJENI|NEKONSOLIDIRANI)\s+I\s+)?(KONSOLIDIRANI\s+(I\s+NEKONSOLIDIRANI\s+)?)?"
    r"(IZVJEŠTAJ|RAČUN)\s+"
    r"(O\s+)?(SVEOBUHVATNOJ\s+DOBITI|FINANCIJSKOM\s+POLOŽAJU|DOBITI\s+I\s+GUBITKA"
    r"|NOVČAN\w+\s+TOK\w*|NOVČANIM\s+TOKOVIMA|PROMJENAMA\s+(KAPITALA|GLAVNICE))",
    re.I | re.M)
# fallback kad naslovi ne pogode (razni layouti): stranice sa >=2 potpisne
# stavke primarnih tablica su gotovo sigurno stranice izvještaja
CONTENT_SIGNS = ("Ukupna imovina", "Ukupno imovina", "UKUPNO IMOVINA",
                 "Ukupna sveobuhvatna dobit", "Novac i novčani ekvivalenti",
                 "Zadržana dobit", "Ukupne obveze", "Dobit prije oporezivanja",
                 "Temeljni kapital")
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

    hits, share_hits, content_pages = [], [], []
    for num, body in pages:
        if STATEMENT_RX.search(body) or GFI_RX.search(body):
            hits.append(num)
        if SHARES_RX.search(body):
            share_hits.append(num)
        if sum(1 for s in CONTENT_SIGNS if s in body) >= 2:
            content_pages.append(num)
    used_fallback = False
    if not hits:
        hits = list(content_pages)      # fallback kad naslovi ne pogode
        used_fallback = True
    if not hits:
        return [], f"nema pogodaka naslova NI sadržaja izvještaja u {n} str"

    wanted = set()
    for h in hits:
        for d in range(-NEIGHBOR, NEIGHBOR + 1):
            if 1 <= h + d <= n:
                wanted.add(h + d)
    # UNIJA s content stranicama (capano) — naslovi znaju promašiti dio tablica
    # (npr. P&L bez naslovnog retka), potpisne stavke ih vraćaju u slice
    wanted.update(content_pages[:15])
    wanted.update(share_hits[:4])
    diag = (f"pogoci{' (content-fallback)' if used_fallback else ''}: "
            f"{hits[:12]}{'...' if len(hits) > 12 else ''}; "
            f"content: {content_pages[:8]}; dionice: {share_hits[:4]}")
    return sorted(wanted), diag


FLOW_STATEMENT_RX = re.compile(
    r"(KONSOLIDIRANI\s+)?(IZVJEŠTAJ|RAČUN)\s+(O\s+)?(SVEOBUHVATNOJ\s+DOBITI"
    r"|FINANCIJSKOM\s+POLOŽAJU|DOBITI\s+I\s+GUBITKA|NOVČAN\w+\s+TOK\w*"
    r"|NOVČANIM\s+TOKOVIMA)", re.I)
FLOW_SHARES_RX = re.compile(
    r"podijeljen\w?\s+(je\s+)?(na\s+)?[\d.,]{5,}\s+.{0,25}dionic"
    r"|[Bb]roj\s+dionica\s+na\s+dan|[Tt]emeljni\s+kapital", re.S)
WINDOW = 14_000


def build_slice_chars(text: str, extra_note: str = "") -> tuple[str, list[int], str]:
    """Slice za tekst BEZ oznaka stranica (ESEF xhtml): prozori oko pogodaka
    naslova izvještaja + POTPISNIH stavki tablica + bilješke o dionicama."""
    hits = [m.start() for m in FLOW_STATEMENT_RX.finditer(text)]
    for s in CONTENT_SIGNS:            # unija s potpisnim stavkama (kao PDF ruta)
        hits.extend(m.start() for m in re.finditer(re.escape(s), text))
    hits = sorted(hits)[:60]
    sh = [m.start() for m in FLOW_SHARES_RX.finditer(text)][:6]
    if not hits:
        return "", [], "nema pogodaka naslova izvještaja u tekstu"
    # grupiraj bliske pogotke u prozore
    spans: list[list[int]] = []
    for p in sorted(hits + sh):
        a, b = max(0, p - WINDOW // 4), min(len(text), p + WINDOW)
        if spans and a <= spans[-1][1]:
            spans[-1][1] = max(spans[-1][1], b)
        else:
            spans.append([a, b])
    hdr = ("[NAPOMENA EKSTRAKTORU: isječci iz ESEF (xhtml) godišnjeg izvješća; "
           "brojevi stranica su u podnožjima teksta — njih citiraj kao "
           f"source_page. {extra_note}]\n\n")
    out = hdr + "\n\n===== NOVI ISJEČAK =====\n".join(
        text[a:b] for a, b in spans)
    diag = f"{len(hits)} naslova, {len(sh)} kapital-pogodaka, {len(spans)} prozora"
    if len(out) > MAX_CHARS:
        out = out[:MAX_CHARS]
        diag += f"; ODREZANO na {MAX_CHARS}"
    return out, [a for a, _ in spans], diag


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
