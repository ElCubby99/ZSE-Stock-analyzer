"""M44: deterministički sync izvješća i dividendi s EHO feedova — 0 API kredita.

Uzrok (incident 20.-23.07.2026.): watcher klasificira objave Haikuom, pa je
potrošen API kredit značio da NIŠTA novo ne ulazi u bazu (ni izvješća ni
dividende), a time ni vijesti — iako su EHO feedovi STRUKTURIRANI i za ta
dva toka klasifikacija uopće nije potrebna:

  - financialReports feed već nosi (issuer, year, period, documentType,
    consolidated, documentLink) -> filing 'pending' ide ravno u queue;
    kvartalni XLSX se parsira deterministički (parse_tfi_universe), a
    godišnji PDF čeka LLM ekstrakciju (bez ključa/kredita ostaje pending
    s razlogom — ništa se ne izmišlja).
  - dividendne objave se prepoznaju po newsTypeId/naslovu u issuerNews
    feedu (isti kriterij kao src.dividends.scrape_dividends), a iznosi se
    čitaju iz strukturiranih "Informacije o dividendi" blokova objave.

LLM watcher ostaje za slobodne kategorije (buyback, kapitalne promjene,
ostalo) — ovaj modul ga NE zamjenjuje, nego garantira da izvješća i
dividende (dva toka koja pune vijesti i valuacije) teku i bez API-ja.

CLI:  python -m src.report_sync [--lookback-days 7]
                                [--extract] [--recompute] [--regen]
      (--extract obrađuje pending queue; --recompute revalorizira dirnute
       firme; --regen regenerira exporte + okida deploy hook iz env-a)
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from . import eho

# EHO oznake perioda -> naši period_type ključevi. Feed koristi i '2Q'
# (kumulativ) i '1H' za polugodišnje — parse_tfi_universe.LABEL_TO_PT ima
# samo '2Q' (a PT_TO_LABEL mora ostati jednoznačan), pa se '1H' dodaje OVDJE.
def _period_labels() -> dict:
    from scripts.parse_tfi_universe import LABEL_TO_PT
    return {**LABEL_TO_PT, "1H": "h1"}


def _company_id(cur, ticker: str | None):
    if not ticker:
        return None
    cur.execute("SELECT company_id FROM share_classes WHERE ticker=%s", (ticker,))
    r = cur.fetchone()
    if r:
        return r[0]
    cur.execute("SELECT id FROM companies WHERE ticker=%s", (ticker,))
    r = cur.fetchone()
    return r[0] if r else None


def sync_reports(conn, log, lookback_days: int = 7) -> list[int]:
    """financialReports feed (globalno, jedan poziv) -> filings 'pending'.

    Po (izdavatelj, godina, period) bira se JEDAN dokument: konsolidirani
    ima prednost pred nekonsolidiranim, interim traži XLSX (deterministički
    TFI parser), godišnji PDF. Dedup radi UNIQUE(company_id, doc_type,
    fiscal_year, period_type, basis) + ON CONFLICT DO NOTHING.
    Vraća company_id-eve s novo ubačenim filingom."""
    labels = _period_labels()
    date_from = (date.today() - timedelta(days=lookback_days)).isoformat()
    d = eho.feed("financialReports", date_from=date_from,
                 date_to=date.today().isoformat())
    items = d.get("items") or []

    groups: dict[tuple, list] = {}
    for x in items:
        ticker = x.get("issuerCode") or x.get("ticker")
        pt = labels.get(str(x.get("period")))
        if not ticker or pt is None or not x.get("documentLink"):
            continue
        is_interim = pt != "annual"
        if x.get("documentType") != ("XLSX" if is_interim else "PDF"):
            continue
        groups.setdefault((ticker, x.get("year"), pt), []).append(x)

    touched: list[int] = []
    cur = conn.cursor()
    for (ticker, year, pt), cands in sorted(groups.items()):
        cid = _company_id(cur, ticker)
        if cid is None:
            log("watcher", None, "skipped",
                f"{ticker}: izvješće FY{year} {pt} — firma nije u bazi "
                "(onboarding je zaseban)")
            continue
        # konsolidirani prije nekonsolidiranog; unutar toga najnovija objava
        cands.sort(key=lambda c: (0 if c.get("consolidated") else 1,
                                  c.get("publishDate") or ""),)
        x = cands[0]
        basis = "consolidated" if x.get("consolidated") else "standalone"
        is_interim = pt != "annual"
        cur.execute(
            """INSERT INTO filings (company_id, doc_type, fiscal_year, period_type,
                 basis, currency, reporting_scale, cumulative, source_url,
                 published_at, status)
               VALUES (%s,'financial_report',%s,%s,%s,'EUR',1,%s,%s,%s,'pending')
               ON CONFLICT (company_id, doc_type, fiscal_year, period_type, basis)
               DO NOTHING""",
            (cid, year, pt, basis, True if is_interim else None,
             (x.get("documentLink") or "").replace("\\/", "/"),
             (x.get("publishDate") or "")[:10] or None))
        if cur.rowcount:
            touched.append(cid)
            route = "TFI XLSX (deterministički)" if is_interim else "PDF (LLM ekstrakcija)"
            log("watcher", cid, "ok",
                f"{ticker}: FY{year} {pt}/{basis} u queue [{route}] — EHO feed, bez klasifikacije")
    return touched


def sync_dividend_news(conn, log, lookback_days: int = 7) -> int:
    """issuerNews feed (globalno) -> dividendne objave BEZ klasifikacije:
    isti kriterij kao scrape_dividends (newsTypeId ili 'dividend' u naslovu).
    Za svaki pogođeni ticker: scrape + store + dps upsert (idempotentno).
    Objava se bilježi u announcements (external_id UNIQUE) pa je LLM watcher
    kasnije preskače — nema dvostrukog troška ni dvostrukih zapisa."""
    from .dividends import (DIVIDEND_NEWS_TYPES, scrape_dividends,
                            store_dividends, upsert_dps_financials)
    date_from = (date.today() - timedelta(days=lookback_days)).isoformat()
    d = eho.feed("issuerNews", date_from=date_from,
                 date_to=date.today().isoformat())
    cur = conn.cursor()
    hits: dict[str, list] = {}
    for it in d.get("items") or []:
        title = (it.get("title") or "")
        if it.get("type") not in DIVIDEND_NEWS_TYPES and "dividend" not in title.lower():
            continue
        ticker = it.get("issuerCode") or it.get("ticker")
        ext_id = it.get("link")
        if not ticker or not ext_id:
            continue
        cur.execute("SELECT 1 FROM announcements WHERE external_id=%s", (ext_id,))
        if cur.fetchone():
            continue
        hits.setdefault(ticker, []).append(it)

    n_total = 0
    for ticker, its in sorted(hits.items()):
        cid = _company_id(cur, ticker)
        try:
            divs = scrape_dividends(ticker, date_from=date_from, verbose=False)
            n = store_dividends(conn, ticker, divs) if divs else 0
            if divs:
                upsert_dps_financials(conn, ticker, verbose=False)
            n_total += n
            action = f"dividende (deterministički): +{n} događaja"
        except Exception as e:  # noqa: BLE001 — jedan ticker ne ruši sync
            conn.rollback()
            log("watcher", cid, "failed",
                f"{ticker}: dividendni scrape: {type(e).__name__}: {e}")
            continue
        for it in its:
            cur.execute(
                """INSERT INTO announcements (company_id, published_at, title,
                     category, confidence, source_url, external_id,
                     needs_review, action_taken)
                   VALUES (%s,%s,%s,'dividend',1.00,%s,%s,FALSE,%s)
                   ON CONFLICT (external_id) WHERE external_id IS NOT NULL
                   DO NOTHING""",
                (cid, (it.get("publishDate") or "")[:10] or None,
                 (it.get("title") or "")[:400], it.get("link"), it.get("link"),
                 action[:200]))
        log("watcher", cid, "ok", f"{ticker}: {action}")
    return n_total


def import_backlogs(conn, log, path="data/sync/backlogs.json") -> int:
    """M47: upsert kuriranih backlog redova iz verzioniranog seed JSON-a
    (ticker, fiscal_year, backlog_eur, growth_rate, source). Surgical — dira
    SAMO tablicu backlogs; idempotentno (ON CONFLICT UPDATE). Vraća broj
    redova. Nepostojeći file / prazan -> 0 bez greške."""
    import json
    import pathlib
    p = pathlib.Path(path)
    if not p.exists():
        return 0
    rows = json.loads(p.read_text(encoding="utf-8"))
    cur = conn.cursor()
    n = 0
    for r in rows:
        cur.execute("SELECT id FROM companies WHERE ticker=%s", (r["ticker"],))
        c = cur.fetchone()
        if not c:
            log("backlog", None, "skipped", f"{r['ticker']}: firma nije u bazi")
            continue
        cur.execute(
            """INSERT INTO backlogs (company_id, fiscal_year, backlog_eur,
                 growth_rate, source)
               VALUES (%s,%s,%s,%s,%s)
               ON CONFLICT (company_id, fiscal_year) DO UPDATE SET
                 backlog_eur=EXCLUDED.backlog_eur, growth_rate=EXCLUDED.growth_rate,
                 source=EXCLUDED.source""",
            (c[0], r["fiscal_year"], r.get("backlog_eur"), r.get("growth_rate"),
             r["source"]))
        n += 1
        log("backlog", c[0], "ok",
            f"{r['ticker']} FY{r['fiscal_year']}: backlog upsert "
            f"(g={r.get('growth_rate')})")
    return n


def main(argv=None) -> int:
    sys.path.insert(0, ".")
    from .daily import (_logger, ensure_schema, stage_extract_queue,
                        stage_recompute, stage_regen)
    from .db import get_conn

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lookback-days", type=int, default=7)
    p.add_argument("--extract", action="store_true",
                   help="obradi pending filings queue nakon synca")
    p.add_argument("--recompute", action="store_true",
                   help="revaloriziraj dirnute firme")
    p.add_argument("--recompute-tickers", default="",
                   help="zarezom odvojeni tickeri za revalorizaciju uz sync "
                        "('svi' = sve firme s financijama u bazi — npr. nakon "
                        "promjene metodologije)")
    p.add_argument("--regen", action="store_true",
                   help="regeneriraj exporte (+ deploy hook iz env-a)")
    a = p.parse_args(argv)

    with get_conn() as conn:
        run_id = f"report-sync-{date.today().isoformat()}"
        log = _logger(conn, run_id)
        try:
            ensure_schema(conn)
        except Exception as e:  # noqa: BLE001
            conn.rollback()
            log("schema", None, "failed", f"{type(e).__name__}: {e}")
        touched = sync_reports(conn, log, a.lookback_days)
        n_div = sync_dividend_news(conn, log, a.lookback_days)
        try:
            n_bl = import_backlogs(conn, log)
        except Exception as e:  # noqa: BLE001 — seed opcionalan, ne ruši sync
            conn.rollback()
            log("backlog", None, "failed", f"{type(e).__name__}: {e}")
            n_bl = 0
        conn.commit()
        print(f"[report-sync] novih filinga: {len(touched)}, "
              f"dividendnih događaja: {n_div}, backlog redova: {n_bl}")
        if a.extract:
            touched = sorted(set(touched + stage_extract_queue(conn, run_id, log)))
        extra: list[int] = []
        if a.recompute_tickers.strip():
            arg = a.recompute_tickers.strip()
            with conn.cursor() as cur:
                if arg.lower() in ("svi", "all", "*"):
                    cur.execute("SELECT DISTINCT company_id FROM financials")
                else:
                    tks = [t.strip().upper() for t in arg.split(",") if t.strip()]
                    cur.execute("SELECT id FROM companies WHERE ticker = ANY(%s)",
                                (tks,))
                extra = [r[0] for r in cur.fetchall()]
        if (a.recompute and touched) or extra:
            stage_recompute(conn, run_id, log, sorted(set(touched + extra)))
        if a.regen:
            stage_regen(conn, run_id, log, changed=bool(touched or n_div))
        conn.commit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
