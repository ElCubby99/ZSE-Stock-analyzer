"""M17: valuation_changelog — povijest promjena procjene po firmi.

Backfill iz STVARNIH povijesnih snapshotova (valuations._reconciliation,
4.–11.7.) + ručni unosi za metodološke prekretnice prije snapshota. Ubuduće
redove piše daily snapshot (pomak zone > 10% -> automatski red s razlogom
izvedenim iz promjene ulaza) — vidi src/daily.py.

Pokretanje:  python -m scripts.seed_valuation_changelog
"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402

DDL = """
CREATE TABLE IF NOT EXISTS valuation_changelog (
  id          SERIAL PRIMARY KEY,
  company_id  INT NOT NULL REFERENCES companies(id),
  changed_on  DATE NOT NULL,
  old_low     NUMERIC, old_high NUMERIC,
  new_low     NUMERIC, new_high NUMERIC,
  reason      TEXT NOT NULL,
  kind        TEXT NOT NULL DEFAULT 'recompute',  -- methodology|recompute|backfill
  created_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE (company_id, changed_on, reason)
);
"""

# metodološke prekretnice (globalne; stare zone iz snapshota gdje postoje)
MILESTONES = [
    ("2026-07-12", "methodology",
     "Metodologija v2 (M11–M13): rast se izvodi iz forward signala zadnjeg "
     "izvješća (backlog, book-to-bill, guidance) umjesto povijesnog prosjeka; "
     "peer multipli kalibrirani iz baze umjesto placeholdera; zona = sidro ± "
     "osjetljivost umjesto min–max svih metoda. v1 je sustavno podcjenjivao "
     "rast — ovo je izravni popravak."),
    ("2026-07-13", "methodology",
     "Doktrina v2: tri pristupa umjesto zasebnih multipl-metoda (comps s "
     "internom triangulacijom), sidro po arhetipu iz podataka, taksonomija "
     "holding diskonta (integrirani parent 0–5%; izmjereni P/NAV), "
     "confidence gate rekurzivnog SOTP-a, market-implied provjera i red rules."),
]


def main() -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        # zadnji snapshot PRIJE 12.7. po firmi (stara zona za prvu prekretnicu)
        cur.execute("""
            SELECT DISTINCT ON (v.company_id) v.company_id,
                   (v.assumptions->'reconciliation'->>'zone_low')::numeric,
                   (v.assumptions->'reconciliation'->>'zone_high')::numeric
            FROM valuations v
            WHERE v.method='_reconciliation' AND v.as_of_date < '2026-07-12'
              AND v.assumptions->'reconciliation'->>'zone_low' IS NOT NULL
            ORDER BY v.company_id, v.as_of_date DESC""")
        old_zones = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
        # trenutna zona iz exporta (poslije obiju prekretnica)
        import glob
        cur_zones = {}
        for f in glob.glob("frontend/public/data/*.json"):
            if f.endswith("overview.json"):
                continue
            d = json.load(open(f))
            rec = (d.get("valuation") or {}).get("reconciliation") or {}
            if rec.get("zone_low") is None:
                continue
            cur.execute("SELECT id FROM companies WHERE ticker=%s", (d["ticker"],))
            r = cur.fetchone()
            if r:
                cur_zones[r[0]] = (rec["zone_low"], rec["zone_high"], d["ticker"])
        added = 0
        for cid, (lo, hi, tick) in cur_zones.items():
            oz = old_zones.get(cid)
            if oz:
                # dvije prekretnice: v2 metodologija pa doktrina; stara zona
                # poznata samo za prvu — druga nosi kumulativni prijelaz
                cur.execute("""INSERT INTO valuation_changelog
                               (company_id, changed_on, old_low, old_high,
                                new_low, new_high, reason, kind)
                               VALUES (%s,%s,%s,%s,NULL,NULL,%s,'methodology')
                               ON CONFLICT DO NOTHING""",
                            (cid, MILESTONES[0][0], oz[0], oz[1], MILESTONES[0][2]))
                cur.execute("""INSERT INTO valuation_changelog
                               (company_id, changed_on, old_low, old_high,
                                new_low, new_high, reason, kind)
                               VALUES (%s,%s,%s,%s,%s,%s,%s,'methodology')
                               ON CONFLICT DO NOTHING""",
                            (cid, MILESTONES[1][0], oz[0], oz[1], lo, hi,
                             MILESTONES[1][2]))
                added += cur.rowcount
            else:
                cur.execute("""INSERT INTO valuation_changelog
                               (company_id, changed_on, new_low, new_high, reason, kind)
                               VALUES (%s,'2026-07-14',%s,%s,%s,'backfill')
                               ON CONFLICT DO NOTHING""",
                            (cid, lo, hi,
                             "Prva analiza: financije iz standardiziranog TFI "
                             "obrasca (4Q kumulativ FY2025, nerevidirano) + "
                             "doktrina v2 sidro po arhetipu."))
                added += cur.rowcount
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM valuation_changelog")
        print(f"[changelog] upisano; ukupno redova: {cur.fetchone()[0]} (+{added} novih)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
