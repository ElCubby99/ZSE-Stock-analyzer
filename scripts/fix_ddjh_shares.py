"""M56: DDJH — ispravak broja dionica.

ZSE stranica papira (i naš onboarding iz nje) nosi 'Uvrštena količina'
101.532 — ali to je samo dio dionica uvršten na burzu. Društvo prema
Pozivu na Glavnu skupštinu 27.8.2026. (EHO objava #67717) ima temeljni
kapital podijeljen na UKUPNO 28.350.832 dionice (svaka 1 glas). Fer
vrijednost po dionici mora se računati na SVE dionice — s uvrštenom
količinom bila je ~279x napuhana (zona 687 € umjesto ~2,5 €).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.db import get_conn  # noqa: E402

TOTAL = 28_350_832
NOTE = ("broj dionica = UKUPAN temeljni kapital: 28.350.832 dionica (Poziv na "
        "Glavnu skupštinu 27.8.2026., EHO objava #67717) — na ZSE je uvršteno "
        "samo 101.532 dionica (0,36%), pa se burzovna cijena formira na "
        "minijaturnom uvrštenom ostatku i nije reprezentativna za cijelu firmu")


def main() -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""UPDATE share_classes sc SET shares_issued=%s, dividend_note=%s
                       FROM companies c WHERE c.id=sc.company_id AND c.ticker='DDJH'
                       RETURNING sc.ticker, sc.shares_issued""", (TOTAL, NOTE))
        print("updated:", cur.fetchall())
        conn.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
