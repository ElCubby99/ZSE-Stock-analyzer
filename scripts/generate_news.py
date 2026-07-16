#!/usr/bin/env python3
"""M30: auto-generacija vijesti iz podataka koje pipeline već ima.

Skenira lokalnu bazu za NOVA izvješća (filings.ingested_at) i NOVE dividende
(dividends.created_at, bez izvedenih backfill zapisa) unutar lookback prozora
te ih šalje kao DRAFT vijesti u Supabase kroz Edge Function `news-ingest`
(x-api-key = BLOG_API_KEY). Nikad auto-publish — admin pregledava u /admin.

Dedup: auto_source_ref ('filing:<id>' / 'dividend:<id>') je unique u
news_items, pa je ponovni run istog pipelinea idempotentan (skipped, ne
duplikat). Pipeline NEMA direktan write u Supabase bazu — samo endpoint.

Pokretanje (korak 5 u scripts/daily_update.sh):
    .venv/bin/python scripts/generate_news.py [--lookback-days 7] [--dry-run]

Env (u .env / okolini): SUPABASE_URL + BLOG_API_KEY; bez njih se (osim uz
--dry-run) samo ispiše upozorenje i izađe bez greške (pipeline ne smije pasti
zbog vijesti).
"""
import argparse
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402

PERIOD_HR = {
    "annual": "godišnje izvješće",
    "h1": "polugodišnje izvješće",
    "q1": "izvješće za Q1",
    "q2": "izvješće za Q2",
    "q3": "izvješće za Q3",
    "q4": "izvješće za Q4",
    "9m": "izvješće za 9 mjeseci",
}


def _clip(s: str, limit: int = 120) -> str:
    """Kratko za headline (<=120): reži na granici riječi, nikad usred."""
    if len(s) <= limit:
        return s
    cut = s[: limit - 1].rsplit(" ", 1)[0]
    return f"{cut}…"


def _fmt_amount(v) -> str:
    return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def collect_filing_news(cur, date_from: date) -> list[dict]:
    cur.execute(
        """SELECT f.id, c.ticker, c.name, f.fiscal_year, f.period_type
           FROM filings f JOIN companies c ON c.id = f.company_id
           WHERE f.doc_type = 'financial_report' AND f.ingested_at >= %s
           ORDER BY f.ingested_at""", (date_from,))
    items = []
    for fid, ticker, name, fy, period in cur.fetchall():
        what = PERIOD_HR.get(period, "izvješće")
        fy_txt = f" za {fy}." if fy else ""
        items.append({
            "ticker": ticker,
            "category": "novo_izvjesce",
            "headline": _clip(f"Novo {what}{fy_txt} — {name} ({ticker}) — pogledaj analizu"),
            "body": None,
            "link_path": f"/dionica/{ticker.lower()}",
            "auto_source_ref": f"filing:{fid}",
        })
    return items


def collect_dividend_news(cur, date_from: date) -> list[dict]:
    # samo stvarne objave: bez izvedenih (NT backfill) i bez zapisa bez iznosa
    # ("ništa izmišljeno" — vijest bez iznosa nema sadržaja)
    cur.execute(
        """SELECT d.id, c.ticker, c.name, d.amount_eur
           FROM dividends d JOIN companies c ON c.id = d.company_id
           WHERE d.created_at >= %s AND d.amount_eur IS NOT NULL
             AND (d.div_type IS NULL OR d.div_type NOT ILIKE '%%izvedeno%%')
           ORDER BY d.created_at""", (date_from,))
    items = []
    for did, ticker, name, amount in cur.fetchall():
        items.append({
            "ticker": ticker,
            "category": "dividenda",
            "headline": _clip(
                f"Najavljena isplata dividende za {name} ({ticker}) — "
                f"{_fmt_amount(amount)} € po dionici"),
            "body": None,
            "link_path": f"/dionica/{ticker.lower()}",
            "auto_source_ref": f"dividend:{did}",
        })
    return items


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lookback-days", type=int, default=7)
    ap.add_argument("--dry-run", action="store_true",
                    help="samo ispiši kandidate (JSON), bez slanja")
    a = ap.parse_args()

    date_from = date.today() - timedelta(days=a.lookback_days)
    with get_conn() as conn, conn.cursor() as cur:
        items = collect_filing_news(cur, date_from) + collect_dividend_news(cur, date_from)

    if a.dry_run:
        print(json.dumps(items, ensure_ascii=False, indent=1))
        return 0
    if not items:
        print("[vijesti] ništa novo u lookback prozoru")
        return 0

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("BLOG_API_KEY")
    if not url or not key:
        print("[vijesti] SUPABASE_URL/BLOG_API_KEY nisu postavljeni — "
              f"{len(items)} kandidata NIJE poslano (postavi env za auto vijesti)")
        return 0

    import requests
    # Edge Function prima najviše 200 stavki po pozivu — šalji u serijama
    # (16.07.2026.: nagomilani kandidati srušili run s 400 "max 200 po pozivu")
    BATCH = 200
    tot_new = tot_skip = tot_err = 0
    for i in range(0, len(items), BATCH):
        chunk = items[i:i + BATCH]
        r = requests.post(f"{url.rstrip('/')}/functions/v1/news-ingest",
                          headers={"x-api-key": key, "Content-Type": "application/json"},
                          json={"items": chunk}, timeout=60)
        if r.status_code != 200:
            print(f"[vijesti] news-ingest {r.status_code} (serija "
                  f"{i // BATCH + 1}): {r.text[:300]}")
            return 1
        d = r.json()
        tot_new += d.get("inserted") or 0
        tot_skip += d.get("skipped") or 0
        tot_err += d.get("errors") or 0
    print(f"[vijesti] poslano {len(items)}: novo={tot_new} "
          f"preskočeno(dedup)={tot_skip} greške={tot_err}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
