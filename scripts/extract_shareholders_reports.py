#!/usr/bin/env python3
"""M23 izvor 1 (povijesni): top 10 dioničara iz LOKALNIH godišnjih izvješća.

STROGI deterministički parser (bez LLM-a): traži marker '(10) najvećih
dioničara' / 'Vlasnička struktura' u tekstu PDF-a, zatim čita trojke
rang -> ime -> postotak. Prihvaća SAMO ako se parsira >= 5 redova i suma
<= 100,5 % — sve ostalo se preskače s razlogom (radije rupa nego kriva
tablica). Snapshot_date = 31.12. fiskalne godine (stanje iz godišnjeg
izvješća); svaki red citira PDF i stranicu markera.

Pokretanje:  python -m scripts.extract_shareholders_reports
"""
from __future__ import annotations

import datetime
import glob
import os
import re
import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402
from src.pdf_extract import pdf_to_text  # noqa: E402

CUSTODY_RX = re.compile(
    r"skrbni|custody|zbirni ra[čc]un|fiducia|client acc|/", re.I)
MARKER_RX = re.compile(
    r"(10|[Dd]eset)\s*NAJVE[ĆC]IH\s*\n?\s*DIONI[ČC]ARA|"
    r"najve[ćc]ih\s+dioni[čc]ara|"
    r"VLASNI[ČC]KA\s+STRUKTURA|[Dd]ioni[čc]ka\s+struktura", re.I)
# red: '1.' ili '1' na svojoj liniji, pa ime (1-2 linije), pa postotak
ROW_RX = re.compile(
    r"^\s*(\d{1,2})\.?\s*\n"          # rang
    r"((?:[^\n%]{3,90}\n){1,2}?)"     # ime (1-2 linije, bez %)
    r"\s*(\d{1,2}[.,]\d{1,2})\s*%?\s*$",  # udio
    re.M)


def _parse_columnar(seg: str) -> list[dict] | None:
    """Kolonarni PDF oblik (npr. PODR): blok imena iza retka 'Dioničar' do
    'Ukupno', zatim blok postotaka koji ZAVRŠAVA s 100,0% (Ukupno). Strogi
    gate: broj imena == broj postotaka i zadnji pct == 100."""
    hm = re.search(r"^\s*Dioni[čc]ar\s*$", seg, re.M)
    if not hm:
        return None
    names, rest = [], seg[hm.end():]
    lines = rest.splitlines()
    i = 0
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s:
            continue
        if re.match(r"^Ukupno\b", s, re.I):
            names.append("Ukupno")
            break
        if re.match(r"^\d{1,3}[.,]\d{1,2}\s*%?$", s):
            return None          # postotci prije 'Ukupno' -> nije ovaj oblik
        if 3 <= len(s) <= 90:
            names.append(s)
    else:
        return None
    pcts = []
    for ln in lines[i + 1:]:
        s = ln.strip()
        pm = re.match(r"^(\d{1,3}[.,]\d{1,2})\s*%$", s)
        if pm:
            pcts.append(float(pm.group(1).replace(",", ".")))
            if abs(pcts[-1] - 100.0) < 0.01:
                break
        elif pcts and s and not pm:
            break                # blok postotaka je prekinut
    if (len(names) != len(pcts) or not pcts or abs(pcts[-1] - 100.0) > 0.01):
        return None
    rows = []
    for rank, (name, pct) in enumerate(zip(names, pcts), start=1):
        if re.match(r"^(Ukupno|Ostali dioni[čc]ari)\b", name, re.I):
            continue             # zbirni retci nisu top-imatelji
        rows.append({"rank": rank, "name": name, "pct": pct,
                     "is_custody": bool(CUSTODY_RX.search(name))})
    if len(rows) < 5 or sum(r["pct"] for r in rows) > 100.5:
        return None
    return rows


def parse_pdf(path: str) -> tuple[list[dict], str] | None:
    """Proba SVAKI marker u dokumentu (rangirani i kolonarni oblik) — prvi
    segment koji prođe strogi gate pobjeđuje; nijedan -> None (rupa, ne
    kriva tablica)."""
    text = pdf_to_text(path)
    for m in MARKER_RX.finditer(text):
        seg = text[m.start():m.start() + 2500]
        rows = []
        for rm in ROW_RX.finditer(seg):
            rank = int(rm.group(1))
            name = " ".join(rm.group(2).split())
            try:
                pct = float(rm.group(3).replace(",", "."))
            except ValueError:
                continue
            if 1 <= rank <= 10 and 0 < pct <= 100 and len(name) >= 3:
                # kolona 'broj dionica' zna doći zalijepljena uz ime u PDF
                # flowu ("Marko Pipunić 12.831.940") -> odvoji u shares
                shares = None
                sm = re.search(r"\s(\d{1,3}(?:\.\d{3})+|\d{4,})$", name)
                if sm:
                    shares = float(sm.group(1).replace(".", ""))
                    name = name[:sm.start()].strip()
                rows.append({"rank": rank, "name": name, "pct": pct,
                             "shares": shares,
                             "is_custody": bool(CUSTODY_RX.search(name))})
        # strogi gate: >= 5 redova, rangovi UZASTOPNI od 1 (rupa u rangu =
        # fragmentiran PDF flow -> krivo bi izostavio najveće imatelje),
        # suma <= 100.5
        ranks = sorted(r["rank"] for r in rows)
        if (len(rows) < 5 or ranks != list(range(1, len(rows) + 1))
                or sum(r["pct"] for r in rows) > 100.5):
            rows = _parse_columnar(seg) or []
        if rows:
            page_m = None
            for pm in re.finditer(r"=+ STRANICA (\d+) =+", text[:m.start()]):
                page_m = pm.group(1)
            return rows, (f"str. {page_m}" if page_m else "str. n/p")
    return None


def main() -> int:
    ok = skipped = 0
    with get_conn() as conn, conn.cursor() as cur:
        pdfs = sorted(glob.glob("data/reports/*.pdf")
                      + glob.glob("data/reports/auto/*.pdf"))
        for path in pdfs:
            base = os.path.basename(path)
            fm = re.match(r"([a-z0-9]+)_(\d{4})", base)
            if not fm:
                continue
            tick, fy = fm.group(1).upper(), int(fm.group(2))
            if fy < 2024:            # FY2024 i FY2025 (dva snapshota)
                continue
            cur.execute("SELECT id FROM companies WHERE ticker=%s", (tick,))
            r = cur.fetchone()
            if not r:
                skipped += 1
                continue
            cid = r[0]
            try:
                parsed = parse_pdf(path)
            except Exception as e:  # noqa: BLE001
                print(f"[izvješće] {base}: greška čitanja ({str(e)[:50]})")
                skipped += 1
                continue
            if not parsed:
                print(f"[izvješće] {base}: tablica nije nađena/strogi gate pao -> preskačem")
                skipped += 1
                continue
            rows, page = parsed
            snap = datetime.date(fy, 12, 31)
            for row in rows:
                cur.execute(
                    """INSERT INTO shareholders (company_id, snapshot_date,
                         source, source_detail, rank, holder_name, shares, pct,
                         is_custody)
                       VALUES (%s,%s,'annual_report',%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (company_id, snapshot_date, source, rank)
                       DO UPDATE SET holder_name=EXCLUDED.holder_name,
                         shares=EXCLUDED.shares, pct=EXCLUDED.pct,
                         is_custody=EXCLUDED.is_custody,
                         source_detail=EXCLUDED.source_detail""",
                    (cid, snap, f"{base}, {page} (godišnje izvješće FY{fy})",
                     row["rank"], row["name"], row.get("shares"), row["pct"],
                     row["is_custody"]))
            conn.commit()
            ok += 1
            print(f"[izvješće] {base}: {len(rows)} redova (snapshot {snap}, {page})")
    print(f"\nGOTOVO: izvješća s tablicom={ok}, preskočeno={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
