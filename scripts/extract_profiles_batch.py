#!/usr/bin/env python3
"""Z3.1: profil poslovanja za SVE firme s lokalnim godišnjim izvješćem, a bez
profila u bazi. Budžet-gate (api_usage.allow_extraction, non-urgent) prije
batcha; svaki neuspjeh se ispisuje s razlogom. Izlaz: ekstrahirano / palo /
izvješće ne postoji.

Pokretanje:  python -m scripts.extract_profiles_batch
"""
from __future__ import annotations

import glob
import os
import re
import sys

sys.path.insert(0, ".")

from src import api_usage  # noqa: E402
from src.business_profile import build_profile_slice, extract_profile, load_profile  # noqa: E402
from src.db import get_conn  # noqa: E402


def newest_pdf(tick: str) -> str | None:
    cands = []
    for pat in (f"data/reports/{tick.lower()}_*.pdf",
                f"data/reports/auto/{tick.lower()}_*.pdf"):
        for p in glob.glob(pat):
            m = re.search(r"_(\d{4})", os.path.basename(p))
            if m:
                cands.append((int(m.group(1)), p))
    return max(cands)[1] if cands else None


def main() -> int:
    done, failed, missing = [], [], []
    with get_conn() as conn, conn.cursor() as cur:
        if not api_usage.allow_extraction(conn, urgent=False):
            print("BUDŽET: mjesečni API budžet potrošen — batch odgođen")
            return 1
        cur.execute("""SELECT c.ticker FROM companies c
                       WHERE NOT EXISTS (SELECT 1 FROM business_profiles bp
                                         WHERE bp.company_id=c.id)
                       ORDER BY c.ticker""")
        todo = [t for t, in cur.fetchall()]
    for t in todo:
        pdf = newest_pdf(t)
        if not pdf:
            missing.append(t)
            continue
        try:
            p = extract_profile(build_profile_slice(pdf), ticker=t)
            if not p.get("activity"):
                failed.append((t, "ekstrakcija bez 'activity' (isječak bez opisa poslovanja)"))
                continue
            with get_conn() as conn:
                load_profile(conn, t, p,
                             source=f"API ekstrakcija ({pdf}, početak izvješća)")
            done.append(t)
            print(f"[profil] {t}: OK ({os.path.basename(pdf)})")
        except Exception as e:  # noqa: BLE001
            failed.append((t, f"{type(e).__name__}: {str(e)[:80]}"))
            print(f"[profil] {t}: PALO — {type(e).__name__}: {str(e)[:80]}")
    print(f"\nEKSTRAHIRANO ({len(done)}): {', '.join(done)}")
    print(f"PALO ({len(failed)}):")
    for t, why in failed:
        print(f"  {t}: {why}")
    print(f"IZVJEŠĆE NE POSTOJI LOKALNO ({len(missing)}): {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
