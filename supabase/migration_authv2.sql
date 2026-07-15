-- Auth v2 (M26): profiles + portfolios/portfolio_positions + RLS + migracija M9
-- Pokreće se JEDNOM u Supabase SQL editoru. Idempotentno (if not exists /
-- drop-if-exists na policyjima i triggerima). NADOGRAĐUJE M9 shemu:
-- postojeće public.positions se migrira u default portfelj po korisniku.
-- Auto-expose je isključen -> grantovi eksplicitno, SAMO authenticated.

-- ============ 1) PROFILES ============
create table if not exists public.profiles (
  id                 uuid primary key references auth.users (id) on delete cascade,
  display_name       text,
  terms_accepted_at  timestamptz,
  terms_version      text,
  created_at         timestamptz not null default now()
);

comment on table public.profiles is
  'Profil korisnika (M26). terms_accepted_at = zapis prihvata Uvjeta + Politike '
  '(GDPR click-wrap); za OAuth korisnike puni se kroz "Dovrši registraciju" ekran.';

-- trigger: svaki novi auth korisnik dobiva profil; display_name i terms iz
-- user_metadata (email+password signup šalje terms_* kroz options.data)
create or replace function public.handle_new_user()
returns trigger
language plpgsql security definer set search_path = public
as $$
begin
  insert into public.profiles (id, display_name, terms_accepted_at, terms_version)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'full_name',
             new.raw_user_meta_data->>'name',
             split_part(new.email, '@', 1)),
    nullif(new.raw_user_meta_data->>'terms_accepted_at', '')::timestamptz,
    nullif(new.raw_user_meta_data->>'terms_version', '')
  )
  on conflict (id) do nothing;
  return new;
end $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- backfill za POSTOJEĆE M9 korisnike (rade dalje bez ikakve migracije lozinki)
insert into public.profiles (id, display_name, terms_accepted_at, terms_version)
select u.id,
       coalesce(u.raw_user_meta_data->>'full_name', u.raw_user_meta_data->>'name',
                split_part(u.email, '@', 1)),
       nullif(u.raw_user_meta_data->>'terms_accepted_at', '')::timestamptz,
       nullif(u.raw_user_meta_data->>'terms_version', '')
from auth.users u
on conflict (id) do nothing;

-- ENABLE (ne FORCE): jedini insert radi handle_new_user (security definer,
-- vlasnik tablice) — FORCE bi blokirao i njega; authenticated/anon su u
-- svakom slučaju pod policyjima
alter table public.profiles enable row level security;

drop policy if exists profiles_select on public.profiles;
create policy profiles_select on public.profiles
  for select using (auth.uid() = id);

drop policy if exists profiles_update on public.profiles;
create policy profiles_update on public.profiles
  for update using (auth.uid() = id) with check (auth.uid() = id);

-- NEMA insert/delete policyja: insert radi trigger (security definer),
-- brisanje ide isključivo kroz delete-account Edge Function (service role)
revoke all on public.profiles from anon;
revoke all on public.profiles from authenticated;
grant select, update (display_name, terms_accepted_at, terms_version)
  on public.profiles to authenticated;

-- ============ 2) PORTFOLIOS ============
create table if not exists public.portfolios (
  id          bigint generated always as identity primary key,
  user_id     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  name        text not null default 'Moj portfelj'
              check (char_length(name) between 1 and 80),
  created_at  timestamptz not null default now()
);

create index if not exists portfolios_user_idx on public.portfolios (user_id);

create table if not exists public.portfolio_positions (
  id            bigint generated always as identity primary key,
  portfolio_id  bigint not null references public.portfolios (id) on delete cascade,
  ticker        text not null
                check (ticker ~ '^[A-Z0-9]{2,12}$'), -- format praćenih tickera;
                -- referentna tablica dionica ne postoji u Supabaseu (podaci su
                -- statički exporti) -> klijent dodatno validira protiv popisa
  quantity      numeric not null check (quantity > 0),
  avg_price     numeric not null check (avg_price >= 0),
  note          text check (note is null or char_length(note) <= 500),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index if not exists portfolio_positions_pf_idx
  on public.portfolio_positions (portfolio_id);

create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end $$;

drop trigger if exists portfolio_positions_touch on public.portfolio_positions;
create trigger portfolio_positions_touch
  before update on public.portfolio_positions
  for each row execute function public.touch_updated_at();

-- ============ 3) RLS: vlasnik i NITKO drugi ============
alter table public.portfolios enable row level security;
alter table public.portfolios force row level security;
alter table public.portfolio_positions enable row level security;
alter table public.portfolio_positions force row level security;

drop policy if exists portfolios_all on public.portfolios;
create policy portfolios_all on public.portfolios
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists portfolio_positions_all on public.portfolio_positions;
create policy portfolio_positions_all on public.portfolio_positions
  for all
  using (portfolio_id in (select id from public.portfolios where user_id = auth.uid()))
  with check (portfolio_id in (select id from public.portfolios where user_id = auth.uid()));

revoke all on public.portfolios from anon;
revoke all on public.portfolio_positions from anon;
grant select, insert, update, delete on public.portfolios to authenticated;
grant select, insert, update, delete on public.portfolio_positions to authenticated;

-- ============ 4) MIGRACIJA M9 -> v2 ============
-- svaki korisnik s pozicijama dobiva default portfelj; pozicije se presele
do $$
begin
  if exists (select 1 from information_schema.tables
             where table_schema = 'public' and table_name = 'positions') then
    insert into public.portfolios (user_id, name)
    select distinct p.user_id, 'Moj portfelj'
    from public.positions p
    where not exists (select 1 from public.portfolios pf
                      where pf.user_id = p.user_id);

    insert into public.portfolio_positions
      (portfolio_id, ticker, quantity, avg_price, created_at)
    select pf.id, upper(p.ticker), p.qty, p.avg_cost, p.created_at
    from public.positions p
    join public.portfolios pf on pf.user_id = p.user_id
    where not exists (
      select 1 from public.portfolio_positions x
      where x.portfolio_id = pf.id and x.ticker = upper(p.ticker)
        and x.quantity = p.qty and x.avg_price = p.avg_cost);

    drop table public.positions;
  end if;
end $$;
