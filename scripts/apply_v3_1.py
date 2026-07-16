#!/usr/bin/env python3
"""v3.1: primjena dividendnog poda (DIO 1) + kompozitnog g1 (DIO 2).

Za svaku live firmu: stara zona iz OBJAVLJENOG per-stock JSON-a
(frontend/public/data/<T>.json — stvarno stanje weba prije v3.1) ->
nova zona -> red u valuation_changelog s kind='methodology' i ISTINITIM
razlogom kad se sredina zone pomakne > 10%. Imena kojima je zona bila
SUSPENDIRANA ('u rekalibraciji' — objavljeni JSON bez zone) dobivaju
changelog red sa starim vrijednostima NULL i posebnim razlogom.
Novi valuations snapshot za danas (kao daily recompute).

Pokretanje: python -m scripts.apply_v3_1
"""
import json
import pathlib
import sys
from datetime import date

sys.path.insert(0, ".")

DATA = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "public" / "data"


def _published_zone(ticker):
    """(zone_low, zone_high) iz objavljenog JSON-a ili (None, None)."""
    p = DATA / f"{ticker}.json"
    if not p.exists():
        return None, None
    try:
        rec = (json.loads(p.read_text(encoding="utf-8"))
               .get("valuation") or {}).get("reconciliation") or {}
        return rec.get("zone_low"), rec.get("zone_high")
    except Exception:  # noqa: BLE001
        return None, None


from src.db import get_conn                      # noqa: E402
from src.params_calibrated import build_params   # noqa: E402
from src.valuation_methods import build_ctx, value_company  # noqa: E402

REASON = ("Metodologija v3.1: kompozitna stopa rasta g1 (medijan signala "
          "serija / održivi rast iz zadržane dobiti / terminalno sidro, "
          "cap nakon medijana, uvijek ispod troška kapitala) + dividendni "
          "pod (Gordonova vrijednost održive dividende ulazi u zonu umjesto "
          "da je suspendira). Detalji na stranici Metodologija.")

REASON_UNSUSPEND = ("Metodologija v3.1: zona je bila privremeno povučena "
                    "('u rekalibraciji') jer je padala na dividendnom sanity "
                    "testu — to je bila dizajnerska greška; održiva dividenda "
                    "sada kao dividendni pod ULAZI u zonu (Gordonov izračun) "
                    "pa je zona ponovno objavljena. Detalji na stranici "
                    "Metodologija.")


def main() -> int:
    today = date.today()
    moved, small, unsuspended, failed = [], [], [], []
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, ticker FROM companies WHERE is_live ORDER BY ticker")
            companies = cur.fetchall()
        for cid, ticker in companies:
            try:
                ctx = build_ctx(conn, ticker, params=build_params(ticker))
                out = value_company(ctx)
                rec = out["reconciliation"]
                if rec.get("status") == "no_value" or rec.get("zone_low") is None:
                    continue
                old_lo, old_hi = _published_zone(ticker)
                with conn.cursor() as cur:
                    new_lo, new_hi = rec["zone_low"], rec["zone_high"]
                    if old_lo and old_hi:
                        shift = ((new_lo + new_hi) / 2) / ((old_lo + old_hi) / 2) - 1
                        row = (ticker, old_lo, old_hi, new_lo, new_hi, shift)
                        if abs(shift) > 0.10:
                            cur.execute(
                                """INSERT INTO valuation_changelog
                                   (company_id, changed_on, old_low, old_high,
                                    new_low, new_high, reason, kind)
                                   VALUES (%s,%s,%s,%s,%s,%s,%s,'methodology')
                                   ON CONFLICT DO NOTHING""",
                                (cid, today, old_lo, old_hi, new_lo, new_hi, REASON))
                            moved.append(row)
                        else:
                            small.append(row)
                    else:
                        # zona je bila suspendirana/neobjavljena -> sada postoji
                        cur.execute(
                            """INSERT INTO valuation_changelog
                               (company_id, changed_on, old_low, old_high,
                                new_low, new_high, reason, kind)
                               VALUES (%s,%s,NULL,NULL,%s,%s,%s,'methodology')
                               ON CONFLICT DO NOTHING""",
                            (cid, today, new_lo, new_hi, REASON_UNSUSPEND))
                        unsuspended.append((ticker, new_lo, new_hi))
                    # dnevni snapshot metoda + _reconciliation (kao stage_recompute)
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
                        (cid, today, json.dumps({"reconciliation": {
                            "zone_low": rec.get("zone_low"),
                            "zone_high": rec.get("zone_high"),
                            "anchor": (rec.get("anchor_methods") or [None])[0],
                            "archetype": rec.get("archetype")}}, default=str)))
                conn.commit()
            except Exception as e:  # noqa: BLE001 — izolacija po firmi
                conn.rollback()
                failed.append((ticker, str(e)[:120]))
    print(f"ponovno objavljene zone — bile suspendirane ({len(unsuspended)}):")
    for t, nl, nh in unsuspended:
        print(f"  {t:6} (bez zone) -> {nl:,.2f}–{nh:,.2f}")
    print(f"pomak >10% ({len(moved)}):")
    for t, ol, oh, nl, nh, s in sorted(moved, key=lambda x: -abs(x[5])):
        print(f"  {t:6} {ol:,.2f}–{oh:,.2f} -> {nl:,.2f}–{nh:,.2f}  ({s:+.1%})")
    print(f"pomak <=10% ({len(small)}):",
          ", ".join(f"{t} {s:+.1%}" for t, *_, s in small))
    if failed:
        print(f"GREŠKE ({len(failed)}):", failed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
