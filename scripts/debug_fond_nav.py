#!/usr/bin/env python3
"""M-FOND5 izviđanje (runda L3): TOČNI URL-ovi od Borisa (19.07.2026.).

- AZ: .../kategorija-{a,b,c}/kretanje-vrijednosti-nav-a/ (NAV!) +
      financijska-izvjesca/
- PBZ CO: pbzco-fond.hr/fondovi/fond-{a,b,c}/financijski-izvjestaji
- Erste Plavi: www.ersteplavi.hr (BEZ crtice!) + /objave/
- RMF: puna fond-stranica (NAV + struktura imovine po Borisu)

Cilj: utvrditi što je dohvatljivo s GitHub runnera i u kojem obliku
(HTML tablica / JSON / PDF) da se napišu strogi parseri. Samo čita.
"""
import re
import sys

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URLS = [
    ("AZ NAV A", "https://www.azfond.hr/obvezni-mirovinski-fond/kategorija-a/kretanje-vrijednosti-nav-a/"),
    ("AZ NAV B", "https://www.azfond.hr/obvezni-mirovinski-fond/kategorija-b/kretanje-vrijednosti-nav-a/"),
    ("AZ FI B", "https://www.azfond.hr/obvezni-mirovinski-fond/kategorija-b/financijska-izvjesca/"),
    ("PBZ B", "https://www.pbzco-fond.hr/fondovi/fond-b/financijski-izvjestaji"),
    ("Erste home", "https://www.ersteplavi.hr/"),
    ("Erste objave", "https://www.ersteplavi.hr/objave/"),
    ("RMF A puna", "https://www.rmf.hr/raiffeisen-obvezni-mirovinski-fond-kategorija-a-32/32"),
]
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "hr-HR,hr;q=0.9,en;q=0.8"}
NAV_TXT = re.compile(r"neto\s+imovin|NAV", re.I)


def main() -> int:
    for label, url in URLS:
        print(f"\n########## {label} — {url} ##########")
        try:
            r = requests.get(url, timeout=40, headers=UA)
            r.raise_for_status()
            html = r.text
        except Exception as e:  # noqa: BLE001
            print(f"  GREŠKA {type(e).__name__}: {str(e)[:120]}")
            continue
        text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html,
                      flags=re.I | re.S)
        plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))
        print(f"  len={len(plain)}")
        # NAV konteksti s brojkama (kraći, više njih)
        seen_ctx = set()
        for m in NAV_TXT.finditer(plain):
            s = plain[max(0, m.start() - 60):m.start() + 160]
            if re.search(r"\d[\d.,]{5,}", s) and s[:40] not in seen_ctx:
                seen_ctx.add(s[:40])
                print(f"  KONTEKST: ...{s}...")
        # SVE tablice, do 10, s do 12 redova
        for i, tm in enumerate(re.finditer(r"<table.*?</table>", html, re.I | re.S)):
            if i >= 10:
                break
            rows = re.findall(r"<tr.*?</tr>", tm.group(0), re.I | re.S)
            print(f"  TABLICA {i + 1} ({len(rows)} redova):")
            for r_ in rows[:12]:
                cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()[:38]
                         for c in re.findall(r"<t[dh].*?</t[dh]>", r_, re.I | re.S)]
                print("   |", " | ".join(cells[:8]))
        # PDF/XLSX linkovi (svi, s tekstom)
        for m in re.finditer(r'<a\b[^>]*href="([^"]+\.(?:pdf|xlsx?))"[^>]*>(.*?)</a>',
                             html, re.I | re.S):
            t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
            print(f"  FILE: {m.group(1)[:150]}  TEXT: {t[:70]}")
        # JSON/API endpointi u skriptama (za JS aplikacije poput PBZ)
        for m in re.finditer(r'["\'](/[^"\']*(?:api|json|data)[^"\']*)["\']', html, re.I):
            print(f"  API?: {m.group(1)[:120]}")
        # canvas/chart data hint
        if re.search(r"chart|highcharts|graf", html, re.I):
            print("  HINT: stranica sadrži chart/graf komponentu")
    return 0


if __name__ == "__main__":
    sys.exit(main())
