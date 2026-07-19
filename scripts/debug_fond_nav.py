#!/usr/bin/env python3
"""M-FOND5 (opcija C) — IZVIĐAČKA SKRIPTA ZA BORISOVO RAČUNALO (HR mreža).

Stranice mirovinskih društava blokiraju strane datacentre (GitHub/Azure
runneri: Erste DNS fail, PBZ CO timeout), ali s hrvatske mreže rade.
Pokreni LOKALNO:

    pip install requests
    python scripts/debug_fond_nav.py > nav_dump.txt

pa pošalji nav_dump.txt u Claude sesiju — iz njega se pišu STROGI parseri
za automatski mjesečni dohvat NAV-a po fondu. Do tada: ručni unos kroz
Actions workflow 'nav-unos'. Skripta NIŠTA ne mijenja — samo čita i
ispisuje: poveznice na izvještaje/dokumente, isječke teksta oko 'neto
imovina' s brojkama, tablice i PDF/XLSX poveznice.
"""
import re
import sys

import requests

SITES = {
    "AZ": "https://www.azfond.hr",
    "Erste Plavi": "https://www.erste-plavi.hr",
    "PBZ CO": "https://www.pbzco-fond.hr",
    "Raiffeisen": "https://www.rmf.hr",
}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "hr-HR,hr;q=0.9,en;q=0.8"}
KEY = re.compile(r"omf|kategorij|mjese[cč]|izvje[sš]|neto|imovin|dokument|objav|fond", re.I)
NAV_TXT = re.compile(r"neto\s+imovin", re.I)


def _fetch(url, timeout=45):
    r = requests.get(url, timeout=timeout, headers=UA)
    r.raise_for_status()
    return r.text


def _dump(url):
    try:
        html = _fetch(url)
    except Exception as e:  # noqa: BLE001
        print(f"  {url}: GREŠKA {type(e).__name__}: {str(e)[:110]}")
        return None
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.I | re.S)
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))
    print(f"  --- {url} (len {len(plain)}) ---")
    for m in NAV_TXT.finditer(plain):
        s = plain[max(0, m.start() - 70):m.start() + 220]
        if re.search(r"\d", s):
            print(f"    KONTEKST: ...{s}...")
    for i, tm in enumerate(re.finditer(r"<table.*?</table>", html, re.I | re.S)):
        if i >= 3:
            break
        rows = re.findall(r"<tr.*?</tr>", tm.group(0), re.I | re.S)
        print(f"    TABLICA {i + 1} ({len(rows)} redova):")
        for r_ in rows[:8]:
            cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()[:36]
                     for c in re.findall(r"<t[dh].*?</t[dh]>", r_, re.I | re.S)]
            print("     |", " | ".join(cells[:8]))
    for m in re.finditer(r'href="([^"]+\.(?:pdf|xlsx?))"', html, re.I):
        if re.search(r"mjese|izvje|neto|imovin|nav|report", m.group(1), re.I):
            print(f"    FILE: {m.group(1)[:160]}")
    return html


def main() -> int:
    for fund, base in SITES.items():
        print(f"\n########## {fund} — {base} ##########")
        html = _dump(base)
        if not html:
            continue
        links, seen = [], set()
        for m in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.I | re.S):
            href = m.group(1)
            txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
            if not KEY.search(f"{href} {txt}") or href.startswith(("#", "mailto:", "javascript")):
                continue
            u = href if href.startswith("http") else base.rstrip("/") + "/" + href.lstrip("/")
            if u not in seen and not re.search(r"\.pdf|\.xls", u, re.I):
                seen.add(u)
                links.append((u, txt))
        print(f"  kandidatske podstranice ({len(links)}):")
        for u, t in links[:20]:
            print(f"    LINK: {u[:130]}  TEXT: {t[:70]}")
        for u, _t in links[:8]:
            _dump(u)
    return 0


if __name__ == "__main__":
    sys.exit(main())
