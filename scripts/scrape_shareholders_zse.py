#!/usr/bin/env python3
"""M23 izvor 2 (tekući): top 10 dioničara sa ZSE stranice papira (izvor SKDD).

Stranica papira ugrađuje "top_shareholders" JSON u HTML — javni podatak koji
ZSE prikazuje za svaki papir. Snapshot_date = datum dohvata (stranica ne
objavljuje as-of datum liste; to je dokumentirano u source_detail). Imena se
spremaju TOČNO kako su objavljena. Skrbnički/zbirni računi se OZNAČAVAJU
(is_custody) — ime s '/' je račun kod skrbničke banke (npr. fond preko
skrbnika), a eksplicitni 'skrbnički zbirni račun' nije stvarni krajnji vlasnik.

Pokretanje:  python -m scripts.scrape_shareholders_zse [--tickers ...]
Mjesečno: 1. u mjesecu iz noćnog prolaza (src/daily.py) — povijest se gradi.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys

sys.path.insert(0, ".")

import requests  # noqa: E402

from src.db import get_conn  # noqa: E402

PAPER_URL = "https://zse.hr/hr/papir/310"

CUSTODY_RX = re.compile(
    r"skrbni|custody|zbirni ra[čc]un|fiducia|client acc|/", re.I)


def _verify():
    return os.getenv("REQUESTS_CA_BUNDLE") or os.getenv("SSL_CERT_FILE") or True


def fetch_top_shareholders(isin: str) -> list[dict] | None:
    r = requests.get(PAPER_URL, params={"isin": isin}, timeout=40,
                     verify=_verify())
    r.raise_for_status()
    m = re.search(r'"top_shareholders":(\[.*?\])', r.text)
    if not m:
        return None
    try:
        rows = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    out = []
    for x in rows:
        name = (x.get("name") or "").strip()
        try:
            pct = float(str(x.get("percentage")))
        except (TypeError, ValueError):
            continue
        if name and 0 < pct <= 100:
            out.append({"rank": int(x.get("seqno") or len(out) + 1),
                        "name": name, "pct": pct,
                        "is_custody": bool(CUSTODY_RX.search(name))})
    return out or None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="*", default=None)
    a = ap.parse_args(argv)
    today = datetime.date.today()
    ok = empty = fail = 0
    with get_conn() as conn, conn.cursor() as cur:
        # primarna klasa po firmi (top_shareholders je na razini izdavatelja)
        cur.execute("""SELECT c.id, c.ticker, sc.isin FROM companies c
                       JOIN share_classes sc ON sc.company_id = c.id
                       WHERE sc.is_primary_line OR sc.id = (
                             SELECT MIN(id) FROM share_classes WHERE company_id = c.id)
                       ORDER BY c.ticker""")
        firms = [(cid, t, i) for cid, t, i in cur.fetchall() if i]
        if a.tickers:
            firms = [f for f in firms if f[1] in a.tickers]
        seen = set()
        for cid, tick, isin in firms:
            if cid in seen:
                continue
            seen.add(cid)
            try:
                rows = fetch_top_shareholders(isin)
                if not rows:
                    empty += 1
                    print(f"[dioničari] {tick}: ZSE stranica nema top_shareholders")
                    continue
                detail = (f"{PAPER_URL}?isin={isin} (izvor SKDD; lista bez "
                          f"objavljenog as-of datuma — datum = dan dohvata)")
                for r in rows:
                    cur.execute(
                        """INSERT INTO shareholders (company_id, snapshot_date,
                             source, source_detail, rank, holder_name, pct,
                             is_custody)
                           VALUES (%s,%s,'zse_skdd',%s,%s,%s,%s,%s)
                           ON CONFLICT (company_id, snapshot_date, source, rank)
                           DO UPDATE SET holder_name=EXCLUDED.holder_name,
                             pct=EXCLUDED.pct, is_custody=EXCLUDED.is_custody,
                             source_detail=EXCLUDED.source_detail""",
                        (cid, today, detail, r["rank"], r["name"], r["pct"],
                         r["is_custody"]))
                conn.commit()
                ok += 1
                print(f"[dioničari] {tick}: {len(rows)} redova (snapshot {today})")
            except Exception as e:  # noqa: BLE001
                conn.rollback()
                fail += 1
                print(f"[dioničari] {tick}: GREŠKA {str(e)[:70]}")
    print(f"\nGOTOVO: ok={ok}, bez_podataka={empty}, fail={fail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
