#!/usr/bin/env python3
"""Jednokratni forenzički alat (runda 3): per-fond NAV izvor.

Runda 2 (19.07.2026.): AZ (azfond.hr) i Raiffeisen (rmf.hr) NE objavljuju
NAV brojku u HTML-u fond-stranica (samo jedinice/naknade/limite);
erstedoo.hr/erste-plavi.hr ne postoje (DNS), pbzco-fond.hr timeout s GH
runnera. Runda 3: (1) REGOS — službena mjesečna statistika po fondu,
(2) DuckDuckGo HTML tražilica za stvarne domene Erste Plavi / PBZ CO,
(3) hrportfolio.hr NAV stranice kao orijentir gdje agregatori to nalaze.
"""
import re
import sys

import requests

UA = {"User-Agent": "Mozilla/5.0 (compatible; podaci; burzovnilist.com)"}
NAV_TXT = re.compile(r"neto\s+imovin|imovin[a-z]*\s+fonda", re.I)


def _fetch(url, timeout=30):
    r = requests.get(url, timeout=timeout, headers=UA)
    r.raise_for_status()
    return r.text


def _plain(html):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.I | re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))


def _dump(url, timeout=30):
    try:
        html = _fetch(url, timeout)
    except Exception as e:  # noqa: BLE001
        print(f"  {url}: GREŠKA {type(e).__name__}: {str(e)[:100]}")
        return None
    plain = _plain(html)
    print(f"  --- {url} (len {len(plain)}) ---")
    for m in NAV_TXT.finditer(plain):
        s = plain[max(0, m.start() - 70):m.start() + 200]
        if re.search(r"\d", s):
            print(f"    KONTEKST: ...{s}...")
    for m in re.finditer(r'href="([^"]+\.(?:pdf|xlsx?|csv))"', html, re.I):
        if re.search(r"statisti|izvje|pokazatelj|omf|mirovin|neto|imovin", m.group(1), re.I):
            print(f"    FILE: {m.group(1)[:150]}")
    return html


def main() -> int:
    # 1) REGOS — službena statistika po fondu
    print("########## REGOS ##########")
    for url in ("https://www.regos.hr", "https://regos.hr",
                "https://www.regos.hr/statistika",
                "https://www.regos.hr/objave/statisticka-izvjesca"):
        html = _dump(url)
        if html:
            base = re.match(r"https?://[^/]+", url).group(0)
            seen = set()
            for m in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                                 html, re.I | re.S):
                href = m.group(1)
                txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
                if re.search(r"statisti|izvje|pokazatelj|omf|mirovin", f"{href} {txt}", re.I) \
                        and not href.startswith(("#", "mailto:", "javascript")):
                    u = href if href.startswith("http") else base + "/" + href.lstrip("/")
                    if u not in seen:
                        seen.add(u)
                        print(f"    LINK: {u[:130]}  TEXT: {txt[:70]}")
            # dublje: prve 3 statističke podstranice
            for u in list(seen)[:3]:
                if not re.search(r"\.pdf|\.xls", u, re.I):
                    _dump(u)
            break

    # 2) DDG tražilica za stvarne domene Erste Plavi i PBZ CO
    for q in ("Erste Plavi obvezni mirovinski fond službena stranica",
              "PBZ Croatia osiguranje obvezni mirovinski fond neto imovina",
              "AZ obvezni mirovinski fond mjesečni izvještaj neto imovina"):
        print(f"\n########## DDG: {q} ##########")
        try:
            html = _fetch("https://html.duckduckgo.com/html/?q=" + requests.utils.quote(q))
            for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                                 html, re.I | re.S):
                txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
                print(f"    REZ: {m.group(1)[:140]}  {txt[:70]}")
        except Exception as e:  # noqa: BLE001
            print(f"    GREŠKA {type(e).__name__}: {str(e)[:100]}")

    # 3) hrportfolio (agregator, NIJE izvor za produkciju — samo orijentir
    #    gdje se per-fond NAV javno nalazi)
    print("\n########## hrportfolio (orijentir) ##########")
    _dump("https://hrportfolio.hr/fondovi/pregled-mirovinskih-fondova")
    return 0


if __name__ == "__main__":
    sys.exit(main())
