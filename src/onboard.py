"""Tiered onboarding (M6) — docs/zse_orchestrator_spec.md + IZMJENA:
korak `sector_assigned` između entity_resolved i extracting (sektor s
confidenceom bira extraction template i valuacijske metode).

State machine (po firmi):
  discovered -> entity_resolved -> sector_assigned -> filings_found
             -> extracting -> validating -> [group?] holdings_built -> valued
             -> (live | needs_review | failed)

Pravila:
- Tier 1 = aktualni CROBEX10, dohvaćen ŽIVO (src/index_universe.py).
- Gateovi nisu tihi: svaki korak loga u pipeline_runs; dvojbe -> needs_review.
- Promocija u live: Tier 1 ISKLJUČIVO ručno (`--promote TICKER`); auto-promocije
  ovdje NEMA. Idempotentno: live firme i već ekstrahirani filinzi se preskaču.
- Izolacija greške: pad jedne firme ne prekida run.
- Ništa izmišljeno: podatak bez izvora ostaje prazan + razlog u needs_review.

CLI:
  python -m src.onboard --tier 1              # obradi Tier 1 i STANI (report)
  python -m src.onboard --tier 1 --ticker HPB # samo jedna firma
  python -m src.onboard --promote ADRS        # ručna potvrda -> live (Tier 1)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

from . import eho
from .auto_slice import build_slice
from .classify import MIN_CONFIDENCE, classify_sector
from .db import get_conn
from .index_universe import fetch_composition
from .loader import load_extraction
from .pdf_extract import pdf_to_text
from .validator import validate_filing

MANIFEST_DIR = "data/manifests"
AUTO_REPORT_DIR = "data/reports/auto"


# ---------- infrastruktura ----------
def log(conn, run_id: str, stage: str, company_id, status: str, message: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pipeline_runs (run_id, stage, company_id, status, message) "
            "VALUES (%s,%s,%s,%s,%s)",
            (run_id, stage, company_id, status, message[:1500]))
    print(f"  [{stage}] {status}: {message[:160]}")


def set_state(conn, company_id: int, state: str) -> None:
    with conn.cursor() as cur:
        cur.execute("UPDATE companies SET onboarding_status=%s WHERE id=%s",
                    (state, company_id))


# ---------- koraci ----------
def resolve_company(conn, run_id: str, member: dict) -> tuple[int | None, str | None]:
    """Constituent (klasa!) -> company_id. KODT vs KOEI zaštita: identitet po ISIN-u."""
    sym, isin, name = member["symbol"], member["isin"], member["name"]
    with conn.cursor() as cur:
        cur.execute("SELECT company_id FROM share_classes WHERE isin=%s OR ticker=%s",
                    (isin, sym))
        r = cur.fetchone()
        if r:
            cur.execute("SELECT ticker FROM companies WHERE id=%s", (r[0],))
            return r[0], cur.fetchone()[0]
        cur.execute("SELECT id, ticker, isin FROM companies WHERE ticker=%s", (sym,))
        r = cur.fetchone()
        if r:
            cid, tkr, known_isin = r
            if known_isin and known_isin != isin:
                log(conn, run_id, "onboard:entity", cid, "needs_review",
                    f"ISIN nesklad za {sym}: baza {known_isin} vs indeks {isin} — "
                    f"mogući krivi izdavatelj (KODT/KOEI zamka)")
                set_state(conn, cid, "needs_review")
                return None, None
            return cid, tkr
        # nova firma: ticker = simbol klase; ime SLUŽBENO iz sastava indeksa
        cur.execute(
            "INSERT INTO companies (ticker, name, sector, is_group) "
            "VALUES (%s,%s,NULL,FALSE) RETURNING id", (sym, name))
        cid = cur.fetchone()[0]
        class_type = "preferred" if "PA0" in isin else "ordinary"
        cur.execute(
            """INSERT INTO share_classes (company_id, ticker, isin, class_type,
                 shares_issued, has_voting, dividend_note, is_primary_line)
               VALUES (%s,%s,%s,%s,NULL,NULL,
                       'broj dionica NEPOZNAT — čeka izvor (ekstrakcija/GS)',TRUE)
               ON CONFLICT (ticker) DO NOTHING""",
            (cid, sym, isin, class_type))
        log(conn, run_id, "onboard:entity", cid, "ok",
            f"nova firma {sym} ({name}); broj dionica nepoznat dok se ne izvuče")
        return cid, sym


def stage_entity(conn, run_id: str, cid: int, ticker: str, member: dict) -> dict | None:
    """Manifest izvora (URL-ovi izvješća s EHO feeda) + potvrda izdavatelja."""
    d = eho.feed("financialReports", ticker=ticker,
                 date_from="2022-01-01", date_to=date.today().isoformat())
    items = d.get("items") or []
    if not items:
        log(conn, run_id, "onboard:entity", cid, "needs_review",
            f"{ticker}: EHO feed nema financijskih izvješća — ne mogu potvrditi izvore")
        return None
    os.makedirs(MANIFEST_DIR, exist_ok=True)
    manifest = {"ticker": ticker, "constituent_symbol": member["symbol"],
                "constituent_isin": member["isin"], "official_name": member["name"],
                "reports": [{k: it.get(k) for k in
                             ("year", "period", "consolidated", "revised",
                              "documentType", "documentLink", "publishDate")}
                            for it in items]}
    with open(f"{MANIFEST_DIR}/{ticker}.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    log(conn, run_id, "onboard:entity", cid, "ok",
        f"{ticker}: manifest {len(items)} objava FI -> {MANIFEST_DIR}/{ticker}.json")
    set_state(conn, cid, "entity_resolved")
    return manifest


def stage_sector(conn, run_id: str, cid: int, ticker: str, name: str) -> str | None:
    """IZMJENA speca: sektor s confidenceom PRIJE ekstrakcije."""
    with conn.cursor() as cur:
        cur.execute("SELECT sector, sector_confidence FROM companies WHERE id=%s", (cid,))
        sector, conf = cur.fetchone()
    if sector and conf is not None:
        log(conn, run_id, "onboard:sector", cid, "ok",
            f"{ticker}: sektor '{sector}' već dodijeljen (conf {conf})")
        set_state(conn, cid, "sector_assigned")
        return sector
    if sector and conf is None:
        # ručno dodijeljen i izvorima potvrđen u M1–M5 (seed/citati)
        with conn.cursor() as cur:
            cur.execute("UPDATE companies SET sector_confidence=0.95 WHERE id=%s", (cid,))
        log(conn, run_id, "onboard:sector", cid, "ok",
            f"{ticker}: sektor '{sector}' ručno dodijeljen u M1–M5 -> conf 0.95")
        set_state(conn, cid, "sector_assigned")
        return sector
    # dokazi: službeno ime + naslovi nedavnih objava
    try:
        news = eho.feed("issuerNews", ticker=ticker, date_from="2025-07-01",
                        date_to=date.today().isoformat())
        titles = [it.get("title", "") for it in (news.get("items") or [])[:12]]
    except Exception:  # noqa: BLE001
        titles = []
    res = classify_sector(ticker, name, "\n".join(titles) or "(nema objava)")
    sec, c, why = res["sector"], float(res["confidence"]), res["rationale"]
    if c < MIN_CONFIDENCE or sec == "other":
        log(conn, run_id, "onboard:sector", cid, "needs_review",
            f"{ticker}: klasifikacija '{sec}' conf {c:.2f} < {MIN_CONFIDENCE} — {why}")
        set_state(conn, cid, "needs_review")
        return None
    with conn.cursor() as cur:
        cur.execute("UPDATE companies SET sector=%s, sector_confidence=%s WHERE id=%s",
                    (sec, c, cid))
    log(conn, run_id, "onboard:sector", cid, "ok",
        f"{ticker}: sektor '{sec}' (conf {c:.2f}) — {why[:120]}")
    set_state(conn, cid, "sector_assigned")
    return sec


def pick_report(manifest: dict) -> dict | None:
    """Najnovije godišnje izvješće: kons. PDF > kons. ZIP (ESEF) > nekons. PDF/ZIP."""
    items = [r for r in manifest["reports"] if r.get("period") == "1Y"]
    for cons in (True, False):
        for dtype in ("PDF", "ZIP"):
            cand = [r for r in items if bool(r.get("consolidated")) == cons
                    and r.get("documentType") == dtype]
            if cand:
                cand.sort(key=lambda r: (r.get("year") or 0, bool(r.get("revised"))),
                          reverse=True)
                return cand[0]
    return None


def stage_filings(conn, run_id: str, cid: int, ticker: str, manifest: dict) -> dict | None:
    rep = pick_report(manifest)
    if rep is None:
        log(conn, run_id, "onboard:filings", cid, "needs_review",
            f"{ticker}: nema godišnjeg PDF/ZIP izvješća u manifestu — ručni korak")
        set_state(conn, cid, "needs_review")
        return None
    with conn.cursor() as cur:
        cur.execute("UPDATE companies SET is_group=%s WHERE id=%s",
                    (bool(rep.get("consolidated")), cid))
    log(conn, run_id, "onboard:filings", cid, "ok",
        f"{ticker}: FY{rep['year']} {'kons.' if rep['consolidated'] else 'nekons.'} "
        f"PDF ({rep['publishDate'][:10]})")
    set_state(conn, cid, "filings_found")
    return rep


# --- M6 popravak 3: promotion gate — JEZGRENI skup po templateu.
# Nizak confidence na sporednoj stavci NE blokira ako su jezgreni ulazi
# visoki (>=0.85) i metode prošle. Jezgreno = nazivnik (broj dionica,
# rješava ga stage_shares) + ove grupe alternativa:
CORE_ITEM_GROUPS = {
    "bank":    [("equity_parent", "total_equity"),
                ("net_income_parent", "net_income"),
                ("total_operating_income",)],
    "default": [("equity_parent", "total_equity"),
                ("net_income_parent", "net_income"),
                ("revenue",)],
}
CORE_CONF = 0.85


def core_gate(conn, fid: int, sector: str) -> tuple[list[str], list[str]]:
    """-> (blokirajući razlozi, ne-blokirajuće napomene) za filing."""
    groups = CORE_ITEM_GROUPS["bank" if sector == "bank" else "default"]
    core_flat = {i for g in groups for i in g}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT item, value_eur, confidence FROM financials "
            "WHERE filing_id=%s AND is_reported", (fid,))
        rows = {i: (v, float(c) if c is not None else None) for i, v, c in cur.fetchall()}
    blocking, notes = [], []
    for g in groups:
        ok = any(i in rows and rows[i][0] is not None
                 and (rows[i][1] or 0) >= CORE_CONF for i in g)
        if not ok:
            have = {i: rows[i][1] for i in g if i in rows}
            blocking.append(f"jezgrena grupa {g} nedostaje ili conf<{CORE_CONF} ({have})")
    lows = [f"{i}={c:.2f}" for i, (v, c) in rows.items()
            if c is not None and c < CORE_CONF]
    core_lows = [s for s in lows if s.split("=")[0] in core_flat
                 or s.split("=")[0] == "shares_outstanding"]
    side_lows = [s for s in lows if s not in core_lows]
    if core_lows:
        blocking.append(f"nizak confidence na JEZGRENIM stavkama: {', '.join(core_lows)}")
    if side_lows:
        notes.append(f"sporedne stavke ispod praga (ne blokira): {', '.join(side_lows[:8])}")
    return blocking, notes


# --- M6 popravak 2: rezolucija broja dionica kao ZASEBAN korak.
def fetch_listed_quantity(isin: str) -> int | None:
    """'Uvrštena količina' sa službene zse.hr stranice papira (listing podatak)."""
    import re as _re
    import requests

    r = requests.get("https://zse.hr/hr/papir/310", params={"isin": isin},
                     timeout=40, verify=(os.getenv("REQUESTS_CA_BUNDLE")
                                         or os.getenv("SSL_CERT_FILE") or True))
    r.raise_for_status()
    txt = _re.sub(r"<[^>]+>", " ", r.text)
    m = _re.search(r"Uvrštena\s+količina\s*([\d.]+)", txt)
    if not m:
        return None
    return int(m.group(1).replace(".", ""))


def stage_shares(conn, run_id: str, cid: int, ticker: str, member: dict) -> list[str]:
    """Osiguraj nazivnik za per-share metode; bez njega n/p (NE nula)."""
    with conn.cursor() as cur:
        cur.execute("SELECT shares_ex_treasury FROM v_shares_canonical WHERE company_id=%s",
                    (cid,))
        r = cur.fetchone()
        if r and r[0]:
            log(conn, run_id, "onboard:shares", cid, "ok",
                f"{ticker}: {float(r[0]):,.0f} dionica (share_classes)")
            return []
        cur.execute(
            """SELECT fin.value_eur FROM financials fin JOIN filings f ON f.id=fin.filing_id
               WHERE f.company_id=%s AND fin.item='shares_outstanding'
               ORDER BY f.fiscal_year DESC LIMIT 1""", (cid,))
        r = cur.fetchone()
        if r and r[0]:
            log(conn, run_id, "onboard:shares", cid, "ok",
                f"{ticker}: {float(r[0]):,.0f} dionica (iz ekstrakcije)")
            return []
        # fallback: službeni ZSE listing (Uvrštena količina) po ISIN-u klase
        cur.execute("SELECT id, ticker, isin FROM share_classes WHERE company_id=%s", (cid,))
        classes = cur.fetchall()
    if not classes and member.get("isin"):
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO share_classes (company_id, ticker, isin, class_type,
                     shares_issued, is_primary_line, dividend_note)
                   VALUES (%s,%s,%s,%s,NULL,TRUE,'kreirano u stage_shares (M6)')
                   ON CONFLICT (ticker) DO NOTHING""",
                (cid, member["symbol"], member["isin"],
                 "preferred" if "PA0" in member["isin"] else "ordinary"))
            cur.execute("SELECT id, ticker, isin FROM share_classes WHERE company_id=%s", (cid,))
            classes = cur.fetchall()
    filled = 0
    for sc_id, sc_ticker, sc_isin in classes:
        if not sc_isin:
            continue
        try:
            qty = fetch_listed_quantity(sc_isin)
        except Exception as e:  # noqa: BLE001
            log(conn, run_id, "onboard:shares", cid, "failed",
                f"{ticker}/{sc_ticker}: dohvat listinga pao ({e})")
            continue
        if qty:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE share_classes SET shares_issued=%s,
                         treasury_shares=COALESCE(treasury_shares, 0),
                         dividend_note=COALESCE(dividend_note,'') ||
                           ' | broj dionica = Uvrštena količina (zse.hr papir, listing); trezorske NEPOZNATE (0 uz ogradu)'
                       WHERE id=%s AND shares_issued IS NULL""", (qty, sc_id))
                filled += cur.rowcount
            log(conn, run_id, "onboard:shares", cid, "ok",
                f"{ticker}/{sc_ticker}: {qty:,.0f} dionica (zse.hr 'Uvrštena količina'; "
                "trezorske nepoznate -> 0 uz ogradu)")
    if filled:
        return []
    log(conn, run_id, "onboard:shares", cid, "needs_review",
        f"{ticker}: broj dionica NEDOSTUPAN (ni ekstrakcija ni ZSE listing) — "
        "per-share metode ostaju n/p")
    return ["broj dionica nedostupan — per-share metode n/p"]


def already_extracted(conn, cid: int, year: int, basis: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT 1 FROM filings WHERE company_id=%s AND fiscal_year=%s
               AND period_type='annual' AND basis=%s AND doc_type='financial_report'
               AND status IN ('validated','needs_review','extracted')""",
            (cid, year, basis))
        return cur.fetchone() is not None


def stage_extract_validate(conn, run_id: str, cid: int, ticker: str, sector: str,
                           rep: dict) -> tuple[bool, list[str]]:
    """Ekstrakcija (template po SEKTORU) + validate gate. -> (ok, razlozi_review)."""
    basis = "consolidated" if rep.get("consolidated") else "standalone"
    year = rep.get("year")
    if already_extracted(conn, cid, year, basis):
        log(conn, run_id, "onboard:extract", cid, "skipped",
            f"{ticker}: FY{year}/{basis} već u bazi (idempotentno)")
    else:
        from .esef import download, zip_to_text
        os.makedirs(AUTO_REPORT_DIR, exist_ok=True)
        url = (rep.get("documentLink") or "").replace("\\/", "/")
        dtype = rep.get("documentType")
        if dtype == "ZIP":
            # ESEF ruta (prvorazredna): ZIP -> xhtml (ili unutarnji PDF) -> slice
            from .auto_slice import build_slice_chars
            path = f"{AUTO_REPORT_DIR}/{ticker.lower()}_{year}.zip"
            download(url, path)
            text, kind = zip_to_text(path)
            if kind == "pdf":
                slice_text, pages, diag = build_slice(text)
                diag = f"ZIP s unutarnjim PDF-om; {diag}"
            else:
                slice_text, pages, diag = build_slice_chars(text)
        else:
            path = f"{AUTO_REPORT_DIR}/{ticker.lower()}_{year}.pdf"
            download(url, path)
            text = pdf_to_text(path)
            slice_text, pages, diag = build_slice(text)
        if not slice_text:
            log(conn, run_id, "onboard:extract", cid, "needs_review",
                f"{ticker}: izvještaji nisu locirani u PDF-u ({diag})")
            set_state(conn, cid, "needs_review")
            return False, [f"slice nije lociran ({diag})"]
        set_state(conn, cid, "extracting")
        if sector == "bank":
            from .extract import extract_bank_filing as _extract
        else:
            from .extract import extract_filing as _extract
        try:
            extraction = _extract(slice_text)
        except RuntimeError as e:
            if "max_tokens" not in str(e):
                raise
            log(conn, run_id, "onboard:extract", cid, "ok",
                f"{ticker}: izlaz odrezan — retry s max_tokens=32000")
            extraction = _extract(slice_text, max_tokens=32000)
        ext_t = extraction["meta"].get("company_ticker")
        if ext_t != ticker:
            # identitet je potvrđen u entity_resolved; GFI oznake tipa 'HPB-R-A'
            # normaliziramo na ticker firme (rezolucija, ne izmjena podataka)
            log(conn, run_id, "onboard:extract", cid, "ok",
                f"{ticker}: meta ticker '{ext_t}' normaliziran na '{ticker}'")
            extraction["meta"]["company_ticker"] = ticker
        fid = load_extraction(conn, extraction, source_url=url,
                              doc_type="financial_report",
                              published_at=(rep.get("publishDate") or "")[:10] or None)
        log(conn, run_id, "onboard:extract", cid, "ok",
            f"{ticker}: filing {fid} (FY{extraction['meta']['fiscal_year']} "
            f"{extraction['meta']['basis']}; template={'bank' if sector == 'bank' else 'industrial'}; "
            f"slice str {pages[:8]}{'...' if len(pages) > 8 else ''})")
    # validate gate + PROMOTION GATE (M6 popravak 3): strukturna pravila (1–6)
    # blokiraju uvijek; nizak confidence blokira SAMO na jezgrenim stavkama.
    set_state(conn, cid, "validating")
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id FROM filings WHERE company_id=%s AND fiscal_year=%s
               AND period_type='annual' AND basis=%s AND doc_type='financial_report'""",
            (cid, year, basis))
        row = cur.fetchone()
    if row is None:
        return False, ["filing nije nastao"]
    fid = row[0]
    res = validate_filing(conn, fid)
    rule_fails = [f"{r['rule']}: {r['detail']}" for r in res["results"]
                  if r["status"] in ("FAIL", "WARN") and r["rule"] != "7_confidence"]
    blocking, notes = core_gate(conn, fid, sector)
    blocking = rule_fails + blocking
    if blocking:
        log(conn, run_id, "onboard:validate", cid, "needs_review",
            f"{ticker}: filing {fid} BLOKIRAN: " + "; ".join(blocking)[:300])
        return True, blocking      # nastavljamo do valued, ali NE u live
    msg = f"{ticker}: filing {fid} prolazi promotion gate (jezgra čista)"
    if notes:
        msg += " — " + "; ".join(notes)
    log(conn, run_id, "onboard:validate", cid, "ok", msg)
    return True, []


def stage_holdings(conn, run_id: str, cid: int, ticker: str) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT is_group FROM companies WHERE id=%s", (cid,))
        is_group = bool(cur.fetchone()[0])
        if not is_group:
            log(conn, run_id, "onboard:holdings", cid, "skipped",
                f"{ticker}: nije grupa — n/p")
            return
        cur.execute("SELECT COUNT(*) FROM holdings WHERE parent_company_id=%s", (cid,))
        n = cur.fetchone()[0]
    if n:
        log(conn, run_id, "onboard:holdings", cid, "ok",
            f"{ticker}: vlasnički graf postoji ({n} udjela)")
    else:
        # NE blokira: SOTP gate u motoru sam preskače bez udjela/segmenata,
        # ali korak NIJE tih — vidljivo u logu i digestu.
        log(conn, run_id, "onboard:holdings", cid, "skipped",
            f"{ticker}: grupa BEZ vlasničkog grafa — SOTP neće biti dostupan "
            "(izgradnja grafa je zaseban, citiran korak)")
    set_state(conn, cid, "holdings_built")


def stage_valued(conn, run_id: str, cid: int, ticker: str) -> list[str]:
    from .params_calibrated import build_params
    from .valuation_methods import build_ctx, value_company
    params = build_params(ticker)
    ctx = build_ctx(conn, ticker, params=params)
    out = value_company(ctx)
    today = date.today().isoformat()
    with conn.cursor() as cur:
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
        cur.execute(
            """INSERT INTO valuations (company_id, as_of_date, method,
                 value_low, value_base, value_high, assumptions)
               VALUES (%s,%s,'_reconciliation',NULL,NULL,NULL,%s)""",
            (cid, today, json.dumps({"reconciliation": out["reconciliation"],
                                     "skipped": out["skipped"]}, default=str)))
    ran_ok = [k for k, r in out["ran"].items() if r["range"].base]
    msg = (f"{ticker}: metode s vrijednošću: {ran_ok or 'NEMA'}; "
           f"preskočene: {list(out['skipped'])}")
    if not ran_ok:
        why = ("broj dionica nepoznat (nije u sliceu ni u share_classes) — "
               "per-share metode nemaju nazivnik" if not ctx.shares_ex_treasury
               else "nedostaju ulazi (vidi assumptions.missing)")
        log(conn, run_id, "onboard:value", cid, "needs_review", f"{msg} — {why}")
        return [f"nijedna metoda nije dala vrijednost: {why}"]
    log(conn, run_id, "onboard:value", cid, "ok", msg)
    set_state(conn, cid, "valued")
    return []


def process_company(conn, run_id: str, member: dict, tier: int) -> dict:
    """Cijeli state machine za jednu firmu; izolirana greška."""
    result = {"symbol": member["symbol"], "name": member["name"], "ticker": None,
              "state": None, "sector": None, "sector_conf": None, "reasons": []}
    try:
        cid, ticker = resolve_company(conn, run_id, member)
        if cid is None:
            result["state"] = "needs_review"
            result["reasons"].append("identitet izdavatelja (ISIN nesklad)")
            return result
        result["ticker"] = ticker
        with conn.cursor() as cur:
            cur.execute("UPDATE companies SET tier=%s WHERE id=%s AND tier IS NULL",
                        (tier, cid))
            cur.execute("SELECT is_live, onboarding_status, name FROM companies WHERE id=%s", (cid,))
            is_live, status, name = cur.fetchone()
        if is_live:
            result["state"] = "live"
            log(conn, run_id, "onboard:entity", cid, "skipped", f"{ticker}: već live")
            return result

        manifest = stage_entity(conn, run_id, cid, ticker, member)
        if manifest is None:
            result["state"] = "needs_review"
            result["reasons"].append("nema izvora izvješća na EHO feedu")
            return result

        sector = stage_sector(conn, run_id, cid, ticker, name or member["name"])
        if sector is None:
            result["state"] = "needs_review"
            result["reasons"].append("sektor nejasan (conf < 0.85) — ručna dodjela")
            return result

        rep = stage_filings(conn, run_id, cid, ticker, manifest)
        if rep is None:
            result["state"] = "needs_review"
            result["reasons"].append("nema godišnjeg PDF izvješća (možda samo ZIP)")
            return result

        cont, review_reasons = stage_extract_validate(conn, run_id, cid, ticker, sector, rep)
        result["reasons"].extend(review_reasons)
        if not cont:
            result["state"] = "needs_review"
            return result

        result["reasons"].extend(stage_shares(conn, run_id, cid, ticker, member))
        stage_holdings(conn, run_id, cid, ticker)
        result["reasons"].extend(stage_valued(conn, run_id, cid, ticker))

        final = "valued" if not result["reasons"] else "needs_review"
        set_state(conn, cid, final)
        result["state"] = final
    except Exception as e:  # noqa: BLE001 — izolacija po firmi
        conn.rollback()   # očisti pokvarenu transakciju da iduća firma radi
        result["state"] = "failed"
        result["reasons"].append(f"{type(e).__name__}: {e}")
        try:
            if result.get("ticker"):
                with conn.cursor() as cur:
                    cur.execute("UPDATE companies SET onboarding_status='failed' "
                                "WHERE ticker=%s", (result["ticker"],))
            log(conn, run_id, "onboard:error", None, "failed",
                f"{member['symbol']}: {type(e).__name__}: {e}")
        except Exception:  # noqa: BLE001
            pass
    finally:
        with conn.cursor() as cur:
            if result["ticker"]:
                cur.execute("SELECT sector, sector_confidence FROM companies WHERE ticker=%s",
                            (result["ticker"],))
                r = cur.fetchone()
                if r:
                    result["sector"], result["sector_conf"] = r[0], r[1] and float(r[1])
    return result


def report(results: list[dict]) -> None:
    print("\n" + "=" * 86)
    print("TIER 1 ONBOARDING — REZULTAT (promocija u live ČEKA ručnu potvrdu)")
    print("=" * 86)
    print(f"{'clan':7} {'firma':8} {'stanje':13} {'sektor':11} {'conf':5}  needs_review razlozi")
    for r in results:
        conf = f"{r['sector_conf']:.2f}" if r["sector_conf"] is not None else "—"
        reasons = "; ".join(r["reasons"]) or "—"
        print(f"{r['symbol']:7} {(r['ticker'] or '?'):8} {(r['state'] or '?'):13} "
              f"{(r['sector'] or '—'):11} {conf:5}  {reasons[:120]}")
    n = {"valued": 0, "needs_review": 0, "failed": 0, "live": 0}
    for r in results:
        n[r["state"]] = n.get(r["state"], 0) + 1
    print("-" * 86)
    print(f"UKUPNO: {len(results)} | valued (čeka potvrdu): {n['valued']} | "
          f"needs_review: {n['needs_review']} | failed: {n['failed']} | live: {n['live']}")


def promote(ticker: str) -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, onboarding_status FROM companies WHERE ticker=%s", (ticker,))
        r = cur.fetchone()
        if not r:
            print(f"nepoznat ticker {ticker}")
            return 1
        cid, status = r
        if status != "valued":
            print(f"{ticker}: status '{status}' — promocija dozvoljena samo iz 'valued' "
                  f"(needs_review prvo riješi pa ponovi onboarding)")
            return 1
        cur.execute("UPDATE companies SET is_live=TRUE, onboarding_status='live' "
                    "WHERE id=%s", (cid,))
        print(f"{ticker}: PROMOVIRAN u live (ručna potvrda).")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="tiered onboarding (M6)")
    p.add_argument("--tier", type=int, choices=[1], help="pokreni onboarding tiera")
    p.add_argument("--ticker", default=None, help="ograniči na jednu članicu (symbol)")
    p.add_argument("--promote", default=None, help="ručna promocija firme u live")
    a = p.parse_args(argv)

    if a.promote:
        return promote(a.promote.upper())
    if a.tier != 1:
        p.error("za sada je podržan samo --tier 1 (Tier 2 tek nakon ručne potvrde Tiera 1)")

    run_id = f"onboard-t1-{date.today().isoformat()}"
    members = fetch_composition("CROBEX10")
    print(f"CROBEX10 (živo, {len(members)} članica): "
          f"{', '.join(m['symbol'] for m in members)}")
    if a.ticker:
        members = [m for m in members if m["symbol"] == a.ticker.upper()]

    results = []
    with get_conn() as conn:
        for m in members:
            print(f"\n== {m['symbol']} — {m['name']}")
            results.append(process_company(conn, run_id, m, tier=1))
            conn.commit()
    report(results)
    print("\nSTOP: Tier 2 ne počinje dok Tier 1 nije ručno potvrđen "
          "(python -m src.onboard --promote TICKER).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
