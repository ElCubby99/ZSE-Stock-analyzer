"""M26: RLS integracijski test za portfelj v2 (profiles/portfolios/positions).

Izvršava STVARNU supabase/migration_authv2.sql na lokalnom Postgresu unutar
transakcije (rollback na kraju — bez tragova), simulirajući Supabase okolinu
kako to radi i M9 rls_test.sql:
  - auth.users + auth.uid() iz GUC-a request.jwt.claim.sub (isto kao PostgREST)
  - role anon/authenticated; upiti korisnika idu pod SET ROLE authenticated
Dokazuje: A ne vidi/ne mijenja B; spoof insert pada; anon nema pristup ničemu.
"""
import pathlib
import sys

import psycopg2
import pytest

sys.path.insert(0, ".")

from src import config  # noqa: E402

MIG = pathlib.Path("supabase/migration_authv2.sql").read_text(encoding="utf-8")
A = "11111111-1111-1111-1111-111111111111"
B = "22222222-2222-2222-2222-222222222222"


@pytest.fixture()
def cur():
    conn = psycopg2.connect(config.dsn())
    conn.autocommit = False
    c = conn.cursor()
    # Supabase okruženje: auth shema + uid() + role (sve u transakciji)
    c.execute("""
        create schema if not exists auth;
        create table if not exists auth.users (
          id uuid primary key, email text, raw_user_meta_data jsonb default '{}');
        create or replace function auth.uid() returns uuid language sql stable as
          $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
        do $$ begin
          if not exists (select 1 from pg_roles where rolname='authenticated') then
            create role authenticated nologin; end if;
          if not exists (select 1 from pg_roles where rolname='anon') then
            create role anon nologin; end if;
        end $$;
        grant usage on schema public to authenticated, anon;
    """)
    c.execute(MIG)  # stvarna migracija — ono što ide u Supabase SQL editor
    # dva korisnika: A preko emaila (terms u metadata), B kao OAuth (bez terms)
    c.execute("""insert into auth.users values
        (%s, 'a@test.hr',
         '{"terms_accepted_at":"2026-07-15T10:00:00Z","terms_version":"15.07.2026."}'),
        (%s, 'b@test.hr', '{"full_name":"Korisnik B"}')""", (A, B))
    yield c
    conn.rollback()
    conn.close()


def as_user(c, uid):
    c.execute("reset role")
    c.execute("select set_config('request.jwt.claim.sub', %s, false)", (uid,))
    c.execute("set role authenticated")


def as_anon(c):
    c.execute("reset role")
    c.execute("select set_config('request.jwt.claim.sub', '', false)")
    c.execute("set role anon")


def test_profiles_trigger_and_isolation(cur):
    cur.execute("reset role")
    cur.execute("select count(*) from public.profiles")
    assert cur.fetchone()[0] == 2, "trigger mora kreirati profil za svakog auth usera"
    cur.execute("select terms_accepted_at from public.profiles where id=%s", (A,))
    assert cur.fetchone()[0] is not None, "email signup: terms iz user_metadata"
    cur.execute("select terms_accepted_at, display_name from public.profiles where id=%s", (B,))
    terms_b, name_b = cur.fetchone()
    assert terms_b is None and name_b == "Korisnik B", "OAuth: bez terms, ime iz metadata"

    as_user(cur, A)
    cur.execute("select count(*) from public.profiles")
    assert cur.fetchone()[0] == 1, "korisnik vidi SAMO svoj profil"
    cur.execute("update public.profiles set display_name='Ana' where id=%s", (A,))
    assert cur.rowcount == 1
    cur.execute("update public.profiles set display_name='HACK' where id=%s", (B,))
    assert cur.rowcount == 0, "tuđi profil se ne može mijenjati"
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("delete from public.profiles where id=%s", (A,))


def test_portfolio_owner_isolation(cur):
    as_user(cur, A)
    cur.execute("insert into public.portfolios (name) values ('A portfelj') returning id")
    pf_a = cur.fetchone()[0]
    cur.execute("""insert into public.portfolio_positions
        (portfolio_id, ticker, quantity, avg_price) values (%s,'KOEI',3,900)""", (pf_a,))

    as_user(cur, B)
    cur.execute("insert into public.portfolios (name) values ('B portfelj') returning id")
    pf_b = cur.fetchone()[0]
    cur.execute("""insert into public.portfolio_positions
        (portfolio_id, ticker, quantity, avg_price) values (%s,'INA',10,610)""", (pf_b,))

    # B vidi samo svoje
    cur.execute("select count(*) from public.portfolios")
    assert cur.fetchone()[0] == 1
    cur.execute("select count(*) from public.portfolio_positions")
    assert cur.fetchone()[0] == 1
    # B ne može mijenjati/brisati A-ove retke (0 redaka, ne greška)
    cur.execute("update public.portfolio_positions set quantity=999 where portfolio_id=%s", (pf_a,))
    assert cur.rowcount == 0
    cur.execute("delete from public.portfolio_positions where portfolio_id=%s", (pf_a,))
    assert cur.rowcount == 0
    # B ne može ubaciti poziciju u A-ov portfelj (spoof) -> RLS with check
    cur.execute("savepoint spoof")
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("""insert into public.portfolio_positions
            (portfolio_id, ticker, quantity, avg_price) values (%s,'HACK',1,1)""", (pf_a,))
    cur.execute("rollback to savepoint spoof")
    # A i dalje vidi svoju netaknutu poziciju
    as_user(cur, A)
    cur.execute("select ticker, quantity from public.portfolio_positions")
    assert cur.fetchall() == [("KOEI", 3)]


def test_portfolio_validations_and_anon(cur):
    as_user(cur, A)
    cur.execute("insert into public.portfolios (name) values ('V') returning id")
    pf = cur.fetchone()[0]
    for bad in [
        f"insert into public.portfolio_positions (portfolio_id, ticker, quantity, avg_price) values ({pf},'KOEI',0,1)",       # qty > 0
        f"insert into public.portfolio_positions (portfolio_id, ticker, quantity, avg_price) values ({pf},'koei!',1,1)",      # format tickera
        f"insert into public.portfolio_positions (portfolio_id, ticker, quantity, avg_price) values ({pf},'KOEI',1,-5)",      # cijena >= 0
    ]:
        cur.execute("savepoint sp")
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(bad)
        cur.execute("rollback to savepoint sp")

    # anon: NIŠTA (nema grantova, ne samo prazan rezultat)
    as_anon(cur)
    for tbl in ("profiles", "portfolios", "portfolio_positions"):
        cur.execute("savepoint sp2")
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute(f"select * from public.{tbl}")  # noqa: S608
        cur.execute("rollback to savepoint sp2")
