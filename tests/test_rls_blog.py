"""M27: RLS test za blog_posts — draftovi nevidljivi ne-adminima, pisanje
samo admin. Izvršava STVARNE migracije (authv2 + blog) na lokalnom Postgresu
u transakciji s rollbackom; storage shema se stubbа (lokalno ne postoji)."""
import pathlib
import sys

import psycopg2
import pytest

sys.path.insert(0, ".")

from src import config  # noqa: E402

MIG_AUTH = pathlib.Path("supabase/migration_authv2.sql").read_text(encoding="utf-8")
MIG_BLOG = pathlib.Path("supabase/migration_blog.sql").read_text(encoding="utf-8")
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
        -- storage stub (lokalno nema Supabase storage sheme)
        create schema if not exists storage;
        create table if not exists storage.buckets (id text primary key, name text, public boolean);
        create table if not exists storage.objects (
          id uuid default gen_random_uuid() primary key, bucket_id text);
    """)
    c.execute(MIG_AUTH)
    c.execute(MIG_BLOG)
    c.execute("insert into auth.users values (%s,'admin@t.hr','{}'), (%s,'user@t.hr','{}')",
              (ADMIN, USER))
    c.execute("update public.profiles set is_admin = true where id = %s", (ADMIN,))
    # objavljen + draft post (kao vlasnik tablice)
    c.execute("""insert into public.blog_posts (slug, title, content_md, status, published_at)
                 values ('javni-post', 'Javni', 'tekst', 'published', now()),
                        ('tajni-draft', 'Draft', 'tekst', 'draft', null)""")
    yield c
    conn.rollback()
    conn.close()


def as_role(c, role, uid=""):
    c.execute("reset role")
    c.execute("select set_config('request.jwt.claim.sub', %s, false)", (uid,))
    c.execute(f"set role {role}")  # noqa: S608 — fiksne role


def test_anon_sees_only_published(cur):
    as_role(cur, "anon")
    cur.execute("select slug from public.blog_posts")
    assert [r[0] for r in cur.fetchall()] == ["javni-post"], \
        "anon smije vidjeti SAMO objavljeno — draft nigdje javno"
    cur.execute("savepoint sp")
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("insert into public.blog_posts (slug, title, content_md) "
                    "values ('hack', 'x', 'y')")
    cur.execute("rollback to savepoint sp")


def test_non_admin_user_cannot_write_or_see_drafts(cur):
    as_role(cur, "authenticated", USER)
    cur.execute("select slug from public.blog_posts")
    assert [r[0] for r in cur.fetchall()] == ["javni-post"]
    cur.execute("update public.blog_posts set title='HACK' where slug='javni-post'")
    assert cur.rowcount == 0, "ne-admin ne smije mijenjati postove"
    cur.execute("savepoint sp")
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("insert into public.blog_posts (slug, title, content_md) "
                    "values ('hack2', 'x', 'y')")
    cur.execute("rollback to savepoint sp")
    # publish log: ne-admin ne vidi ništa
    cur.execute("select count(*) from public.blog_publish_log")
    assert cur.fetchone()[0] == 0


def test_admin_full_access_and_validations(cur):
    as_role(cur, "authenticated", ADMIN)
    cur.execute("select slug from public.blog_posts order by slug")
    assert [r[0] for r in cur.fetchall()] == ["javni-post", "tajni-draft"], \
        "admin vidi i draftove"
    cur.execute("""insert into public.blog_posts (slug, title, content_md, status)
                   values ('novi-post', 'Novi', 'md', 'draft')""")
    assert cur.rowcount == 1
    cur.execute("update public.blog_posts set status='published', published_at=now() "
                "where slug='novi-post'")
    assert cur.rowcount == 1
    # validacije: slug format i meta cap su i server-side (check constrainti)
    for bad in [
        "insert into public.blog_posts (slug, title, content_md) values ('Nije-Kebab', 'x', 'y')",
        "insert into public.blog_posts (slug, title, content_md, meta_description) "
        "values ('predugi-meta', 'x', 'y', repeat('a', 161))",
        "insert into public.blog_posts (slug, title, content_md, cover_image_url) "
        "values ('http-slika', 'x', 'y', 'http://nesigurno.com/a.png')",
    ]:
        cur.execute("savepoint sp")
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(bad)
        cur.execute("rollback to savepoint sp")
