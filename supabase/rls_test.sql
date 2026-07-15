-- RLS DOKAZ (lokalna simulacija Supabase okruženja) — isti SQL kao schema.sql.
-- Supabase izvodi auth.uid() iz verificiranog JWT-a; ovdje ga simuliramo
-- GUC-om request.jwt.claim.sub (isto što radi PostgREST/Supabase interno).
-- Test: korisnik A NE SMIJE vidjeti ni dirati retke korisnika B.

begin;

create schema if not exists auth;
create table if not exists auth.users (id uuid primary key);
create or replace function auth.uid() returns uuid language sql stable as
  $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;

-- === identično schema.sql (bez referenci koje lokalno ne postoje) ===
create table public.positions (
  id          bigint generated always as identity primary key,
  user_id     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  ticker      text not null check (char_length(ticker) between 1 and 12),
  qty         numeric not null check (qty > 0),
  avg_cost    numeric not null check (avg_cost >= 0),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
alter table public.positions enable row level security;
alter table public.positions force row level security;
create policy positions_select on public.positions for select using (auth.uid() = user_id);
create policy positions_insert on public.positions for insert with check (auth.uid() = user_id);
create policy positions_update on public.positions for update
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy positions_delete on public.positions for delete using (auth.uid() = user_id);

-- NAPOMENA (lokalni test): FORCE ROW LEVEL SECURITY primjenjuje police i na
-- vlasnika tablice (a test korisnik NIJE superuser), pa posebna rola nije
-- potrebna — RLS je aktivan za sve upite ispod.

-- dva korisnika
insert into auth.users values ('11111111-1111-1111-1111-111111111111'),
                              ('22222222-2222-2222-2222-222222222222');

-- ===== korisnik A upisuje 2 pozicije =====
set request.jwt.claim.sub = '11111111-1111-1111-1111-111111111111';
insert into public.positions (ticker, qty, avg_cost) values ('KODT', 3, 3100), ('ZABA', 200, 19.5);

-- ===== korisnik B upisuje 1 poziciju =====
set request.jwt.claim.sub = '22222222-2222-2222-2222-222222222222';
insert into public.positions (ticker, qty, avg_cost) values ('INA', 10, 610);

-- TEST 1: B vidi SAMO svoj redak
select 'TEST1 B vidi' as test, count(*) as n,
       count(*) filter (where ticker <> 'INA') as tudjih
from public.positions;

-- TEST 2: B pokušava UPDATE tuđe pozicije -> 0 redaka
update public.positions set qty = 999999 where ticker = 'KODT';
select 'TEST2 B update tudjeg' as test,
       count(*) filter (where ticker = 'KODT' and qty = 999999) as promijenjeno
from public.positions;

-- TEST 3: B pokušava DELETE tuđeg -> 0 redaka
delete from public.positions where ticker = 'ZABA';

-- TEST 4: B pokušava INSERT s TUĐIM user_id (spoofing) -> mora pasti na RLS
do $$ begin
  begin
    insert into public.positions (user_id, ticker, qty, avg_cost)
    values ('11111111-1111-1111-1111-111111111111', 'HACK', 1, 1);
    raise exception 'TEST4 FAIL: spoofani insert prošao!';
  exception when insufficient_privilege or check_violation then
    raise notice 'TEST4 OK: spoofani insert odbijen (RLS with check)';
  end;
end $$;

-- TEST 5: A i dalje vidi svoje 2 netaknute pozicije
set request.jwt.claim.sub = '11111111-1111-1111-1111-111111111111';
select 'TEST5 A vidi' as test, count(*) as n,
       bool_and(qty in (3, 200)) as netaknuto
from public.positions;

rollback;  -- test ne ostavlja tragove
