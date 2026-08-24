#!/usr/bin/env python3
"""NALOG M30: orkestrator AI rasprava — SKELET za buduće automatske runde.

DISCUSSIONS_ENABLED je default 'false' i sve ispod flaga je NO-OP dok ga
Boris ne uključi u workflow env-u. Faza 1 rundi je generirana ručno
(data/discussions/*.json + scripts/load_discussions.py) — ovaj skript ne
radi nijedan API poziv dok je flag isključen, a i s uključenim flagom
odbija raditi bez ANTHROPIC_API_KEY_BURZOVNILIST (zaseban Console
Workspace ključ; glavni ključ se NIKAD ne koristi).

Dizajn (kad se uključi):
- trigger: tjedni cron + event iz pipelinea (novo izvješće / dividenda)
- Anthropic BATCH API (runde nisu vremenski kritične; 50% jeftinije) +
  prompt caching za role_prompt i data_snapshot
- prije SVAKOG poziva: provjera global_cost_cap_usd_day iz usage_limits;
  probijen cap = stop + zapis + jedan alarm mail na info@
- upis kroz Edge Function discussion-publish (x-api-key) — isti obrazac
  kao blog-publish; validacija i MAR filter su TAMO (i ovdje, dvostruko)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

sys.path.insert(0, ".")

from src.db import get_conn  # noqa: E402
from src.summons import SummonContext, decide_summon, forbidden_hit  # noqa: E402

FLAG = os.environ.get("DISCUSSIONS_ENABLED", "false").lower() == "true"
API_KEY = os.environ.get("ANTHROPIC_API_KEY_BURZOVNILIST")


def _limits(cur) -> dict:
    cur.execute("SELECT key, value_int FROM usage_limits")
    return dict(cur.fetchall())


def cost_today_usd(cur) -> float:
    cur.execute("""SELECT COALESCE(SUM(cost_usd), 0) FROM discussion_posts
                   WHERE created_at >= date_trunc('day', now())""")
    return float(cur.fetchone()[0] or 0)


def cap_ok(cur) -> bool:
    """Globalni dnevni cap na trošak — provjera PRIJE svakog poziva."""
    lim = _limits(cur)
    return cost_today_usd(cur) < float(lim.get("global_cost_cap_usd_day", 5))


def pending_summons(cur) -> list[tuple]:
    cur.execute("""SELECT id, discussion_id, agent_id, user_id
                   FROM agent_summons WHERE status='queued'
                   ORDER BY created_at LIMIT 50""")
    return cur.fetchall()


def process_summons(conn) -> int:
    """Obrada reda spomena (batch svakih 30 min kad je flag ON).
    Odluke kroz src.summons.decide_summon — bez API poziva u ovom skeletu."""
    n = 0
    with conn.cursor() as cur:
        lim = _limits(cur)
        for sid, disc_id, agent_id, user_id in pending_summons(cur):
            cur.execute("""SELECT COALESCE(bool_and(can_summon), true)
                           FROM user_flags WHERE user_id=%s""", (user_id,))
            can = cur.fetchone()[0]
            cur.execute("""SELECT count(*) FROM agent_summons
                           WHERE user_id=%s AND created_at>=date_trunc('day',now())
                             AND status IN ('answered','queued')""", (user_id,))
            u_day = cur.fetchone()[0]
            cur.execute("""SELECT count(*) FROM agent_summons
                           WHERE user_id=%s AND created_at>=now()-interval '7 days'
                             AND status IN ('answered','queued')""", (user_id,))
            u_week = cur.fetchone()[0]
            cur.execute("""SELECT count(*) FROM agent_summons
                           WHERE discussion_id=%s
                             AND created_at>=date_trunc('day',now())""", (disc_id,))
            t_day = cur.fetchone()[0]
            cur.execute("""SELECT count(*) FROM agent_summons
                           WHERE created_at>=date_trunc('day',now())
                             AND status='answered'""")
            g_day = cur.fetchone()[0]
            ctx = SummonContext(
                can_summon=bool(can), user_summons_today=u_day - 1,
                user_summons_week=u_week - 1, thread_summons_today=t_day - 1,
                global_summons_today=g_day,
                global_cost_today_usd=cost_today_usd(cur), limits=lim)
            decision, reason = decide_summon(ctx)
            if decision == "queued":
                # TODO (flag ON): Sonnet 5 poziv — role_prompt + summary runde
                # + zadnjih 10 postova + pitanje; max 400 output tokena;
                # forbidden_hit() na output -> regeneriraj 1x pa rejected_filter
                print(f"[summons] {sid}: spreman za odgovor ({agent_id}) — "
                      "API poziv preskočen (skelet)")
            else:
                cur.execute("""UPDATE agent_summons SET status=%s,
                               processed_at=now() WHERE id=%s""", (decision, sid))
                print(f"[summons] {sid}: {decision} ({reason})")
                n += 1
        conn.commit()
    return n


def main() -> int:
    if not FLAG:
        print("[rasprave] DISCUSSIONS_ENABLED=false — ništa se ne pokreće")
        return 0
    if not API_KEY:
        print("[rasprave] ANTHROPIC_API_KEY_BURZOVNILIST nije postavljen — stop")
        return 1
    with get_conn() as conn, conn.cursor() as cur:
        if not cap_ok(cur):
            print("[rasprave] global_cost_cap_usd_day PROBIJEN — stop + alarm")
            return 0
        # TODO (flag ON): odabir dionica za novu rundu (tjedni raspored +
        # eventi iz pipelinea), Batch API poziv po protokolu iz naloga,
        # upis kroz discussion-publish Edge Function.
        print("[rasprave] skelet: nema implementiranih automatskih rundi "
              "(faza 1 = ručne runde)")
        process_summons(conn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
