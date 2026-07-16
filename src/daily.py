"""Dnevni prolaz (M6, Dio C; od M32 na GitHub Actions u 16:20 nakon
zatvaranja ZSE) + digest (Dio D). Jedan run_id; redoslijed bitan:
  1. watcher  2. extract_queue  3. recompute  4. prices_eod  5. regen  6. digest

Robusnost: izolacija greške po firmi/koraku (jedan pad ne ruši run),
idempotentno (dedup po ID-evima, ON CONFLICT), validate gate uvijek.
Detekcija promjene layouta: previše low-confidence klasifikacija u istom runu
-> alert u digestu + pauza auto-akcija (auto-promocija ovdje ionako ne postoji).

M34 satni pokušaji (zamjena za M32 retry-sleep): workflow pokreće run
SVAKI SAT 16:20 -> 22:20 Europe/Zagreb. Svaki run je kratak i bez spavanja:
  1. idempotentni guard — današnji EOD već kompletan u bazi? -> "already
     done", exit 0, nula posla i nula deploya;
  2. jedan pokušaj dohvata tečajnice — nema podataka? -> "not yet
     published", exit 0 (neutralno; čekanje rade cron termini). SAMO
     zadnji dnevni pokušaj (lokalno >= EOD_FINAL_HOUR, zadano 22) bez
     podataka vraća exit 3 -> workflow failure + issue + mail (jedan
     alarm dnevno);
  3. s podacima: backfill jučerašnje rupe ako je izvor nudi, pa puni
     prolaz (watcher/extract/recompute/regen) točno JEDNOM taj dan.
Istek bez podataka NE dira postojeće stanje (exporti se ne prepisuju,
deploy se ne okida). Runner je efemeran: sve trajno stanje živi u
Postgresu (ZSE_DSN -> Supabase) i u exportima commitanima u repo.

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
        # Log NIKAD ne smije srušiti run (incident 16.07.2026.: aborted
        # transakcija -> log() digao InFailedSqlTransaction i ubio prolaz).
        # Na grešku: rollback pa jedan retry; ako ni to ne prođe, samo print.
        for _ in range(2):
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO pipeline_runs (run_id, stage, company_id, status, message) "
                        "VALUES (%s,%s,%s,%s,%s)",
                        (run_id, stage, company_id, status, str(message)[:1500]))
                break
            except Exception:  # noqa: BLE001
                try:
                    conn.rollback()
                except Exception:  # noqa: BLE001
                    break
        print(f"[{stage}] {status}: {str(message)[:150]}")
    return log


def ensure_schema(conn) -> None:
    """Primijeni idempotentnu shemu (db/zse_schema_v3_1.sql) na početku runa.

    Lokalni razvoj dodaje stupce/tablice — bez ovoga produkcijska baza
    razjaše od koda (incident 16.07.2026.: regen pao na stupcima koji su
    postojali samo lokalno). IF NOT EXISTS => no-op kad je sve već tu."""
    import pathlib
    sql = (pathlib.Path(__file__).resolve().parents[1]
           / "db" / "zse_schema_v3_1.sql").read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


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
    from .sotp_order import CycleError, ordered_tickers
    from .valuation_methods import build_ctx, value_company
    # v3 FAZA SOTP: preračun topološkim redom (kćeri prije matica)
    with conn.cursor() as cur:
        cur.execute("SELECT id, ticker FROM companies WHERE id = ANY(%s)",
                    (sorted(set(company_ids)),))
        id_of = {t: i for i, t in cur.fetchall()}
    try:
        ordered = ordered_tickers(conn, sorted(id_of))
    except CycleError as e:
        log("recompute", None, "failed", str(e))
        raise
    for cid in [id_of[t] for t in ordered]:
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


def _zagreb_now():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Europe/Zagreb"))


def _live_class_tickers(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT COALESCE(sc.ticker, c.ticker)
               FROM companies c LEFT JOIN share_classes sc ON sc.company_id=c.id
               WHERE c.is_live ORDER BY 1""")
        return [r[0] for r in cur.fetchall()]


# Kompletan dan = udio live linija s današnjim zapisom >= prag. Tečajnica
# se objavljuje ODJEDNOM (jedan JSON za sve papire), pa je stvarni ishod
# binaran: ~0% ili ~90%+ (netrgovani papiri nemaju close). Prag 0,5 je
# sigurnosna margina, ne fina granica.
EOD_COMPLETE_MIN_SHARE = float(os.getenv("EOD_COMPLETE_MIN_SHARE", "0.5"))


def eod_already_done(conn, day: date | None = None) -> bool:
    """Idempotentni guard (prvi korak svakog satnog runa): ima li baza VEĆ
    kompletan EOD za zadani (default današnji) trgovinski dan?"""
    day = day or date.today()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM companies WHERE is_live")
        if not cur.fetchone()[0]:
            return False
        cur.execute(
            """SELECT COUNT(*) FROM (
                 SELECT COALESCE(sc.ticker, c.ticker) AS t
                 FROM companies c LEFT JOIN share_classes sc ON sc.company_id=c.id
                 WHERE c.is_live) live""")
        n_live = cur.fetchone()[0]
        cur.execute(
            """SELECT COUNT(DISTINCT (p.company_id, COALESCE(p.share_class_id, 0)))
               FROM prices_eod p JOIN companies c ON c.id=p.company_id
               WHERE c.is_live AND p.trade_date=%s""", (day,))
        n_have = cur.fetchone()[0]
    return n_live > 0 and n_have / n_live >= EOD_COMPLETE_MIN_SHARE


def previous_trading_day(day: date) -> date:
    """Prethodni radni dan (pon-pet). Praznike ne modeliramo — rupa zbog
    praznika se ne backfilla jer izvor za taj dan nema tečajnicu."""
    from datetime import timedelta
    d = day - timedelta(days=1)
    while d.weekday() >= 5:   # 5=subota, 6=nedjelja
        d -= timedelta(days=1)
    return d


def stage_prices(conn, run_id, log, fetch=None) -> tuple[int, bool]:
    """JEDAN kratki pokušaj dohvata današnje tečajnice (bez spavanja —
    čekanje na kasnu ZSE objavu rade satni cron termini, ne runner).

    Vraća (broj_zapisa, not_ready). not_ready=True znači: izvor još nema
    današnje podatke — pozivatelj izlazi neutralno (job SUCCESS), a failure
    podiže SAMO zadnji dnevni pokušaj. Uz uspješan dohvat dodatno zakrpa
    rupu za PRETHODNI trgovinski dan ako je izvor nudi (backfill)."""
    if fetch is None:
        from .prices import fetch_zse_json as fetch

    tickers = _live_class_tickers(conn)
    if not tickers:
        log("prices", None, "skipped", "nema live firmi — cijene se ne dohvaćaju")
        return 0, False

    today = date.today()
    try:
        n = fetch(tickers, [today.isoformat()])
    except Exception as e:  # noqa: BLE001
        log("prices", None, "failed", f"dohvat pao: {type(e).__name__}: {e}")
        return 0, True
    if not n:
        log("prices", None, "skipped",
            f"tečajnica za {today} još nije objavljena — sljedeći pokušaj "
            "radi sljedeći satni cron")
        return 0, True

    log("prices", None, "ok", f"{n} EOD zapisa za {len(tickers)} live linija")
    # Backfill: jučerašnja rupa (npr. dan kad ZSE ništa nije objavio do
    # 22:20) — ako izvor sad nudi i taj datum, serija ne ostaje šupljikava.
    prev = previous_trading_day(today)
    if not eod_already_done(conn, prev):
        try:
            n_prev = fetch(tickers, [prev.isoformat()])
            log("prices", None, "ok" if n_prev else "skipped",
                f"backfill {prev}: {n_prev} EOD zapisa"
                if n_prev else f"backfill {prev}: izvor nema tečajnicu za taj dan")
        except Exception as e:  # noqa: BLE001
            log("prices", None, "failed",
                f"backfill {prev} pao: {type(e).__name__}: {e}")
    return n, False


def stage_blog(log) -> None:
    """Blog regen (DIO 2): content/blog/*.md -> statični JSON-ovi."""
    import subprocess
    r = subprocess.run(["python", "scripts/build_blog.py"], capture_output=True, text=True)
    log("blog", None, "ok" if r.returncode == 0 else "failed",
        (r.stdout or r.stderr).strip()[:150])


def stage_regen(conn, run_id, log, changed: bool) -> None:
    stage_blog(log)   # blog se regenerira svaki run, neovisno o promjenama
    # M22: dividendni kalendar — statusi ovise o DANAŠNJEM datumu (paid vs
    # nadolazeća), pa se regenerira svaki run neovisno o promjenama podataka
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
    from .sotp_order import CycleError, ordered_tickers
    from .stock_json import build_stock_json
    with conn.cursor() as cur:
        cur.execute("SELECT ticker FROM companies WHERE is_live ORDER BY ticker")
        tickers = [r[0] for r in cur.fetchall()]
    # v3 FAZA SOTP: kćeri PRIJE matica (topološki red); ciklus = greška
    try:
        tickers = ordered_tickers(conn, tickers)
    except CycleError as e:
        log("regen", None, "failed", str(e))
        raise
    os.makedirs("frontend/public/data", exist_ok=True)
    for t in tickers:
        try:
            data = build_stock_json(conn, t)
            with open(f"frontend/public/data/{t}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            log("regen", None, "ok", f"{t}.json regeneriran")
        except Exception as e:  # noqa: BLE001
            # rollback OBAVEZAN: pola izvršenog SQL-a ostavlja transakciju
            # aborted i ruši SVE sljedeće tickere (incident 16.07.2026.)
            conn.rollback()
            log("regen", None, "failed", f"{t}: {type(e).__name__}: {e}")
    # M32: overview.json (naslovnica/screener/usporedba + datum svježine u
    # headeru i prerenderu) MORA pratiti nove cijene — bez ovoga bi datum
    # na sajtu ostajao star iako su per-stock exporti svježi
    try:
        import subprocess
        subprocess.run([os.sys.executable, "-m", "scripts.build_overview"],
                       check=True, capture_output=True, text=True)
        log("regen", None, "ok", "overview.json regeneriran")
    except Exception as e:  # noqa: BLE001
        log("regen", None, "failed", f"overview.json: {type(e).__name__}: {e}")
    # M-IDX: indeksi.json (kartice + serije + sastavnice + temperatura)
    try:
        import subprocess
        subprocess.run([os.sys.executable, "-m", "scripts.build_indeksi"],
                       check=True, capture_output=True, text=True)
        log("regen", None, "ok", "indeksi.json regeneriran")
    except Exception as e:  # noqa: BLE001
        log("regen", None, "failed", f"indeksi.json: {type(e).__name__}: {e}")

    # v3 P.2: distribucijski alarm (top-20 likvidnih) — exit 2 = alarm;
    # zapisuje calibration_alert u overview.json (banner na /metodologija),
    # a workflow na alarm otvara issue s labelom calibration-review
    try:
        import subprocess
        r_al = subprocess.run([os.sys.executable, "-m", "scripts.distribucijski_alarm"],
                              capture_output=True, text=True)
        log("regen", None, "ok" if r_al.returncode == 0 else "failed",
            f"distribucijski alarm: {(r_al.stdout or '').strip()[-200:]}")
    except Exception as e:  # noqa: BLE001
        log("regen", None, "failed", f"distribucijski alarm: {e}")
    # M-BOND: obveznice.json (tablica + YTM/duracija + rasporedi kupona)
    try:
        import subprocess
        subprocess.run([os.sys.executable, "-m", "scripts.build_obveznice"],
                       check=True, capture_output=True, text=True)
        log("regen", None, "ok", "obveznice.json regeneriran")
    except Exception as e:  # noqa: BLE001
        log("regen", None, "failed", f"obveznice.json: {type(e).__name__}: {e}")
    # M25: EOD update -> okini Vercel build (prerender po dionici čita svježe
    # exporte). Hook URL NIJE u repou — env VERCEL_DEPLOY_HOOK_URL (README).
    hook = os.environ.get("VERCEL_DEPLOY_HOOK_URL")
    if hook:
        try:
            import requests
            r = requests.post(hook, timeout=30)
            r.raise_for_status()
            log("regen", None, "ok", "Vercel deploy hook okinut (prerender/SEO build)")
        except Exception as e:  # noqa: BLE001
            log("regen", None, "failed", f"deploy hook: {type(e).__name__}: {e}")
    else:
        log("regen", None, "skipped", "VERCEL_DEPLOY_HOOK_URL nije postavljen — build se ne okida")


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


def _attempt_no() -> tuple[int, int]:
    """(N, M) za log "pokušaj N od M" — iz lokalnog sata (termini 16:20 →
    22:20, svaki sat => 7 pokušaja; N clipan u [1, 7])."""
    h = _zagreb_now().hour
    return max(1, min(7, h - 15)), 7


def _is_final_attempt() -> bool:
    """Zadnji dnevni pokušaj = lokalni sat >= EOD_FINAL_HOUR (zadano 22).
    Samo on smije failati kad podataka nema (jedan alarm dnevno, ne po satu)."""
    return _zagreb_now().hour >= int(os.getenv("EOD_FINAL_HOUR", "22"))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="dnevni prolaz (M6/M32; satni pokušaji)")
    p.add_argument("--digest-only", default=None, help="samo digest za run_id")
    a = p.parse_args(argv)

    with get_conn() as conn:
        if a.digest_only:
            print(build_digest(conn, a.digest_only))
            return 0
        run_id = f"daily-{date.today().isoformat()}"
        log = _logger(conn, run_id)

        # 0. shema: idempotentne migracije — lokalna i produkcijska baza
        #    ne smiju razjahati (uzrok pada 16.07.2026.)
        try:
            ensure_schema(conn)
        except Exception as e:  # noqa: BLE001
            conn.rollback()
            log("schema", None, "failed", f"{type(e).__name__}: {e}")

        # 1. idempotentni guard: dan već kompletan -> no-op od par sekundi
        #    (satna serija je sigurna: nakon prvog uspjeha ostali runovi
        #    tog dana ne rade ništa i NE diraju exporte/deploy)
        if eod_already_done(conn):
            log("prices", None, "skipped",
                "already done — današnji EOD je već kompletan u bazi")
            print("already done")
            return 0

        # 2. kratki pokušaj povlačenja (bez spavanja — čekanje rade cronovi)
        n_prices, not_ready = stage_prices(conn, run_id, log)
        if not_ready:
            n_att, m_att = _attempt_no()
            if _is_final_attempt():
                # 3. alarm SAMO na zadnjem dnevnom pokušaju (exit 3 ->
                #    workflow failure + issue + mail; raniji pokušaji šute)
                log("prices", None, "failed",
                    f"EOD za {date.today()} nije objavljen do zadnjeg "
                    f"pokušaja ({n_att}/{m_att}) — zadržano prethodno stanje")
                conn.commit()
                return 3
            log("prices", None, "skipped",
                f"podaci još nisu objavljeni, pokušaj {n_att} od {m_att} — "
                "izlazim neutralno (SUCCESS), sljedeći cron ponavlja")
            conn.commit()
            print("not yet published")
            return 0

        # 3. podaci su tu -> puni prolaz (watcher/extract/recompute se rade
        #    JEDNOM dnevno, u runu koji je našao podatke — ne 7x)
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
        # M-IDX: indeksi (vrijednosti + sastavnice) — rupa: do M-IDX se
        # index_eod nikad nije ažurirao u dnevnom prolazu
        try:
            from .indices import refresh_constituents, update_index_eod
            n_idx = update_index_eod(conn, log=lambda m: None)
            refresh_constituents(conn, log=lambda m: None)
            log("indices", None, "ok", f"{n_idx} EOD zapisa indeksa + sastavnice")
        except Exception as e:  # noqa: BLE001
            conn.rollback()
            log("indices", None, "failed", f"{type(e).__name__}: {e}")
            n_idx = 0
        # M-BOND: obveznice (master iz tečajnice + EOD cijene u % nominale)
        try:
            from .bonds import sync_master, update_prices
            sync_master(conn, log=lambda m: None)
            n_bond = update_prices(conn, log=lambda m: None)
            log("bonds", None, "ok", f"{n_bond} EOD zapisa obveznica")
        except Exception as e:  # noqa: BLE001
            conn.rollback()
            log("bonds", None, "failed", f"{type(e).__name__}: {e}")
            n_bond = 0
        stage_regen(conn, run_id, log, changed=bool(touched or n_prices or n_idx or n_bond))
        conn.commit()
        digest = build_digest(conn, run_id)
        os.makedirs("data/digests", exist_ok=True)
        path = f"data/digests/{run_id}.md"
        with open(path, "w", encoding="utf-8") as f:
            f.write(digest)
        print("\n" + digest)
        print(f"\n(digest spremljen u {path})")
    # exit 3 se vraća RANIJE, samo iz zadnjeg dnevnog pokušaja bez podataka;
    # dovde stižemo isključivo s uspješno povučenim cijenama -> 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
