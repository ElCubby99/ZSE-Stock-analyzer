#!/usr/bin/env python3
"""NALOG M30 faza 1 + M72: upis ručno generiranih rundi i forumskih tema
(data/discussions/*.json, data/discussions/topics/*.json)
u bazu kao DRAFT. Pokreće se kroz db-sync workflow (discussions_seed=true)
nad produkcijom (ZSE_DSN) ili lokalno. Idempotentno: runda (ticker,
round_no) se pri ponovnom učitavanju ZAMJENJUJE (AI postovi + calls);
ljudski komentari se NE diraju. Objava je isključivo Borisov klik u /admin.

Validacija ista kao u discussion-publish Edge Functionu: AI post bez citata
ili sa zabranjenim izrazom (MAR) ruši datoteku.
"""
from __future__ import annotations

import glob
import json
import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402
from src.summons import forbidden_hit  # noqa: E402

SRC = "data/discussions"
MAX_BODY = 2600


def _check(doc: dict, fn: str) -> None:
    d = doc["discussion"]
    assert d["ticker"] and int(d["round_no"]) >= 1, f"{fn}: ticker/round_no"
    assert d.get("data_snapshot"), f"{fn}: data_snapshot obavezan"
    assert doc.get("posts"), f"{fn}: nema postova"
    kind = d.get("kind", "ai_round")
    assert kind in ("ai_round", "topic"), f"{fn}: kind"
    if kind == "topic":
        assert d.get("slug"), f"{fn}: topic bez sluga"
        assert d.get("title_hr") and d.get("title_en"), f"{fn}: topic bez naslova"
    for p in doc["posts"]:
        who = p.get("agent_id", "?")
        assert p.get("body_hr", "").strip(), f"{fn}/{who}: prazan body_hr"
        assert p.get("citations"), f"{fn}/{who}: AI post bez citata"
        assert len(p["body_hr"]) <= MAX_BODY, f"{fn}/{who}: predug post"
        assert len(p.get("body_en") or "") <= MAX_BODY, f"{fn}/{who}: predug EN"
        for txt in (p["body_hr"], p.get("body_en") or ""):
            hit = forbidden_hit(txt)
            assert not hit, f"{fn}/{who}: MAR filter ({hit})"
    for c in doc.get("calls", []):
        assert c["stance"] in ("below_zone", "in_zone", "above_zone"), \
            f"{fn}/{c.get('agent_id')}: stance"
        assert c.get("invalidation_condition", "").strip(), \
            f"{fn}/{c.get('agent_id')}: invalidation_condition"
    for key in ("summary_hr", "summary_en"):
        hit = forbidden_hit(d.get(key) or "")
        assert not hit, f"{fn}: MAR filter u {key} ({hit})"


def load_file(cur, path: str) -> str:
    doc = json.load(open(path, encoding="utf-8"))
    _check(doc, path)
    d = doc["discussion"]
    cur.execute("""SELECT id FROM discussions WHERE ticker=%s AND round_no=%s""",
                (d["ticker"], d["round_no"]))
    row = cur.fetchone()
    args = (d["ticker"], d["round_no"], d.get("trigger", "manual"),
            json.dumps(d["data_snapshot"], ensure_ascii=False),
            d.get("summary_hr"), d.get("summary_en"),
            json.dumps(d.get("agree_points") or [], ensure_ascii=False),
            json.dumps(d.get("disagree_points") or [], ensure_ascii=False),
            json.dumps(d.get("questions_for_humans") or [], ensure_ascii=False),
            d.get("kind", "ai_round"), d.get("slug"),
            d.get("title_hr"), d.get("title_en"),
            d.get("related_href"), d.get("related_href_en"))
    if row:
        disc_id = row[0]
        cur.execute("""UPDATE discussions SET ticker=%s, round_no=%s, trigger=%s,
                         data_snapshot=%s, summary_hr=%s, summary_en=%s,
                         agree_points=%s, disagree_points=%s,
                         questions_for_humans=%s, kind=%s, slug=%s,
                         title_hr=%s, title_en=%s, related_href=%s,
                         related_href_en=%s
                       WHERE id=%s""", (*args, disc_id))
        # M77: reseed briše SAMO protokolarne postove runde (volley_no
        # postavljen u seed datotekama); "živi" AI postovi — event-komentari
        # i odgovori na @spomene (volley_no NULL) — preživljavaju reseed
        cur.execute("""DELETE FROM discussion_posts
                       WHERE discussion_id=%s AND author_type='ai'
                         AND volley_no IS NOT NULL""", (disc_id,))
        cur.execute("DELETE FROM agent_calls WHERE discussion_id=%s", (disc_id,))
    else:
        cur.execute("""INSERT INTO discussions (ticker, round_no, trigger,
                         data_snapshot, summary_hr, summary_en, agree_points,
                         disagree_points, questions_for_humans, kind, slug,
                         title_hr, title_en, related_href, related_href_en,
                         status)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                               'draft')
                       RETURNING id""", args)
        disc_id = cur.fetchone()[0]
    for p in doc["posts"]:
        cur.execute("""INSERT INTO discussion_posts (discussion_id, author_type,
                         agent_id, volley_no, body_hr, body_en, citations,
                         status, model_used, cost_usd)
                       VALUES (%s,'ai',%s,%s,%s,%s,%s,'published',%s,0)""",
                    (disc_id, p["agent_id"], p.get("volley_no"),
                     p["body_hr"], p.get("body_en"),
                     json.dumps(p["citations"], ensure_ascii=False),
                     p.get("model_used", "claude-code-manual")))
    for c in doc.get("calls", []):
        cur.execute("""INSERT INTO agent_calls (discussion_id, agent_id, ticker,
                         stance, horizon_months, price_at_call, zone_low,
                         zone_high, invalidation_condition)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (disc_id, c["agent_id"], d["ticker"], c["stance"],
                     c.get("horizon_months", 12), c.get("price_at_call"),
                     c.get("zone_low"), c.get("zone_high"),
                     c["invalidation_condition"]))
    return d["ticker"]


def main() -> int:
    # runde po dionicama + forumske teme (ETF-ovi, mirovinski fondovi)
    files = sorted(glob.glob(f"{SRC}/*.json")) + sorted(glob.glob(f"{SRC}/topics/*.json"))
    if not files:
        print(f"[rasprave] nema datoteka u {SRC}/")
        return 0
    with get_conn() as conn, conn.cursor() as cur:
        for path in files:
            t = load_file(cur, path)
            print(f"[rasprave] {t}: runda učitana kao draft ({path})")
        conn.commit()
    print(f"[rasprave] GOTOVO: {len(files)} rundi u draftu — objava u /admin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
