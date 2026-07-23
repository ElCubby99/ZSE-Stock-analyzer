"""Dnevni watcher (M6, Dio B) — JEDAN disclosure feed, ne re-scrape svih firmi.

Tok: EHO issuerNews od kursora naovamo -> dedup (announcements.external_id
UNIQUE) -> klasifikacija (Haiku) -> rutanje:
  financial_report  -> filings status='pending' NIJE moguće bez (year, period,
                       basis) — umjesto pogađanja, upari s financialReports
                       feedom istog izdavatelja/datuma; bez para -> needs_review.
  dividend          -> python-put: src.dividends za taj ticker (idempotentno).
  buyback/capital_change -> needs_review (broj dionica mijenjamo SAMO iz
                       citiranog izvora — politika verificiranog seeda).
  gsa/manager_transaction/other -> samo log.
Low-confidence (<0.85) -> announcements.needs_review=TRUE, BEZ rutanja.
Kursor se ažurira tek na kraju uspješnog prolaza.
"""
from __future__ import annotations

from datetime import date, timedelta

from . import eho
from .classify import MIN_CONFIDENCE, classify_announcement

SOURCE = "zse_disclosure"


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


def _route(conn, run_id: str, cur, ann_id: int, cid, ticker, category: str,
           item: dict, log) -> str:
    if category == "dividend" and ticker:
        from .dividends import scrape_dividends, store_dividends, upsert_dps_financials
        divs = scrape_dividends(ticker, date_from=(date.today() - timedelta(days=30)).isoformat(),
                                verbose=False)
        n = store_dividends(conn, ticker, divs)
        upsert_dps_financials(conn, ticker, verbose=False)
        return f"dividende: +{n} događaja, dps osvježen"
    if category == "financial_report" and ticker:
        # M44: feed za polugodišnje koristi i '1H' (uz '2Q') — proširena mapa
        from .report_sync import _period_labels
        LABEL_TO_PT = _period_labels()
        d = eho.feed("financialReports", ticker=ticker,
                     date_from=(item.get("publishDate") or "")[:10] or date.today().isoformat(),
                     date_to=date.today().isoformat())
        cid2 = _company_id(cur, ticker)
        if cid2 is None:
            cur.execute("UPDATE announcements SET needs_review=TRUE WHERE id=%s", (ann_id,))
            return f"nepoznata firma {ticker} -> needs_review (onboarding je zaseban)"
        # KORAK 2d: INTERIM (kvartal) -> TFI XLSX (deterministički, 0 kredita,
        # period_type q1/h1/9m/q4 + cumulative=TRUE jer je IFRS interim YTD).
        # GODIŠNJI (1Y) -> PDF ruta (LLM); valuacija se oslanja na 'annual'.
        # Bankovni interim je nadzorni obrazac -> parse_tfi vrati prazno u
        # ekstrakciji -> needs_review (zaseban parser je odobrena faza).
        cands = []
        for x in (d.get("items") or []):
            pt = LABEL_TO_PT.get(str(x.get("period")))
            if pt is None:
                continue
            is_interim = pt != "annual"
            if x.get("documentType") != ("XLSX" if is_interim else "PDF"):
                continue
            cands.append(((x.get("publishDate") or ""), 0 if x.get("consolidated") else 1,
                          x, pt, is_interim))
        if not cands:
            cur.execute("UPDATE announcements SET needs_review=TRUE WHERE id=%s", (ann_id,))
            return "FI objava bez uparivog dokumenta (XLSX kvartal / PDF godišnji) -> needs_review"
        cands.sort(key=lambda c: (c[0], c[1]))  # najbliži objavi, konsolidiran prvi
        _pd, _co, x, pt, is_interim = cands[0]
        basis = "consolidated" if x.get("consolidated") else "standalone"
        cumulative = True if is_interim else None
        cur.execute(
            """INSERT INTO filings (company_id, doc_type, fiscal_year, period_type,
                 basis, currency, reporting_scale, cumulative, source_url,
                 published_at, status)
               VALUES (%s,'financial_report',%s,%s,%s,'EUR',1,%s,%s,%s,'pending')
               ON CONFLICT (company_id, doc_type, fiscal_year, period_type, basis)
               DO NOTHING""",
            (cid2, x.get("year"), pt, basis, cumulative,
             (x.get("documentLink") or "").replace("\\/", "/"),
             (x.get("publishDate") or "")[:10] or None))
        route = "TFI XLSX kvartal" if is_interim else "PDF godišnji"
        return (f"filing u queue: FY{x.get('year')} {pt}/{basis} [{route}]"
                if cur.rowcount else "filing već postoji (dedup)")
    if category in ("buyback", "capital_change"):
        cur.execute("UPDATE announcements SET needs_review=TRUE WHERE id=%s", (ann_id,))
        return "promjena kapitala/trezorskih -> needs_review (verificirani seed politika)"
    return "samo log"


def run_watcher(conn, run_id: str, log, lookback_days: int = 3) -> dict:
    """-> statistika za digest. log(stage, company_id, status, message)."""
    cur = conn.cursor()
    cur.execute("SELECT last_seen_id FROM watcher_state WHERE source=%s", (SOURCE,))
    r = cur.fetchone()
    last_seen = r[0] if r else None

    date_from = (date.today() - timedelta(days=lookback_days)).isoformat()
    d = eho.feed("issuerNews", date_from=date_from, date_to=date.today().isoformat())
    items = d.get("items") or []
    items.sort(key=lambda x: (x.get("publishDate") or "", x.get("link") or ""))

    stats = {"seen": len(items), "new": 0, "routed": 0, "review": 0, "low_conf": 0}
    newest = last_seen
    for it in items:
        ext_id = it.get("link")
        if not ext_id:
            continue
        cur.execute("SELECT 1 FROM announcements WHERE external_id=%s", (ext_id,))
        if cur.fetchone():
            continue
        stats["new"] += 1
        ticker = it.get("issuerCode") or it.get("ticker")
        title = it.get("title") or ""
        cls = classify_announcement(title, issuer=ticker)
        cat, conf = cls["category"], float(cls["confidence"])
        cid = _company_id(cur, ticker)
        cur.execute(
            """INSERT INTO announcements (company_id, published_at, title, category,
                 confidence, source_url, external_id, needs_review)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (cid, (it.get("publishDate") or "")[:10] or None, title[:400], cat, conf,
             ext_id, ext_id, conf < MIN_CONFIDENCE))
        ann_id = cur.fetchone()[0]
        if conf < MIN_CONFIDENCE:
            stats["low_conf"] += 1
            log("watcher", cid, "needs_review",
                f"{ticker or '?'}: '{title[:60]}' conf {conf:.2f} < prag — bez rutanja")
            continue
        action = _route(conn, run_id, cur, ann_id, cid, ticker, cat, it, log)
        cur.execute("UPDATE announcements SET action_taken=%s WHERE id=%s",
                    (action[:200], ann_id))
        stats["routed"] += 1
        if "needs_review" in action:
            stats["review"] += 1
        log("watcher", cid, "ok", f"{ticker or '?'}: {cat} ({conf:.2f}) -> {action}")
        newest = ext_id
    cur.execute(
        """INSERT INTO watcher_state (source, last_seen_id, last_run_at)
           VALUES (%s,%s,now())
           ON CONFLICT (source) DO UPDATE SET last_seen_id=EXCLUDED.last_seen_id,
                                              last_run_at=now()""",
        (SOURCE, newest))
    return stats
