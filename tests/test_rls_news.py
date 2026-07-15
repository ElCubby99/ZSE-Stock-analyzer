"""M30: RLS test za news_items — draft nevidljiv ne-adminima, pisanje samo
admin, dedup po auto_source_ref. Izvršava STVARNE migracije (authv2 + blog +
news) na lokalnom Postgresu u transakciji s rollbackom."""
import pathlib
import sys

import psycopg2
import pytest

sys.path.insert(0, ".")

from src import config  # noqa: E402

MIG_AUTH = pathlib.Path("supabase/migration_authv2.sql").read_text(encoding="utf-8")
MIG_BLOG = pathlib.Path("supabase/migration_blog.sql").read_text(encoding="utf-8")
MIG_NEWS = pathlib.Path("supabase/migration_news.sql").read_text(encoding="utf-8")
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
        create schema if not exists storage;
        create table if not exists storage.buckets (id text primary key, name text, public boolean);
        create table if not exists storage.objects (
          id uuid default gen_random_uuid() primary key, bucket_id text);
    """)
    c.execute(MIG_AUTH)
    c.execute(MIG_BLOG)
    c.execute(MIG_NEWS)
    c.execute("insert into auth.users values (%s,'admin@t.hr','{}'), (%s,'user@t.hr','{}')",
              (ADMIN, USER))
    c.execute("update public.profiles set is_admin = true where id = %s", (ADMIN,))
    c.execute("""insert into public.news_items
                   (ticker, category, headline, link_path, source_type,
                    auto_source_ref, status, published_at)
                 values
                   ('KOEI', 'novo_izvjesce', 'Objavljena vijest', '/dionica/koei',
                    'auto', 'filing:1', 'published', now()),
                   (null, 'opce', 'Tajni draft', '/dividende',
                    'manual', null, 'draft', null)""")
    yield c
    conn.rollback()
    conn.close()


def as_role(c, role, uid=""):
    c.execute("reset role")
    c.execute("select set_config('request.jwt.claim.sub', %s, false)", (uid,))
    c.execute(f"set role {role}")  # noqa: S608 — fiksne role


def test_anon_vidi_samo_published(cur):
    as_role(cur, "anon")
    cur.execute("select headline from public.news_items")
    assert [r[0] for r in cur.fetchall()] == ["Objavljena vijest"], \
        "anon smije vidjeti SAMO objavljeno — draft nigdje javno"
    cur.execute("savepoint sp")
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("insert into public.news_items (category, headline, link_path) "
                    "values ('opce', 'hack', '/x')")
    cur.execute("rollback to savepoint sp")


def test_ne_admin_ne_pise_i_ne_vidi_draft(cur):
    as_role(cur, "authenticated", USER)
    cur.execute("select headline from public.news_items")
    assert [r[0] for r in cur.fetchall()] == ["Objavljena vijest"]
    cur.execute("update public.news_items set headline='HACK' "
                "where headline='Objavljena vijest'")
    assert cur.rowcount == 0, "ne-admin ne smije mijenjati vijesti"
    cur.execute("update public.news_items set tweeted=true")
    assert cur.rowcount == 0, "tweeted mijenja samo admin/Edge Function"


def test_admin_pun_pristup_i_validacije(cur):
    as_role(cur, "authenticated", ADMIN)
    cur.execute("select headline from public.news_items order by headline")
    assert [r[0] for r in cur.fetchall()] == ["Objavljena vijest", "Tajni draft"], \
        "admin vidi i draftove"
    cur.execute("""insert into public.news_items (category, headline, link_path)
                   values ('dividenda', 'Nova vijest', '/dividende')""")
    assert cur.rowcount == 1
    cur.execute("update public.news_items set status='published', published_at=now() "
                "where headline='Nova vijest'")
    assert cur.rowcount == 1
    # check constrainti su i server-side, ne samo UI
    for bad in [
        # nevaljana kategorija
        "insert into public.news_items (category, headline, link_path) "
        "values ('kriva', 'x', '/x')",
        # headline preko 120
        "insert into public.news_items (category, headline, link_path) "
        f"values ('opce', '{'a' * 121}', '/x')",
        # link_path nije interna ruta
        "insert into public.news_items (category, headline, link_path) "
        "values ('opce', 'x', 'https://vanjski.example')",
        # status izvan enuma
        "insert into public.news_items (category, headline, link_path, status) "
        "values ('opce', 'x', '/x', 'archived')",
    ]:
        cur.execute("savepoint sp")
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(bad)
        cur.execute("rollback to savepoint sp")


def test_dedup_auto_source_ref(cur):
    """Isti auto_source_ref se ne smije duplicirati — brana da ponovni EOD
    run istu stvar ne generira dvaput."""
    as_role(cur, "authenticated", ADMIN)
    cur.execute("savepoint sp")
    with pytest.raises(psycopg2.errors.UniqueViolation):
        cur.execute("""insert into public.news_items
                         (category, headline, link_path, source_type, auto_source_ref)
                       values ('novo_izvjesce', 'Duplikat', '/dionica/koei',
                               'auto', 'filing:1')""")
    cur.execute("rollback to savepoint sp")
    # NULL auto_source_ref (ručne vijesti) se smije ponavljati
    cur.execute("""insert into public.news_items (category, headline, link_path)
                   values ('opce', 'Ručna 1', '/x'), ('opce', 'Ručna 2', '/x')""")
    assert cur.rowcount == 2
