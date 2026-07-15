-- Faza 3 (M9): portfelj — Supabase shema + ROW LEVEL SECURITY
-- Pokreće se JEDNOM u Supabase SQL editoru (Dashboard -> SQL Editor -> New query).
-- Lozinke i sessioni su u Supabase Auth (auth.users) — MI ih ne diramo;
-- naša je samo tablica pozicija, vezana na auth.uid().

create table if not exists public.positions (
  id          bigint generated always as identity primary key,
  user_id     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  ticker      text not null check (char_length(ticker) between 1 and 12),
  qty         numeric not null check (qty > 0),
  avg_cost    numeric not null check (avg_cost >= 0),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

comment on table public.positions is
  'Ručno unesene pozicije korisnika (v1). user_id ISKLJUČIVO iz auth.uid() — nikad iz client inputa.';

create index if not exists positions_user_idx on public.positions (user_id);

-- updated_at automatski
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end $$;

drop trigger if exists positions_touch on public.positions;
create trigger positions_touch before update on public.positions
  for each row execute function public.touch_updated_at();

-- ============ ROW LEVEL SECURITY (tvrdo pravilo) ============
alter table public.positions enable row level security;
alter table public.positions force row level security;

-- korisnik vidi/mijenja ISKLJUČIVO svoje retke (auth.uid() iz verificiranog JWT-a)
drop policy if exists positions_select on public.positions;
create policy positions_select on public.positions
  for select using (auth.uid() = user_id);

drop policy if exists positions_insert on public.positions;
create policy positions_insert on public.positions
  for insert with check (auth.uid() = user_id);

drop policy if exists positions_update on public.positions;
create policy positions_update on public.positions
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists positions_delete on public.positions;
create policy positions_delete on public.positions
  for delete using (auth.uid() = user_id);

-- anon/authenticated smiju samo kroz RLS; nikakav javni bypass
revoke all on public.positions from anon;
grant select, insert, update, delete on public.positions to authenticated;
