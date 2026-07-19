#!/usr/bin/env python3
"""Jednokratni forenzički alat (runda 2): ispiši GDJE i KAKO mirovinska
društva objavljuju NETO IMOVINU (NAV) pojedinog OMF-a.

Runda 1 (19.07.2026.) pokazala: azfond.hr/rmf.hr dostupni ali NAV nije na
skeniranim stranicama (fond-stranice nisu bile u kandidatima); Erste kriva
domena (www.erste-plavi.hr ne postoji); pbzco-fond.hr timeout. Runda 2:
ispravljene domene, dublji crawl fond-stranica (omf/kategorij u URL-u),
ispis brojeva uz 'neto imovina' i popis PDF-ova s 'mjesec' u nazivu.
"""
import re
import sys

import requests

SITES = {
    "AZ": ["https://www.azfond.hr",
           "https://www.azfond.hr/az-omf-kategorije-a/",
           "https://www.azfond.hr/az-omf-kategorije-b/",
           "https://www.azfond.hr/az-omf-kategorije-c/",
           "https://www.azfond.hr/mjesecni-izvjestaji/",
           "https://www.azfond.hr/zakonske-objave"],
    "Erste Plavi": ["https://www.erstedoo.hr", "https://erstedoo.hr",
                    "https://www.erste-plavi.hr"],
    "PBZ CO": ["https://www.pbzco-fond.hr", "https://pbzco-fond.hr",
               "http://www.pbzco-fond.hr", "https://mirovinski.pbz.hr"],
    "Raiffeisen": ["https://www.rmf.hr/default.aspx?id=24",
                   "https://www.rmf.hr/default.aspx?id=32"],
}
UA = {"User-Agent": "Mozilla/5.0 (compatible; podaci; burzovnilist.com)"}
FOND_LINK = re.compile(r"omf|kategorij|mjese[cč]|izvje[sš]|neto|imovin|fond", re.I)
NAV_NUM = re.compile(r"(neto\s+imovin[a-z]*[^0-9]{0,120})([\d.,]{4,})", re.I)


def _fetch(url, timeout=90):
    r = requests.get(url, timeout=timeout, headers=UA)
    r.raise_for_status()
    return r.text


def _dump(url, html, deep_base=None):
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html,
                  flags=re.I | re.S)
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))
    print(f"  --- {url} (len {len(plain)}) ---")
    # 1) brojevi neposredno uz 'neto imovina'
    for m in NAV_NUM.finditer(plain):
        print(f"    NAV-KANDIDAT: ...{m.group(1)[-90:]}{m.group(2)}...")
    # 2) fact-box parovi (dt/dd, th/td, li) koji spominju imovinu
    for m in re.finditer(r"neto imovin[a-z]*", plain, re.I):
        s = plain[max(0, m.start() - 60):m.start() + 200]
        if re.search(r"\d", s):
            print(f"    KONTEKST: ...{s}...")
    # 3) PDF/XLSX s 'mjesec'/'izvj' u nazivu
    for m in re.finditer(r'href="([^"]+\.(?:pdf|xlsx?))"', html, re.I):
        if re.search(r"mjese|izvje|neto|imovin|report", m.group(1), re.I):
            print(f"    FILE: {m.group(1)[:150]}")
    # 4) poveznice na fond-stranice (za ručni odabir sljedeće razine)
    if deep_base:
        seen = set()
        for m in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                             html, re.I | re.S):
            href = m.group(1)
            txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
            if not FOND_LINK.search(f"{href} {txt}") or href.startswith(("#", "mailto:", "javascript")):
                continue
            u = href if href.startswith("http") else deep_base.rstrip("/") + "/" + href.lstrip("/")
            if u in seen:
                continue
            seen.add(u)
            print(f"    LINK: {u[:120]}  TEXT: {txt[:70]}")


def main() -> int:
    for fund, urls in SITES.items():
        print(f"\n########## {fund} ##########")
        for url in urls:
            try:
                html = _fetch(url)
            except Exception as e:  # noqa: BLE001
                print(f"  {url}: GREŠKA {type(e).__name__}: {str(e)[:110]}")
                continue
            base = re.match(r"https?://[^/]+", url).group(0)
            _dump(url, html, deep_base=base)
            # jedna razina dublje: fond-stranice s homepage-a (max 6)
            if url.rstrip("/").count("/") <= 2:   # samo za homepage
                links = []
                for m in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                                     html, re.I | re.S):
                    href = m.group(1)
                    txt = re.sub(r"<[^>]+>", " ", m.group(2))
                    if re.search(r"omf|kategorij|mjese[cč]ni", f"{href} {txt}", re.I) \
                            and not href.startswith(("#", "mailto:", "javascript")) \
                            and not re.search(r"\.pdf|\.xls", href, re.I):
                        u = href if href.startswith("http") else base + "/" + href.lstrip("/")
                        if u not in links:
                            links.append(u)
                for u in links[:6]:
                    try:
                        _dump(u, _fetch(u))
                    except Exception as e:  # noqa: BLE001
                        print(f"  {u}: GREŠKA {type(e).__name__}: {str(e)[:90]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
