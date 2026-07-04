"""ESEF/iXBRL ruta (M6 popravak 1): EHO ZIP -> xhtml -> tekst za ekstrakciju.

Neki izdavatelji (HT, ZABA) objavljuju godišnje izvješće SAMO kao ESEF paket
(ZIP s inline-XBRL xhtml-om). Ova ruta ga čini prvorazrednim izvorom:
raspakiraj, nađi reports/*.xhtml, skini tagove, vrati tekst s brojevima
stranica u podnožjima (extractor ih citira kao source_page).
"""
from __future__ import annotations

import html as _html
import os
import re
import zipfile


def download(url: str, dest: str, timeout: int = 300) -> str:
    import requests

    r = requests.get(url, timeout=timeout,
                     verify=(os.getenv("REQUESTS_CA_BUNDLE")
                             or os.getenv("SSL_CERT_FILE") or True))
    r.raise_for_status()
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(r.content)
    return dest


def xhtml_to_text(raw: str) -> str:
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S)
    t = re.sub(r"</(p|div|tr|td|th|h\d|li|table)>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = _html.unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t)


def zip_to_text(zip_path: str, _depth: int = 0) -> tuple[str, str]:
    """ZIP -> (tekst, vrsta). ESEF xhtml ako postoji; inače najveći PDF u ZIP-u
    (neki izdavatelji zipaju PDF-ove, ne ESEF). -> vrsta u {'xhtml','pdf'}."""
    with zipfile.ZipFile(zip_path) as z:
        xh = [i for i in z.infolist()
              if i.filename.lower().endswith((".xhtml", ".html"))]
        if xh:
            best = max(xh, key=lambda i: i.file_size)
            raw = z.read(best).decode("utf-8", errors="replace")
            return xhtml_to_text(raw), "xhtml"
        pdfs = [i for i in z.infolist() if i.filename.lower().endswith(".pdf")]
        if pdfs:
            from .pdf_extract import pdf_to_text
            best = max(pdfs, key=lambda i: i.file_size)
            inner = zip_path + ".inner.pdf"
            with open(inner, "wb") as f:
                f.write(z.read(best))
            return pdf_to_text(inner), "pdf"
        # ugniježđeni ZIP (npr. HT: wrapper oko ESEF paketa) — spusti se razinu
        zips = [i for i in z.infolist() if i.filename.lower().endswith(".zip")]
        if zips and _depth < 2:
            best = max(zips, key=lambda i: i.file_size)
            inner = zip_path + f".inner{_depth}.zip"
            with open(inner, "wb") as f:
                f.write(z.read(best))
            return zip_to_text(inner, _depth=_depth + 1)
    raise ValueError("ZIP ne sadrži ni xhtml ni PDF (ni ugniježđeni ZIP)")
