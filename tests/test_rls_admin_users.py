"""M62: RLS test za admin_users_overview() — pregled prijava (portfelj).

Izvršava STVARNE migracije (authv2 + blog + admin_users) na lokalnom
Postgresu u transakciji s rollbackom, simulirajući Supabase okolinu kao
ostali RLS testovi. Dokazuje: ne-admin i anon NE vide ničije emailove
(0 redaka / bez pristupa), admin vidi popis s ispravnim brojevima
portfelja i pozicija.
"""
import pathlib
import sys

import psycopg2
import pytest

sys.path.insert(0, ".")

from src import config  # noqa: E402

MIG_AUTH = pathlib.Path("supabase/migration_authv2.sql").read_text(encoding="utf-8")
MIG_BLOG = pathlib.Path("supabase/migration_blog.sql").read_text(encoding="utf-8")
MIG_USERS = pathlib.Path("supabase/migration_admin_users.sql").read_text(encoding="utf-8")
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
        -- M62: stupci koje prava Supabase auth.users shema ima, a stub ne
        alter table auth.users add column if not exists raw_app_meta_data jsonb default '{}';
        alter table auth.users add column if not exists created_at timestamptz default now();
        alter table auth.users add column if not exists last_sign_in_at timestamptz;
        create or replace function auth.uid() returns uuid language sql stable as
          $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
        grant usage on schema public to authenticated, anon;
        -- storage stub (za migration_blog)
        create schema if not exists storage;
        create table if not exists storage.buckets (id text primary key, name text, public boolean);
        create table if not exists storage.objects (
          id uuid default gen_random_uuid() primary key, bucket_id text);
    """)
    c.execute(MIG_AUTH)
    c.execute(MIG_BLOG)
    c.execute(MIG_USERS)
    c.execute("""insert into auth.users (id, email, raw_user_meta_data, raw_app_meta_data)
                 values (%s, 'admin@t.hr', '{}', '{"provider":"email"}'),
                        (%s, 'user@t.hr', '{"full_name":"Korisnik B"}',
                         '{"provider":"google"}')""", (ADMIN, USER))
    c.execute("update public.profiles set is_admin = true where id = %s", (ADMIN,))
    # korisnik B: 1 portfelj s 2 pozicije — kroz RLS, kao u aplikaciji
    # (portfolios/positions su FORCE RLS pa ni vlasnik tablice ne ubacuje mimo)
    as_role(c, "authenticated", USER)
    c.execute("insert into public.portfolios (name) values ('Test portfelj') returning id")
    pf = c.fetchone()[0]
    c.execute("""insert into public.portfolio_positions
                   (portfolio_id, ticker, quantity, avg_price)
                 values (%s, 'KOEI', 10, 900), (%s, 'HPB', 5, 290)""", (pf, pf))
    c.execute("reset role")
    yield c
    conn.rollback()
    conn.close()


def as_role(c, role, uid=""):
    c.execute("reset role")
    c.execute("select set_config('request.jwt.claim.sub', %s, false)", (uid,))
    c.execute(f"set role {role}")  # noqa: S608 — fiksne role


def test_ne_admin_vidi_nula_redaka(cur):
    as_role(cur, "authenticated", USER)
    cur.execute("select * from public.admin_users_overview()")
    assert cur.fetchall() == [], "ne-admin NE smije vidjeti tuđe emailove"


def test_anon_nema_pristup(cur):
    as_role(cur, "anon")
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("select * from public.admin_users_overview()")


def test_admin_vidi_prijave_s_brojevima(cur):
    as_role(cur, "authenticated", ADMIN)
    cur.execute("""select email, display_name, provider, n_portfolios, n_positions
                   from public.admin_users_overview() order by email""")
    rows = cur.fetchall()
    assert [r[0] for r in rows] == ["admin@t.hr", "user@t.hr"]
    by_email = {r[0]: r for r in rows}
    assert by_email["user@t.hr"][1] == "Korisnik B"
    assert by_email["user@t.hr"][2] == "google"
    assert by_email["user@t.hr"][3] == 1 and by_email["user@t.hr"][4] == 2
    assert by_email["admin@t.hr"][3] == 0 and by_email["admin@t.hr"][4] == 0
