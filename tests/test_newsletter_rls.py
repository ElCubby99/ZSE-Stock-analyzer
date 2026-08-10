"""M67: RLS test za newsletter_subscribers + admin_newsletter_overview().

Izvršava STVARNE migracije (authv2 + newsletter) na lokalnom Postgresu u
transakciji s rollbackom, kao ostali RLS testovi. Dokazuje:
- ne-admin i anon NE vide nijedan email (RLS + gate u funkciji)
- admin kroz funkciju vidi popis sa statusima
- dupla prijava istog emaila (case-insensitive) je nemoguća (unique)
- noćni purge (db/zse_schema_v3_1.sql) briše SAMO stare pending zapise
"""
import pathlib
import sys

import psycopg2
import pytest

sys.path.insert(0, ".")

from src import config  # noqa: E402

MIG_AUTH = pathlib.Path("supabase/migration_authv2.sql").read_text(encoding="utf-8")
MIG_BLOG = pathlib.Path("supabase/migration_blog.sql").read_text(encoding="utf-8")
MIG_NL = pathlib.Path("supabase/migration_newsletter.sql").read_text(encoding="utf-8")
ADMIN = "aaaaaaaa-1111-1111-1111-111111111111"
USER = "bbbbbbbb-2222-2222-2222-222222222222"


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
        -- storage stub (za migration_blog — ona definira public.is_admin())
        create schema if not exists storage;
        create table if not exists storage.buckets (id text primary key, name text, public boolean);
        create table if not exists storage.objects (
          id uuid default gen_random_uuid() primary key, bucket_id text);
    """)
    c.execute(MIG_AUTH)
    c.execute(MIG_BLOG)
    c.execute(MIG_NL)
    c.execute("""insert into auth.users (id, email) values
                 (%s, 'admin@t.hr'), (%s, 'user@t.hr')""", (ADMIN, USER))
    c.execute("update public.profiles set is_admin = true where id = %s", (ADMIN,))
    # zapisi kao da ih je upisala Edge Function — Supabase service_role ima
    # BYPASSRLS; lokalno to emuliramo privremenim skidanjem FORCE (vlasnik
    # tada zaobilazi RLS), pa FORCE vraćamo prije samih testova
    c.execute("alter table public.newsletter_subscribers no force row level security")
    c.execute("""insert into public.newsletter_subscribers
                   (email, status, lang, source, confirmed_at)
                 values ('ana@primjer.hr', 'confirmed', 'hr', 'popup', now()),
                        ('bob@example.com', 'pending', 'en', 'header', null)""")
    c.execute("alter table public.newsletter_subscribers force row level security")
    yield c
    conn.rollback()
    conn.close()


def as_role(c, role, uid=""):
    c.execute("reset role")
    c.execute("select set_config('request.jwt.claim.sub', %s, false)", (uid,))
    c.execute(f"set role {role}")  # noqa: S608 — fiksne role


def test_ne_admin_ne_vidi_nista(cur):
    as_role(cur, "authenticated", USER)
    cur.execute("select * from public.admin_newsletter_overview()")
    assert cur.fetchall() == [], "ne-admin NE smije vidjeti emailove pretplatnika"
    # izravan SELECT ne prolazi ni na razini GRANT-a (tablica nema grant
    # na authenticated — pristup isključivo kroz SECURITY DEFINER funkciju)
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("select count(*) from public.newsletter_subscribers")


def test_anon_nema_pristup_funkciji(cur):
    as_role(cur, "anon")
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("select * from public.admin_newsletter_overview()")


def test_admin_vidi_pretplatnike(cur):
    as_role(cur, "authenticated", ADMIN)
    cur.execute("""select email, status, lang, source
                   from public.admin_newsletter_overview() order by email""")
    rows = cur.fetchall()
    assert rows == [("ana@primjer.hr", "confirmed", "hr", "popup"),
                    ("bob@example.com", "pending", "en", "header")]


def test_dupla_prijava_nemoguca(cur):
    # upis kao Edge Function (BYPASSRLS emulacija, kao u fixtureu)
    cur.execute("alter table public.newsletter_subscribers no force row level security")
    with pytest.raises(psycopg2.errors.UniqueViolation):
        cur.execute("""insert into public.newsletter_subscribers (email)
                       values ('ANA@primjer.hr')""")  # case-insensitive unique


def test_purge_brise_samo_stare_pending(cur):
    cur.execute("alter table public.newsletter_subscribers no force row level security")
    cur.execute("""insert into public.newsletter_subscribers (email, status, created_at)
                   values ('star-pending@t.hr', 'pending', now() - interval '31 days'),
                          ('star-potvrdjen@t.hr', 'confirmed', now() - interval '400 days')""")
    # isti izraz kao noćna korekcija u db/zse_schema_v3_1.sql
    cur.execute("""DELETE FROM newsletter_subscribers
                   WHERE status = 'pending' AND created_at < now() - interval '30 days'""")
    cur.execute("select email from public.newsletter_subscribers order by email")
    emails = [r[0] for r in cur.fetchall()]
    assert "star-pending@t.hr" not in emails, "stari pending se briše (minimizacija)"
    assert "star-potvrdjen@t.hr" in emails, "potvrđeni se NIKAD ne briše purgeom"
    assert "bob@example.com" in emails, "svježi pending ostaje"
