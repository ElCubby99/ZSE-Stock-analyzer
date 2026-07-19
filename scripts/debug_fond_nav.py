#!/usr/bin/env python3
"""Jednokratni forenzički alat: ispiši GDJE i KAKO mirovinska društva
objavljuju NETO IMOVINU (NAV) pojedinog OMF-a na svojim stranicama.

Stranice društava nisu dostupne iz razvojnog okruženja (allowlist), pa se
struktura ne može pogledati lokalno — skript se vrti kroz debug-fond-nav.yml
workflow (GitHub runner, otvorena mreža) i u log ispiše za svako društvo:
  1. sve <a> poveznice s homepage-a čiji href/tekst upućuje na
     izvještaje/neto imovinu/vrijednosti jedinica
  2. za kandidatske HTML stranice: isječke teksta oko 'neto imovin',
     tablice s brojkama i PDF/XLSX poveznice
Iz tog ispisa se piše ISPRAVAN strogi parser (ništa izmišljeno).
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
UA = {"User-Agent": "Mozilla/5.0 (podaci; burzovnilist.com)"}
KEY = re.compile(r"neto|imovin|izvje[sš][cć]|izvjes|vrijednost|jedinic"
                 r"|statisti|dokument|objav|mjese[cč]|omf", re.I)
NAV_TXT = re.compile(r"neto\s+imovin", re.I)


def _fetch(url):
    r = requests.get(url, timeout=60, headers=UA)
    r.raise_for_status()
    return r.text


def _links(html, base):
    out = []
    for m in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                         html, re.I | re.S):
        href, text = m.group(1), re.sub(r"<[^>]+>", " ", m.group(2))
        text = re.sub(r"\s+", " ", text).strip()
        if not KEY.search(f"{href} {text}"):
            continue
        if href.startswith("#") or href.startswith("mailto:"):
            continue
        url = href if href.startswith("http") else base.rstrip("/") + "/" + href.lstrip("/")
        out.append((url, text[:90]))
    # dedup uz očuvanje redoslijeda
    seen, ded = set(), []
    for u, t in out:
        if u not in seen:
            seen.add(u)
            ded.append((u, t))
    return ded


def _dump_page(url):
    try:
        html = _fetch(url)
    except Exception as e:  # noqa: BLE001
        print(f"    GREŠKA: {type(e).__name__}: {e}")
        return
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html,
                  flags=re.I | re.S)
    plain = re.sub(r"<[^>]+>", " ", text)
    plain = re.sub(r"\s+", " ", plain)
    hits = [m.start() for m in NAV_TXT.finditer(plain)]
    print(f"    'neto imovin' spominjanja: {len(hits)}")
    for pos in hits[:6]:
        print(f"      ...{plain[max(0, pos - 80):pos + 240]}...")
    # tablice — prvih par redova svake
    for i, tm in enumerate(re.finditer(r"<table.*?</table>", html, re.I | re.S)):
        if i >= 4:
            break
        rows = re.findall(r"<tr.*?</tr>", tm.group(0), re.I | re.S)
        print(f"    TABLICA {i + 1} ({len(rows)} redova):")
        for r_ in rows[:6]:
            cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()[:40]
                     for c in re.findall(r"<t[dh].*?</t[dh]>", r_, re.I | re.S)]
            print("      |", " | ".join(cells[:8]))
    # datoteke
    for m in re.finditer(r'href="([^"]+\.(?:pdf|xlsx?|csv))"', html, re.I):
        print(f"    FILE-LINK: {m.group(1)[:140]}")


def main() -> int:
    for fund, base in SITES.items():
        print(f"\n########## {fund} — {base} ##########")
        try:
            home = _fetch(base)
        except Exception as e:  # noqa: BLE001
            print(f"  homepage GREŠKA: {type(e).__name__}: {e}")
            continue
        links = _links(home, base)
        print(f"  kandidatske poveznice ({len(links)}):")
        for u, t in links[:25]:
            print(f"    LINK: {u}  TEXT: {t}")
        # homepage sam po sebi zna nositi NAV blok
        print("  --- HOMEPAGE dump ---")
        _dump_page(base)
        for u, t in links[:6]:
            if re.search(r"\.pdf|\.xls", u, re.I):
                continue
            print(f"  --- PAGE {u} ({t[:50]}) ---")
            _dump_page(u)
    return 0


if __name__ == "__main__":
    sys.exit(main())
