"""Noćni prolaz (M6, Dio C) + digest (Dio D). Jedan run_id; redoslijed bitan:
  1. watcher  2. extract_queue  3. recompute  4. prices_eod  5. regen  6. digest

Robusnost: izolacija greške po firmi/koraku (jedan pad ne ruši run),
idempotentno (dedup po ID-evima, ON CONFLICT), validate gate uvijek.
Detekcija promjene layouta: previše low-confidence klasifikacija u istom runu
-> alert u digestu + pauza auto-akcija (auto-promocija ovdje ionako ne postoji).

CLI:  python -m src.daily            # puni prolaz
      python -m src.daily --digest-only <run_id>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

from .db import get_conn

LAYOUT_ALERT_LOW_CONF = 5   # >=N low-conf klasifikacija u runu -> alert


def _logger(conn, run_id):
    def log(stage, company_id, status, message):
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO pipeline_runs (run_id, stage, company_id, status, message) "
                "VALUES (%s,%s,%s,%s,%s)",
                (run_id, stage, company_id, status, str(message)[:1500]))
        print(f"[{stage}] {status}: {str(message)[:150]}")
    return log


def stage_extract_queue(conn, run_id, log) -> list[int]:
    """filings status='pending' -> download + auto slice + template ekstrakcija."""
    from .auto_slice import build_slice
    from .loader import load_extraction
    from .pdf_extract import pdf_to_text
    from .validator import validate_filing
    import requests

    cur = conn.cursor()
    cur.execute(
        """SELECT f.id, f.company_id, c.ticker, c.sector, f.source_url, f.fiscal_year,
                  f.period_type, f.cumulative
           FROM filings f JOIN companies c ON c.id=f.company_id
           WHERE f.status='pending' ORDER BY f.id""")
    touched = []
    for fid, cid, ticker, sector, url, year, period_type, cumulative in cur.fetchall():
        try:
            # KORAK 2d: TFI-POD XLSX (kvartal) -> deterministički parser, 0 kredita
            if (url or "").lower().endswith(".xlsx"):
                if sector in ("bank", "insurance"):
                    # FINREP nadzorni layout — industrijski parser bi krivo
                    # matchao; čeka zaseban parser (M19 nalaz)
                    log("extract", cid, "needs_review",
                        f"{ticker}: bankovni interim XLSX (FINREP) -> zaseban parser")
                    continue
                from scripts.parse_tfi_universe import ingest_tfi_xlsx
                new_fid, parsed = ingest_tfi_xlsx(
                    conn, ticker, url, year, period_type or "annual",
                    cumulative=bool(cumulative))
                if new_fid is None:
                    log("extract", cid, "needs_review",
                        f"{ticker}: XLSX nije TFI-POD (npr. bankovni nadzorni obrazac) "
                        "-> zaseban parser")
                    conn.rollback()
                    continue
                res = validate_filing(conn, new_fid)
                log("extract", cid, "ok" if res["status"] == "validated" else "needs_review",
                    f"{ticker}: {period_type} XLSX filing {new_fid} -> {res['status']}")
                if new_fid != fid:
                    with conn.cursor() as c2:
                        c2.execute("DELETE FROM filings WHERE id=%s AND status='pending'", (fid,))
                touched.append(cid)
                conn.commit()
                continue
            os.makedirs("data/reports/auto", exist_ok=True)
            path = f"data/reports/auto/{ticker.lower()}_{year}_q.pdf"
            r = requests.get(url, timeout=180,
                             verify=(os.getenv("REQUESTS_CA_BUNDLE")
                                     or os.getenv("SSL_CERT_FILE") or True))
            r.raise_for_status()
            open(path, "wb").write(r.content)
            slice_text, pages, diag = build_slice(pdf_to_text(path))
            if not slice_text:
                log("extract", cid, "needs_review", f"{ticker}: slice nije lociran ({diag})")
                continue
            if sector == "bank":
                from .extract import extract_bank_filing as _extract
            else:
                from .extract import extract_filing as _extract
            extraction = _extract(slice_text, ticker=ticker)
            new_fid = load_extraction(conn, extraction, source_url=url,
                                      doc_type="financial_report")
            res = validate_filing(conn, new_fid)
            log("extract", cid, "ok" if res["status"] == "validated" else "needs_review",
                f"{ticker}: filing {new_fid} -> {res['status']}")
            if new_fid != fid:  # pending placeholder zamijenjen stvarnim ključem
                with conn.cursor() as c2:
                    c2.execute("DELETE FROM filings WHERE id=%s AND status='pending'", (fid,))
            touched.append(cid)
            conn.commit()
        except Exception as e:  # noqa: BLE001 — izolacija po firmi
            conn.rollback()
            log("extract", cid, "failed", f"{ticker}: {type(e).__name__}: {e}")
    return touched


def stage_recompute(conn, run_id, log, company_ids: list[int]) -> None:
    from .params_calibrated import build_params
    from .valuation_methods import build_ctx, value_company
    for cid in sorted(set(company_ids)):
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT ticker FROM companies WHERE id=%s", (cid,))
                ticker = cur.fetchone()[0]
            ctx = build_ctx(conn, ticker, params=build_params(ticker))
            out = value_company(ctx)
            today = date.today().isoformat()
            rec = out["reconciliation"]
            with conn.cursor() as cur:
                # M17 changelog: pomak sredine zone > 10% vs zadnji snapshot
                # -> red s razlogom IZVEDENIM iz promjene ključnih ulaza
                if rec.get("zone_low") is not None:
                    cur.execute(
                        """SELECT (assumptions->'reconciliation'->>'zone_low')::numeric,
                                  (assumptions->'reconciliation'->>'zone_high')::numeric,
                                  assumptions->'reconciliation'->>'anchor'
                           FROM valuations
                           WHERE company_id=%s AND method='_reconciliation'
                                 AND as_of_date < %s
                           ORDER BY as_of_date DESC LIMIT 1""", (cid, today))
                    prev = cur.fetchone()
                    if prev and prev[0]:
                        old_mid = (float(prev[0]) + float(prev[1])) / 2
                        new_mid = (rec["zone_low"] + rec["zone_high"]) / 2
                        if old_mid and abs(new_mid / old_mid - 1) > 0.10:
                            prim = (rec.get("anchor_methods") or ["?"])[0]
                            why = []
                            if prev[2] and prev[2] != prim:
                                why.append(f"sidro promijenjeno ({prev[2]} -> {prim})")
                            gh = ctx.growth_hint or {}
                            if gh.get("forward"):
                                why.append(f"forward rast {gh['g1']:.1%} ({gh.get('rule')})")
                            why.append("novi ulazi iz zadnjeg izvješća/kalibracije")
                            cur.execute(
                                """INSERT INTO valuation_changelog
                                   (company_id, changed_on, old_low, old_high,
                                    new_low, new_high, reason, kind)
                                   VALUES (%s,%s,%s,%s,%s,%s,%s,'recompute')
                                   ON CONFLICT DO NOTHING""",
                                (cid, today, prev[0], prev[1],
                                 rec["zone_low"], rec["zone_high"],
                                 "; ".join(why)))
                cur.execute("DELETE FROM valuations WHERE company_id=%s AND as_of_date=%s",
                            (cid, today))
                for key, r in out["ran"].items():
                    vr = r["range"]
                    cur.execute(
                        """INSERT INTO valuations (company_id, as_of_date, method,
                             value_low, value_base, value_high, assumptions)
                           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                        (cid, today, key, vr.low, vr.base, vr.high,
                         json.dumps({**vr.assumptions, "confidence": vr.confidence},
                                    default=str)))
                # _reconciliation snapshot (zona + sidro) — osnova za changelog
                cur.execute(
                    """INSERT INTO valuations (company_id, as_of_date, method,
                         value_low, value_base, value_high, assumptions)
                       VALUES (%s,%s,'_reconciliation',NULL,NULL,NULL,%s)""",
                    (cid, today, json.dumps({"reconciliation": {
                        "zone_low": rec.get("zone_low"),
                        "zone_high": rec.get("zone_high"),
                        "anchor": (rec.get("anchor_methods") or [None])[0],
                        "archetype": rec.get("archetype"),
                    }, "skipped": out["skipped"]}, default=str)))
            log("value", cid, "ok", f"{ticker}: revaloriziran ({len(out['ran'])} metoda)")
            conn.commit()
        except Exception as e:  # noqa: BLE001
            conn.rollback()
            log("value", cid, "failed", f"{type(e).__name__}: {e}")


def stage_prices(conn, run_id, log) -> int:
    from .prices import fetch_zse_json
    with conn.cursor() as cur:
        cur.execute(
            """SELECT COALESCE(sc.ticker, c.ticker)
               FROM companies c LEFT JOIN share_classes sc ON sc.company_id=c.id
               WHERE c.is_live ORDER BY 1""")
        tickers = [r[0] for r in cur.fetchall()]
    if not tickers:
        log("prices", None, "skipped", "nema live firmi — cijene se ne dohvaćaju")
        return 0
    try:
        n = fetch_zse_json(tickers, [date.today().isoformat()])
        log("prices", None, "ok", f"{n} EOD zapisa za {len(tickers)} live linija")
        return n
    except Exception as e:  # noqa: BLE001
        log("prices", None, "failed", f"{type(e).__name__}: {e}")
        return 0


def stage_blog(log) -> None:
    """Nightly blog regen (DIO 2): content/blog/*.md -> statični JSON-ovi."""
    import subprocess
    r = subprocess.run(["python", "scripts/build_blog.py"], capture_output=True, text=True)
    log("blog", None, "ok" if r.returncode == 0 else "failed",
        (r.stdout or r.stderr).strip()[:150])


def stage_regen(conn, run_id, log, changed: bool) -> None:
    stage_blog(log)   # blog se regenerira svake noći, neovisno o promjenama
    # M22: dividendni kalendar — statusi ovise o DANAŠNJEM datumu (paid vs
    # nadolazeća), pa se regenerira svake noći neovisno o promjenama podataka
    try:
        import subprocess
        subprocess.run([os.sys.executable, "-m", "scripts.build_dividende"],
                       check=True, capture_output=True, text=True)
        log("regen", None, "ok", "dividende.json regeneriran")
    except Exception as e:  # noqa: BLE001
        log("regen", None, "failed", f"dividende.json: {type(e).__name__}: {e}")
    # M23: MJESEČNI snapshot top 10 dioničara (ZSE/SKDD) — 1. u mjesecu;
    # povijest snapshota se gradi ubuduće (promjene = diff zadnja dva)
    if date.today().day == 1:
        try:
            import subprocess
            subprocess.run([os.sys.executable, "-m", "scripts.scrape_shareholders_zse"],
                           check=True, capture_output=True, text=True, timeout=1800)
            log("regen", None, "ok", "mjesečni snapshot dioničara (ZSE/SKDD)")
        except Exception as e:  # noqa: BLE001
            log("regen", None, "failed", f"snapshot dioničara: {type(e).__name__}: {e}")
    if not changed:
        log("regen", None, "skipped", "ništa se nije promijenilo")
        return
    from .stock_json import build_stock_json
    with conn.cursor() as cur:
        cur.execute("SELECT ticker FROM companies WHERE is_live ORDER BY ticker")
        tickers = [r[0] for r in cur.fetchall()]
    os.makedirs("frontend/public/data", exist_ok=True)
    for t in tickers:
        try:
            data = build_stock_json(conn, t)
            with open(f"frontend/public/data/{t}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            log("regen", None, "ok", f"{t}.json regeneriran")
        except Exception as e:  # noqa: BLE001
            log("regen", None, "failed", f"{t}: {type(e).__name__}: {e}")


def build_digest(conn, run_id: str) -> str:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT stage, status, COUNT(*) FROM pipeline_runs
               WHERE run_id=%s GROUP BY 1,2 ORDER BY 1,2""", (run_id,))
        counts = cur.fetchall()
        cur.execute(
            """SELECT p.stage, c.ticker, p.message FROM pipeline_runs p
               LEFT JOIN companies c ON c.id=p.company_id
               WHERE p.run_id=%s AND p.status IN ('needs_review','failed')
               ORDER BY p.id""", (run_id,))
        problems = cur.fetchall()
        cur.execute(
            "SELECT COUNT(*) FROM pipeline_runs WHERE run_id=%s AND status='needs_review' "
            "AND stage='watcher'", (run_id,))
        low_conf = cur.fetchone()[0]
    lines = [f"# Digest — {run_id}", ""]
    # M19-A: dnevni + mjesečni API trošak s budžetom — bez ovoga trošak
    # raste nevidljivo dok skaliramo
    from . import api_usage
    try:
        lines.append(api_usage.digest_line(conn))
        lines.append("")
    except Exception as e:  # noqa: BLE001 — digest ne pada zbog troška
        lines.append(f"API trošak: n/p ({type(e).__name__})")
        lines.append("")
    lines.append("## Sažetak po koracima")
    for stage, status, n in counts:
        lines.append(f"- {stage}: {status} × {n}")
    if low_conf >= LAYOUT_ALERT_LOW_CONF:
        lines.append(f"\n**ALERT: {low_conf} low-confidence klasifikacija u istom runu — "
                     "moguća promjena formata izvora; auto-akcije pauzirati i pregledati.**")
    lines.append("\n## needs_review / failed (za ručni pregled)")
    if problems:
        for stage, ticker, msg in problems:
            lines.append(f"- [{stage}] {ticker or '—'}: {msg}")
    else:
        lines.append("- ništa 🎉")
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="noćni prolaz (M6)")
    p.add_argument("--digest-only", default=None, help="samo digest za run_id")
    a = p.parse_args(argv)

    with get_conn() as conn:
        if a.digest_only:
            print(build_digest(conn, a.digest_only))
            return 0
        run_id = f"daily-{date.today().isoformat()}"
        log = _logger(conn, run_id)
        from .watcher import run_watcher
        try:
            stats = run_watcher(conn, run_id, log)
            log("watcher", None, "ok", f"feed: {stats}")
            conn.commit()
        except Exception as e:  # noqa: BLE001
            conn.rollback()
            log("watcher", None, "failed", f"{type(e).__name__}: {e}")
        touched = stage_extract_queue(conn, run_id, log)
        stage_recompute(conn, run_id, log, touched)
        n_prices = stage_prices(conn, run_id, log)
        stage_regen(conn, run_id, log, changed=bool(touched or n_prices))
        conn.commit()
        digest = build_digest(conn, run_id)
        os.makedirs("data/digests", exist_ok=True)
        path = f"data/digests/{run_id}.md"
        with open(path, "w", encoding="utf-8") as f:
            f.write(digest)
        print("\n" + digest)
        print(f"\n(digest spremljen u {path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
