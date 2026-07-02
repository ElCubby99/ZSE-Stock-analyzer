"""EHO (eho.zse.hr) klijent — jedini dosegljivi ZSE izvor bez API ključa.

Feed dokumentacija: https://eho.zse.hr/feed (JSON/XML/RSS). BITNO: bez
dateFrom/dateTo feed vraća samo današnji dan. Egress proxy re-terminira TLS,
pa requests mora vjerovati CA bundleu (REQUESTS_CA_BUNDLE ili EHO_CA_BUNDLE).

Strukturirani dividendni blokovi: objave odluka glavnih skupština na
eho.zse.hr nose sekciju "Informacije o dividendi" s poljima po VRIJEDNOSNICI
(klasi): tip, iznos EUR, ex-datum, datum prava, datum isplate. To je izvor
stvarnih dps brojki po klasi (vidi parse_dividend_blocks).
"""
from __future__ import annotations

import html as _html
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

import requests

BASE = "https://eho.zse.hr"


def _verify():
    return (os.getenv("EHO_CA_BUNDLE") or os.getenv("REQUESTS_CA_BUNDLE")
            or os.getenv("SSL_CERT_FILE") or True)


def feed(variant: str, *, ticker: str | None = None,
         date_from: str | None = None, date_to: str | None = None,
         news_type_id: int | None = None, timeout: int = 60) -> dict[str, Any]:
    """JSON feed: variant je financialReports|issuerNews|tradingNews|..."""
    params: dict[str, Any] = {"variant": variant}
    if ticker:
        params["ticker"] = ticker
    if date_from:
        params["dateFrom"] = date_from
    if date_to:
        params["dateTo"] = date_to
    if news_type_id is not None:
        params["newsTypeId"] = news_type_id
    r = requests.get(f"{BASE}/feed/json", params=params, timeout=timeout,
                     verify=_verify())
    r.raise_for_status()
    return r.json()


def page_text(url: str, *, timeout: int = 60) -> str:
    """Dohvati EHO stranicu objave i vrati očišćeni tekst (bez tagova)."""
    r = requests.get(url, timeout=timeout, verify=_verify())
    r.raise_for_status()
    t = re.sub(r"<script.*?</script>", " ", r.text, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", _html.unescape(t)).strip()


# ---------- "Informacije o dividendi" blokovi ----------
@dataclass
class DividendInfo:
    class_ticker: str          # 'ADRS', 'ADRS2', 'CROS', 'CROS2', ...
    security_name: str
    div_type: str              # 'Izglasana dividenda' | 'Predujam dividende' | ...
    amount_eur: float
    ex_date: Optional[date]
    record_date: Optional[date]
    payment_date: Optional[date]
    source_url: str


def _hr_date(s: str | None) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(s.strip().rstrip("."), "%d.%m.%Y").date()
    except ValueError:
        return None


_BLOCK_RE = re.compile(
    r"Za vrijednosnicu\s+(?P<name>.+?)\s+(?P<ticker>[A-Z][A-Z0-9]{1,11})\s+"
    r"Tip dividende\s+(?P<dtype>.+?)\s+Vrsta dividende\s+.+?\s+"
    r"Vrijednost dividende\s+(?P<amount>[\d.,]+)\s*(?P<ccy>EUR|HRK)\s+"
    r"Početak trgovanja bez dividende\s+(?P<ex>\d{2}\.\d{2}\.\d{4}\.?)\s+"
    r"Datum stjecanja prava na dividendu\s+(?P<rec>\d{2}\.\d{2}\.\d{4}\.?)\s+"
    r"Datum isplate dividende\s+(?P<pay>\d{2}\.\d{2}\.\d{4}\.?)",
)


def parse_dividend_blocks(text: str, source_url: str) -> list[DividendInfo]:
    """Parsiraj sve "Informacije o dividendi" blokove iz teksta EHO objave."""
    out: list[DividendInfo] = []
    for m in _BLOCK_RE.finditer(text):
        amount = float(m.group("amount").replace(".", "").replace(",", ".")
                       if "," in m.group("amount") else m.group("amount"))
        if m.group("ccy") == "HRK":
            # HRK dividende (do 2022) — konverzija fiksnim tečajem radi konzistencije.
            from . import config
            amount = amount / config.HRK_EUR_RATE
        out.append(DividendInfo(
            class_ticker=m.group("ticker"),
            security_name=m.group("name").strip(),
            div_type=m.group("dtype").strip(),
            amount_eur=amount,
            ex_date=_hr_date(m.group("ex")),
            record_date=_hr_date(m.group("rec")),
            payment_date=_hr_date(m.group("pay")),
            source_url=source_url,
        ))
    return out
