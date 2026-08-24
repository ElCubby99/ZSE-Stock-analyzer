"""NALOG M30: testovi rasprava — spomeni (čista logika, bez API poziva),
MAR filter, migracija + RLS u rollback transakciji, loader validacija."""
import json
import pathlib
import sys

import psycopg2
import pytest

sys.path.insert(0, ".")

from src import config  # noqa: E402
from src.summons import (  # noqa: E402
    SummonContext, decide_summon, forbidden_hit, parse_mentions,
)

MIG_AUTH = pathlib.Path("supabase/migration_authv2.sql").read_text(encoding="utf-8")
MIG_BLOG = pathlib.Path("supabase/migration_blog.sql").read_text(encoding="utf-8")
MIG_DISC = pathlib.Path("supabase/migration_discussions.sql").read_text(encoding="utf-8")
ADMIN = "aaaaaaaa-1111-1111-1111-111111111111"
USER = "bbbbbbbb-2222-2222-2222-222222222222"


# ---------- spomeni: parsiranje + redoslijed limita ----------

def test_parse_mentions_samo_ljudski_post():
    body = "@ai_value što kažeš na maržu? @ai_skeptic @ai_value @ai_mod @ai_nepostojeci"
    assert parse_mentions(body, "human") == ["ai_value", "ai_skeptic", "ai_nepostojeci"]
    assert parse_mentions(body, "ai") == [], "spomen iz AI posta se ignorira po konstrukciji"
    assert "ai_mod" not in parse_mentions(body, "human"), "moderator se ne poziva"


def test_decide_summon_redoslijed_prvi_pad():
    lim = {"summons_per_user_day": 1, "summons_per_user_week": 5,
           "summons_per_thread_day": 5, "global_summons_per_day": 50,
           "global_cost_cap_usd_day": 5}
    assert decide_summon(SummonContext(limits=lim)) == ("queued", None)
    assert decide_summon(SummonContext(can_summon=False, limits=lim)) \
        == ("rejected_limit", "can_summon=false")
    assert decide_summon(SummonContext(user_summons_today=1, limits=lim)) \
        == ("deferred", "summons_per_user_day")
    assert decide_summon(SummonContext(user_summons_week=5, limits=lim)) \
        == ("deferred", "summons_per_user_week")
    assert decide_summon(SummonContext(thread_summons_today=5, limits=lim)) \
        == ("deferred", "summons_per_thread_day")
    assert decide_summon(SummonContext(global_summons_today=50, limits=lim)) \
        == ("rejected_limit", "global_summons_per_day")
    assert decide_summon(SummonContext(global_cost_today_usd=5.0, limits=lim)) \
        == ("rejected_limit", "global_cost_cap_usd_day")
    # can_summon=false pobjeđuje SVE ostale (prvi pad odlučuje)
    assert decide_summon(SummonContext(can_summon=False, user_summons_today=9,
                                       limits=lim))[0] == "rejected_limit"


def test_mar_filter():
    assert forbidden_hit("Kupite ovu dionicu odmah") is not None
    assert forbidden_hit("preporučujem prodaju") is not None
    assert forbidden_hit("ciljna cijena je 100 €") is not None
    assert forbidden_hit("target price of 50") is not None
    # legitimni izrazi NE smiju okinuti
    assert forbidden_hit("otkup vlastitih dionica (buyback)") is None
    assert forbidden_hit("prodaja imovine napuhala je dobit") is None
    assert forbidden_hit("cijena je ispod fer-zone") is None


# ---------- migracija + RLS ----------

@pytest.fixture()
def cur():
    conn = psycopg2.connect(config.dsn())
    conn.autocommit = False
    c = conn.cursor()
    c.execute("""
        create schema if not exists auth;
        create table if not exists auth.users (
          id uuid primary key, email text, raw_user_meta_data jsonb default '{}');
        create or replace function auth.uid() returns uuid language sql stable as
          $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
        grant usage on schema public to authenticated, anon;
        create schema if not exists storage;
        create table if not exists storage.buckets (id text primary key, name text, public boolean);
        create table if not exists storage.objects (
          id uuid default gen_random_uuid() primary key, bucket_id text);
    """)
    c.execute(MIG_AUTH)
    c.execute(MIG_BLOG)
    c.execute(MIG_DISC)
    c.execute("""insert into auth.users (id, email) values
                 (%s, 'admin@t.hr'), (%s, 'user@t.hr')""", (ADMIN, USER))
    c.execute("update public.profiles set is_admin = true where id = %s", (ADMIN,))
    # jedna draft i jedna objavljena runda s AI postom
    c.execute("""insert into public.discussions (ticker, round_no, data_snapshot, status)
                 values ('HT', 1, '{}'::jsonb, 'published'),
                        ('KOEI', 1, '{}'::jsonb, 'draft')
                 returning id""")
    ids = [r[0] for r in c.fetchall()]
    c.execute("""insert into public.discussion_posts
                   (discussion_id, author_type, agent_id, volley_no, body_hr, citations)
                 values (%s, 'ai', 'ai_value', 1, 'test teza',
                         '[{"label":"P/E","value":"10"}]'::jsonb)""", (ids[0],))
    yield c
    conn.rollback()
    conn.close()


def as_role(c, role, uid=""):
    c.execute("reset role")
    c.execute("select set_config('request.jwt.claim.sub', %s, false)", (uid,))
    c.execute(f"set role {role}")  # noqa: S608


def test_seed_agenata(cur):
    cur.execute("select id, model from public.ai_agents order by id")
    rows = dict(cur.fetchall())
    assert set(rows) == {"ai_value", "ai_skeptic", "ai_macro", "ai_owner", "ai_mod"}
    assert rows["ai_mod"] == "claude-opus-4-8"
    cur.execute("select count(*) from public.usage_limits")
    assert cur.fetchone()[0] >= 8


def test_anon_vidi_samo_objavljeno(cur):
    as_role(cur, "anon")
    cur.execute("select ticker from public.discussions")
    assert [r[0] for r in cur.fetchall()] == ["HT"], "draft se ne vidi javno"
    cur.execute("select count(*) from public.discussion_posts")
    assert cur.fetchone()[0] == 1
    cur.execute("select count(*) from public.ai_agents")
    assert cur.fetchone()[0] == 5, "profili agenata su javni"


def test_anon_ne_moze_pisati(cur):
    as_role(cur, "anon")
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("""insert into public.discussion_posts
                       (discussion_id, author_type, user_id, body_hr)
                       select id, 'human', %s, 'spam' from public.discussions limit 1""",
                    (USER,))


def test_authenticated_ne_moze_direktno_insertati(cur):
    # komentari idu ISKLJUČIVO kroz Edge Function (service role) — izravni
    # INSERT nema policy pa pada na RLS-u
    as_role(cur, "authenticated", USER)
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("""insert into public.discussion_posts
                       (discussion_id, author_type, user_id, body_hr)
                       select id, 'human', %s, 'komentar' from public.discussions limit 1""",
                    (USER,))


def test_ai_post_bez_citata_pada_na_checku(cur):
    with pytest.raises(psycopg2.errors.CheckViolation):
        cur.execute("""insert into public.discussion_posts
                       (discussion_id, author_type, agent_id, body_hr, citations)
                       select id, 'ai', 'ai_value', 'bez citata', '[]'::jsonb
                       from public.discussions limit 1""")


def test_gdpr_brisanje_anonimizira_post(cur):
    cur.execute("select id from public.discussions where ticker='HT'")
    disc = cur.fetchone()[0]
    cur.execute("""insert into public.discussion_posts
                   (discussion_id, author_type, user_id, body_hr, ip_hash, status)
                   values (%s, 'human', %s, 'moj komentar', 'abc', 'published')
                   returning id""", (disc, USER))
    pid = cur.fetchone()[0]
    cur.execute("delete from auth.users where id=%s", (USER,))
    cur.execute("""select body_hr, user_id, ip_hash from public.discussion_posts
                   where id=%s""", (pid,))
    body, uid, iph = cur.fetchone()
    assert body == "[obrisano]" and uid is None and iph is None, \
        "GDPR: post se anonimizira, nit ostaje"


# ---------- loader: validacija seed datoteka ----------

def test_seed_datoteke_prolaze_validaciju():
    from scripts.load_discussions import _check
    files = sorted(pathlib.Path("data/discussions").glob("*.json"))
    assert len(files) >= 10, "faza 1 traži 10 rundi (CROBEX10)"
    for f in files:
        doc = json.loads(f.read_text(encoding="utf-8"))
        _check(doc, f.name)  # baca AssertionError ako nešto ne valja
        # protokol: mod otvara (volley 0) i postoji zaključak + 3 pitanja
        assert doc["posts"][0]["agent_id"] == "ai_mod"
        assert doc["posts"][0]["volley_no"] == 0
        assert len(doc["discussion"]["questions_for_humans"]) == 3
        assert doc["discussion"]["summary_hr"] and doc["discussion"]["summary_en"]
        assert len(doc.get("calls", [])) == 4, "svaki debater daje agent_call"
        # EN prijevod za svaki AI post
        for p in doc["posts"]:
            assert (p.get("body_en") or "").strip(), f"{f.name}: post bez EN"
