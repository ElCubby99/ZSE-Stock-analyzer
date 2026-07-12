#!/usr/bin/env python3
"""Novosti tab: deterministički import EHO objava izdavatelja u announcements
(BEZ klasifikacije — ta ostaje watcheru s API-jem; category=NULL, samo
naslov+datum+link kako jesu na EHO-u). Dedup po external_id."""
import sys
sys.path.insert(0, ".")
from datetime import date, timedelta

from src.db import get_conn
from src import eho

TICKERS = ["ADRS", "CROS", "ZABA", "ADPL", "ARNT", "ATGR", "DLKV", "HPB", "HT",
           "IG", "KODT", "KOEI", "PODR", "RIVP", "SPAN", "TOK", "ZITO"]


def main():
    date_from = (date.today() - timedelta(days=365)).isoformat()
    with get_conn() as conn, conn.cursor() as cur:
        total = 0
        for t in TICKERS:
            cur.execute("SELECT id FROM companies WHERE ticker=%s", (t,))
            r = cur.fetchone()
            if not r:
                continue
            cid = r[0]
            try:
                d = eho.feed("issuerNews", ticker=t, date_from=date_from,
                             date_to=date.today().isoformat())
            except Exception as e:  # noqa: BLE001
                print(f"  [skip] {t}: {e}"); continue
            n = 0
            for it in d.get("items") or []:
                link = it.get("link")
                title = (it.get("title") or "").strip()
                if not link or not title:
                    continue
                cur.execute(
                    """INSERT INTO announcements (company_id, published_at, title,
                         category, source_url, external_id, needs_review, action_taken)
                       VALUES (%s,%s,%s,NULL,%s,%s,FALSE,
                               'import bez klasifikacije (Novosti tab)')
                       ON CONFLICT (external_id) WHERE external_id IS NOT NULL DO NOTHING""",
                    (cid, (it.get("publishDate") or "")[:10] or None,
                     title[:400], link, link))
                n += cur.rowcount
            total += n
            print(f"  {t}: +{n} objava")
        print(f"ukupno novih: {total}")


if __name__ == "__main__":
    main()
