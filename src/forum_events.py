"""M77: AI Forum živi — event-komentari agenata + odgovori na @spomene.

Dva mehanizma nad OBJAVLJENIM nitima (discussions.status='published'):

1. Event-komentari: kad za firmu s objavljenom rundom stigne nova objava
   (novo financijsko izvješće ili dividendni događaj), pripadni agent
   (izvješće -> Vrijednosni, dividenda -> Vlasnički) napiše kratak komentar
   u nit — s citatom EHO izvora. Detekcijski gateovi su ISTI kao u
   scripts/generate_news.py (bez backfill šuma, bez izvedenih zapisa).

2. Odgovori na @spomene: red agent_summons (puni ga Edge Function
   discussion-comment) obrađuje se za komentare koje je admin ODOBRIO
   (status='published') — agent odgovara u niti (reply_to = komentar).
   Limiti kroz src.summons.decide_summon (ugovor iz naloga M30).

Pravila (stroga):
- ISKLJUČIVO ANTHROPIC_API_KEY_BURZOVNILIST (zaseban Console Workspace
  ključ); bez njega je modul NO-OP s razlogom u logu. Glavni
  ANTHROPIC_API_KEY se NIKAD ne koristi za forum.
- prije SVAKOG poziva: global_cost_cap_usd_day (usage_limits) naspram
  današnjeg zbroja discussion_posts.cost_usd; trošak se loguje i u
  api_usage (mjesečni budžet, digest).
- MAR filter (src.summons.forbidden_hit) na SVAKI output: pogodak ->
  JEDNA regeneracija sa strožom uputom, pa odustajanje (ništa se ne
  objavljuje). AI post bez citata se ne objavljuje (DB CHECK je mreža).
- dedupe po izvoru: nit koja već ima AI post s citatom istog source_url
  ne dobiva drugi komentar za isti događaj (idempotentno preko runova).
- event/summons postovi nose volley_no NULL ("živi" postovi izvan
  protokola runde) — loader rundi (scripts/load_discussions.py) ih pri
  reseedu NE briše.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable

from . import api_usage
from .summons import SummonContext, decide_summon, forbidden_hit

Log = Callable[[str], None]

MAX_EVENT_POSTS_PER_RUN = 4     # gornja granica novih event-komentara po runu
MAX_SUMMON_REPLIES_PER_RUN = 6  # gornja granica odgovora na spomene po runu
LOOKBACK_DAYS = 3               # događaji stariji od ovoga su obrađeni ranije

EVENT_AGENT = {"report": "ai_value", "dividend": "ai_owner"}

# JSON shema izlaza — ista za event-komentar i odgovor na spomen
OUT_SCHEMA = {
    "type": "object",
    "properties": {
        "body_hr": {"type": "string"},
        "body_en": {"type": "string"},
        "citations": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "value": {"type": "string"},
                    "source_url": {"type": "string"},
                },
                "required": ["label"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["body_hr", "body_en", "citations"],
    "additionalProperties": False,
}

COMMON_RULES = (
    "\n\nPRAVILA ZA OVAJ KOMENTAR (stroga):\n"
    "- Koristiš ISKLJUČIVO činjenice iz bloka PODACI dolje — nijednu brojku "
    "ne izmišljaš niti donosiš iz vlastitog znanja.\n"
    "- Maks. 120 riječi po jeziku; ton foruma: konkretno, bez fraza.\n"
    "- NIKAD preporuka, rejting ni ciljna cijena; riječi kupi/prodaj/"
    "preporučujem ne postoje. Odnos cijene i fer-zone smiješ komentirati "
    "samo ako je zona navedena u PODACIMA.\n"
    "- Vraćaš JSON: body_hr (hrvatski), body_en (engleski prijevod istog "
    "sadržaja), citations (bar jedan citat s izvorom događaja — source_url "
    "iz PODATAKA).\n"
)

STRICTER_RETRY = (
    "\n\nUPOZORENJE: prethodni pokušaj je pao na MAR filteru (zabranjeni "
    "izraz). Preformuliraj bez ijedne riječi koja implicira preporuku, "
    "kupnju, prodaju ili ciljnu cijenu."
)


def api_key() -> str | None:
    return os.environ.get("ANTHROPIC_API_KEY_BURZOVNILIST") or None


# ---------- limiti / trošak ----------

def _limits(cur) -> dict:
    cur.execute("SELECT key, value_int FROM usage_limits")
    return dict(cur.fetchall())


def cost_today_usd(cur) -> float:
    cur.execute("""SELECT COALESCE(SUM(cost_usd), 0) FROM discussion_posts
                   WHERE created_at >= date_trunc('day', now())""")
    return float(cur.fetchone()[0] or 0)


def cap_ok(cur) -> bool:
    lim = _limits(cur)
    return cost_today_usd(cur) < float(lim.get("global_cost_cap_usd_day", 5))


# ---------- detekcija događaja ----------

def collect_events(cur, lookback_days: int = LOOKBACK_DAYS) -> list[dict]:
    """Događaji za tickere s OBJAVLJENOM rundom (kind='ai_round').
    Gateovi identični scripts/generate_news.py — backfill i izvedeni zapisi
    NISU događaji. Vraća najviše jedan događaj po niti (najnoviji)."""
    events: list[dict] = []
    # novo financijsko izvješće -> Vrijednosni
    cur.execute(
        """SELECT DISTINCT ON (dd.id)
                  dd.id, c.ticker, c.name, f.fiscal_year, f.period_type,
                  f.source_url, f.published_at
           FROM filings f
           JOIN companies c ON c.id = f.company_id
           JOIN discussions dd ON dd.ticker = c.ticker
                AND dd.status = 'published' AND dd.kind = 'ai_round'
           WHERE f.doc_type = 'financial_report'
             AND f.ingested_at >= now() - make_interval(days => %s)
             AND f.fiscal_year >= EXTRACT(YEAR FROM CURRENT_DATE)::int - 1
             -- M66/M78: događaj je NOVA objava na izvoru — backfill/restore
             -- starih izvješća ima svjež ingested_at ali star published_at
             AND f.published_at IS NOT NULL
             AND f.published_at >= CURRENT_DATE - 7
           ORDER BY dd.id, f.ingested_at DESC""", (lookback_days,))
    for disc_id, ticker, name, fy, period, src, pub in cur.fetchall():
        if not src:
            continue  # bez izvora nema citata -> nema komentara
        events.append({
            "kind": "report", "discussion_id": disc_id, "ticker": ticker,
            "agent_id": EVENT_AGENT["report"], "source_url": src,
            "facts": {
                "dogadjaj": "novo financijsko izvješće",
                "firma": f"{name} ({ticker})",
                "fiskalna_godina": fy, "period": period,
                "objavljeno": str(pub) if pub else None,
                "source_url": src,
            },
        })
    # dividendni događaj -> Vlasnički (isti gateovi kao vijesti: M66/M66.1)
    cur.execute(
        """SELECT DISTINCT ON (dd.id)
                  dd.id, c.ticker, c.name, d.amount_eur, d.div_type,
                  d.ex_date, d.payment_date, d.fiscal_year, d.source_url
           FROM dividends d
           JOIN companies c ON c.id = d.company_id
           JOIN discussions dd ON dd.ticker = c.ticker
                AND dd.status = 'published' AND dd.kind = 'ai_round'
           WHERE d.created_at >= now() - make_interval(days => %s)
             AND d.amount_eur IS NOT NULL AND d.source_url IS NOT NULL
             AND (d.div_type IS NULL OR d.div_type NOT ILIKE '%%izvedeno%%')
             AND COALESCE(d.fiscal_year,
                          EXTRACT(YEAR FROM CURRENT_DATE)::int)
                 >= EXTRACT(YEAR FROM CURRENT_DATE)::int - 1
             AND (d.ex_date IS NULL OR d.ex_date >= CURRENT_DATE - 7)
             AND NOT (d.div_type ILIKE '%%rijedlog%%' AND EXISTS (
                   SELECT 1 FROM dividends di
                   WHERE di.company_id = d.company_id
                     AND di.amount_eur = d.amount_eur
                     AND COALESCE(di.fiscal_year, 0) = COALESCE(d.fiscal_year, 0)
                     AND (di.div_type IS NULL
                          OR di.div_type NOT ILIKE '%%rijedlog%%')))
           ORDER BY dd.id, d.created_at DESC""", (lookback_days,))
    for (disc_id, ticker, name, amount, dtyp, ex, pay, fy,
         src) in cur.fetchall():
        is_prop = bool(dtyp and "rijedlog" in dtyp)
        events.append({
            "kind": "dividend", "discussion_id": disc_id, "ticker": ticker,
            "agent_id": EVENT_AGENT["dividend"], "source_url": src,
            "facts": {
                "dogadjaj": ("prijedlog dividende (NIJE izglasana — "
                             "skupština ga može i odbiti)" if is_prop
                             else "objavljen dividendni događaj"),
                "firma": f"{name} ({ticker})",
                "iznos_eur_po_dionici": float(amount),
                "vrsta": dtyp,
                "ex_datum": str(ex) if ex else None,
                "datum_isplate": str(pay) if pay else None,
                "fiskalna_godina": fy,
                "source_url": src,
            },
        })
    return events


def already_commented(cur, discussion_id, source_url: str) -> bool:
    """Idempotentnost preko runova: citat istog izvora u niti = obrađeno."""
    cur.execute(
        """SELECT 1 FROM discussion_posts
           WHERE discussion_id = %s AND author_type = 'ai'
             AND citations @> %s::jsonb LIMIT 1""",
        (discussion_id, json.dumps([{"source_url": source_url}])))
    return cur.fetchone() is not None


# ---------- kontekst niti ----------

def _thread_context(cur, discussion_id, n: int = 6) -> str:
    cur.execute(
        """SELECT COALESCE(a.display_name_hr, p.agent_id, 'Čitatelj'), p.body_hr
           FROM discussion_posts p
           LEFT JOIN ai_agents a ON a.id = p.agent_id
           WHERE p.discussion_id = %s AND p.status = 'published'
           ORDER BY p.created_at DESC LIMIT %s""", (discussion_id, n))
    rows = cur.fetchall()[::-1]
    return "\n".join(f"[{who}] {body[:400]}" for who, body in rows)


def _agent(cur, agent_id: str) -> dict | None:
    cur.execute("""SELECT id, display_name_hr, role_prompt, model
                   FROM ai_agents WHERE id = %s AND is_active""", (agent_id,))
    r = cur.fetchone()
    if not r:
        return None
    return {"id": r[0], "name": r[1], "role_prompt": r[2], "model": r[3]}


# ---------- generacija (Anthropic API) ----------

def _generate(agent: dict, user_prompt: str, *, ticker: str | None,
              conn, operation: str) -> dict | None:
    """Jedan poziv + MAR provjera; pad filtera -> jedan retry sa strožom
    uputom. Vraća {body_hr, body_en, citations, model, usage_cost} ili None."""
    import anthropic  # lazy import da testovi rade bez paketa

    client = anthropic.Anthropic(api_key=api_key())
    model = os.environ.get("FORUM_AI_MODEL") or agent["model"]
    prompt = user_prompt
    for attempt in (1, 2):
        # isti mehanizam kao src/extract.py (stream + json_schema izlaz)
        with client.messages.stream(
            model=model, max_tokens=1500,
            system=agent["role_prompt"] + COMMON_RULES,
            output_config={"format": {"type": "json_schema",
                                      "schema": OUT_SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            resp = stream.get_final_message()
        api_usage.record(operation, resp.model or model, resp.usage,
                         ticker=ticker, conn=conn)
        cost_eur = api_usage.estimate_cost_eur(
            resp.model or model,
            getattr(resp.usage, "input_tokens", 0) or 0,
            getattr(resp.usage, "output_tokens", 0) or 0) or 0.0
        if resp.stop_reason in ("refusal", "max_tokens"):
            return None
        text = next((b.text for b in resp.content
                     if getattr(b, "type", None) == "text"), None)
        if not text:
            return None
        try:
            out = json.loads(text)
        except ValueError:
            return None
        hit = forbidden_hit(out.get("body_hr", "")) or \
            forbidden_hit(out.get("body_en", ""))
        if hit and attempt == 1:
            prompt = user_prompt + STRICTER_RETRY
            continue
        if hit or not out.get("citations"):
            return None  # rejected_filter — ništa se ne objavljuje
        out["model"] = resp.model or model
        out["tokens_in"] = int(getattr(resp.usage, "input_tokens", 0) or 0)
        out["tokens_out"] = int(getattr(resp.usage, "output_tokens", 0) or 0)
        # cost_usd u discussion_posts hrani dnevni cap (USD); EUR procjena
        # iz cjenika je dovoljno blizu — cap je sigurnosna mreža, ne knjigovodstvo
        out["cost_usd"] = round(cost_eur, 6)
        return out
    return None


def _insert_post(cur, discussion_id, agent_id, out: dict,
                 reply_to=None) -> Any:
    cur.execute(
        """INSERT INTO discussion_posts (discussion_id, author_type, agent_id,
             volley_no, reply_to, body_hr, body_en, citations, status,
             model_used, tokens_in, tokens_out, cost_usd)
           VALUES (%s, 'ai', %s, NULL, %s, %s, %s, %s, 'published',
                   %s, %s, %s, %s)
           RETURNING id""",
        (discussion_id, agent_id, reply_to, out["body_hr"], out["body_en"],
         json.dumps(out["citations"], ensure_ascii=False), out["model"],
         out["tokens_in"], out["tokens_out"], out["cost_usd"]))
    return cur.fetchone()[0]


# ---------- 1) event-komentari ----------

def post_event_comments(conn, log: Log = print, *, generate=_generate,
                        lookback_days: int = LOOKBACK_DAYS,
                        max_posts: int = MAX_EVENT_POSTS_PER_RUN) -> int:
    n = 0
    with conn.cursor() as cur:
        for ev in collect_events(cur, lookback_days):
            if n >= max_posts:
                log("[forum] dnevna granica event-komentara dosegnuta")
                break
            if already_commented(cur, ev["discussion_id"], ev["source_url"]):
                continue
            if not cap_ok(cur):
                log("[forum] global_cost_cap_usd_day dosegnut — stop")
                break
            agent = _agent(cur, ev["agent_id"])
            if not agent:
                continue
            ctx = _thread_context(cur, ev["discussion_id"])
            prompt = (
                "U niti AI Foruma o ovoj dionici stigla je NOVA objava. "
                "Napiši kratak komentar u nit: što objava sadrži i na što se "
                "u dosadašnjoj raspravi nadovezuje. Ako je prijedlog, jasno "
                "naglasi da NIJE izglasan.\n\n"
                f"PODACI (jedini dopušteni izvor brojki):\n"
                f"{json.dumps(ev['facts'], ensure_ascii=False, indent=1)}\n\n"
                f"DOSADAŠNJA RASPRAVA (zadnji postovi, samo kontekst):\n{ctx}")
            out = generate(agent, prompt, ticker=ev["ticker"], conn=conn,
                           operation="forum_event")
            if not out:
                log(f"[forum] {ev['ticker']}: {ev['kind']} — odbijeno "
                    "(filter/format), ništa nije objavljeno")
                continue
            pid = _insert_post(cur, ev["discussion_id"], ev["agent_id"], out)
            conn.commit()
            n += 1
            log(f"[forum] {ev['ticker']}: {agent['name']} komentirao "
                f"({ev['kind']}, post {pid})")
    return n


# ---------- 2) odgovori na @spomene ----------

def answer_summons(conn, log: Log = print, *, generate=_generate,
                   max_replies: int = MAX_SUMMON_REPLIES_PER_RUN) -> int:
    n = 0
    with conn.cursor() as cur:
        lim = _limits(cur)
        cur.execute(
            """SELECT s.id, s.discussion_id, s.agent_id, s.user_id,
                      p.id, p.status, p.body_hr, d.ticker
               FROM agent_summons s
               JOIN discussion_posts p ON p.id = s.post_id
               JOIN discussions d ON d.id = s.discussion_id
               WHERE s.status = 'queued'
               ORDER BY s.created_at LIMIT 50""")
        for (sid, disc_id, agent_id, user_id, post_id, p_status, body,
             ticker) in cur.fetchall():
            if p_status in ("hidden", "flagged"):
                cur.execute("""UPDATE agent_summons SET status='rejected_filter',
                               processed_at=now() WHERE id=%s""", (sid,))
                conn.commit()
                continue
            if p_status != "published":
                continue  # čeka odobrenje moderatora — ostaje queued
            if n >= max_replies:
                break
            # brojila za decide_summon (ugovor M30: prvi pad odlučuje)
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
            ctx_obj = SummonContext(
                can_summon=bool(can), user_summons_today=u_day - 1,
                user_summons_week=u_week - 1, thread_summons_today=t_day - 1,
                global_summons_today=g_day,
                global_cost_today_usd=cost_today_usd(cur), limits=lim)
            decision, reason = decide_summon(ctx_obj)
            if decision != "queued":
                cur.execute("""UPDATE agent_summons SET status=%s,
                               processed_at=now() WHERE id=%s""",
                            (decision, sid))
                conn.commit()
                log(f"[summons] {sid}: {decision} ({reason})")
                continue
            agent = _agent(cur, agent_id)
            if not agent:
                cur.execute("""UPDATE agent_summons SET status='rejected_filter',
                               processed_at=now() WHERE id=%s""", (sid,))
                conn.commit()
                continue
            ctx = _thread_context(cur, disc_id, n=8)
            prompt = (
                "Čitatelj te spomenuo u niti AI Foruma i postavlja pitanje. "
                "Odgovori u niti: prvo jednom rečenicom parafraziraj pitanje "
                "(čitatelji odgovor vide i bez komentara), zatim odgovori — "
                "isključivo na temelju dosadašnje rasprave i njenih citata. "
                "Ako odgovor traži podatak koji u raspravi ne postoji, reci "
                "to otvoreno (n/p nije 0 — prazno s razlogom je bolje od "
                "krive brojke).\n\n"
                f"PITANJE ČITATELJA:\n{body[:1500]}\n\n"
                f"DOSADAŠNJA RASPRAVA (zadnji postovi):\n{ctx}")
            out = generate(agent, prompt, ticker=ticker, conn=conn,
                           operation="forum_summon")
            if not out:
                cur.execute("""UPDATE agent_summons SET status='rejected_filter',
                               processed_at=now() WHERE id=%s""", (sid,))
                conn.commit()
                log(f"[summons] {sid}: odbijeno (filter/format)")
                continue
            pid = _insert_post(cur, disc_id, agent_id, out, reply_to=post_id)
            cur.execute("""UPDATE agent_summons SET status='answered',
                           reply_post_id=%s, processed_at=now()
                           WHERE id=%s""", (pid, sid))
            conn.commit()
            n += 1
            log(f"[summons] {sid}: {agent['name']} odgovorio (post {pid})")
    return n


# ---------- ulaz iz pipelinea ----------

def run(conn, log: Log = print) -> dict:
    """Poziva daily pipeline. Bez ključa: no-op s razlogom (cijene/exporti
    ne smiju ovisiti o forumu)."""
    if not api_key():
        log("[forum] ANTHROPIC_API_KEY_BURZOVNILIST nije postavljen — "
            "event-komentari i spomeni se preskaču")
        return {"events": 0, "summons": 0}
    with conn.cursor() as cur:
        if not cap_ok(cur):
            log("[forum] global_cost_cap_usd_day već dosegnut — preskačem")
            return {"events": 0, "summons": 0}
    ne = post_event_comments(conn, log)
    ns = answer_summons(conn, log)
    return {"events": ne, "summons": ns}


def main() -> int:
    """CLI za discussions workflow (dnevni termin + vikendi — daily-eod
    vikendom ne dolazi do forum koraka). Ispisuje FORUM_POSTS=<n> da korak
    iza može okinuti Vercel deploy samo kad ima novih postova."""
    from .db import get_conn
    with get_conn() as conn:
        stats = run(conn)
    total = stats["events"] + stats["summons"]
    print(f"[forum] event-komentari: {stats['events']}, "
          f"odgovori na spomene: {stats['summons']}")
    print(f"FORUM_POSTS={total}")
    return 0


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
