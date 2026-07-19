"""M41-1: učitaj 45 business-profila (HR) + EN prijevode u business_profiles.

Ulaz: scratchpad/bp_all_45.json (HR) + bp_en_batch_{A,B,C}.json (EN).
Insert/upsert po company_id; JSONB stupci. Ne dira valuacije.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import src.db as db

S = pathlib.Path("/tmp/claude-0/-home-user-ZSE-Stock-analyzer/"
                 "bb2e6cb3-8fb7-5416-83d2-f5f529dd7764/scratchpad")


def _year(*texts) -> int:
    for t in texts:
        if not t:
            continue
        m = re.search(r"(20\d{2})", str(t))
        if m:
            return int(m.group(1))
    return 2025


def main(apply: bool) -> int:
    hr = json.load(open(S / "bp_all_45.json", encoding="utf-8"))
    en = {}
    for b in ("A", "B", "C"):
        en.update(json.load(open(S / f"bp_en_batch_{b}.json", encoding="utf-8")))

    missing_en = [t for t in hr if t not in en]
    if missing_en:
        print("NEDOSTAJE EN za:", missing_en)
        return 2

    with db.get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT ticker, id FROM companies")
        cid = dict(cur.fetchall())
        n_ins = 0
        no_company = []
        for t, p in sorted(hr.items()):
            if t not in cid:
                no_company.append(t)
                continue
            bp_en = en[t]
            # sanity: broj elemenata mora se poklapati (overlay po indexu)
            for k_hr, k_en in (("segments", "segments"), ("markets", "markets"),
                               ("issuer_claims", "claims")):
                if len(p.get(k_hr) or []) != len(bp_en.get(k_en) or []):
                    print(f"  MISMATCH {t}.{k_hr}: HR={len(p.get(k_hr) or [])} "
                          f"EN={len(bp_en.get(k_en) or [])}")
                    return 3
            fy = _year(p.get("activity_source_page"), p.get("source"))
            if not apply:
                print(f"  [dry] {t}: fy={fy} seg={len(p.get('segments') or [])} "
                      f"mkt={len(p.get('markets') or [])} "
                      f"claims={len(p.get('issuer_claims') or [])} "
                      f"exp={'da' if p.get('export_share') else 'ne'}")
                continue
            cur.execute(
                """INSERT INTO business_profiles (company_id, fiscal_year, activity,
                     activity_source_page, segments, markets, export_share,
                     issuer_claims, source, bp_en)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (company_id) DO UPDATE SET
                     fiscal_year=EXCLUDED.fiscal_year, activity=EXCLUDED.activity,
                     activity_source_page=EXCLUDED.activity_source_page,
                     segments=EXCLUDED.segments, markets=EXCLUDED.markets,
                     export_share=EXCLUDED.export_share,
                     issuer_claims=EXCLUDED.issuer_claims, source=EXCLUDED.source,
                     bp_en=EXCLUDED.bp_en""",
                (cid[t], fy, p.get("activity"), p.get("activity_source_page"),
                 json.dumps(p.get("segments"), ensure_ascii=False) if p.get("segments") is not None else None,
                 json.dumps(p.get("markets"), ensure_ascii=False) if p.get("markets") is not None else None,
                 json.dumps(p.get("export_share"), ensure_ascii=False) if p.get("export_share") is not None else None,
                 json.dumps(p.get("issuer_claims"), ensure_ascii=False) if p.get("issuer_claims") is not None else None,
                 p.get("source"),
                 json.dumps(bp_en, ensure_ascii=False)))
            n_ins += 1
        if no_company:
            print("NEMA U companies (preskočeno):", no_company)
        print(f"{'UPISANO' if apply else 'DRY'} profila: {n_ins}/{len(hr)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--apply" in sys.argv))
