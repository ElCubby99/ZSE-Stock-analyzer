-- M67: newsletter pretplatnici — double opt-in (GDPR čl. 6. st. 1. t. (a)
-- + ZEK čl. 107.: privola PRIJE slanja komercijalnih poruka).
-- Pokreće se JEDNOM u Supabase SQL editoru ili kroz db-sync workflow
-- (input newsletter_sql=true); idempotentno.
--
-- Tok: /newsletter Edge Function (service role) upisuje 'pending' + šalje
-- potvrdni mail s confirm_tokenom; klik na link -> 'confirmed'
-- (confirmed_at = dokaz privole). Odjava: unsubscribe_token u svakom
-- mailu -> 'unsubscribed' (zapis se ČUVA kao dokaz privole/odjave i
-- lista isključenja). Nepotvrđeni 'pending' zapisi se brišu nakon 30 dana
-- (noćna korekcija u db/zse_schema_v3_1.sql — minimizacija podataka).
--
-- Frontend NEMA nikakav pristup tablici (ni čitanje): sve ide kroz Edge
-- Function; adminu popis daje SECURITY DEFINER funkcija koja SAMA
-- provjerava public.is_admin() (kao admin_users_overview, M62).

create table if not exists public.newsletter_subscribers (
  id                   uuid primary key default gen_random_uuid(),
  email                text not null,
  status               text not null default 'pending'
                       check (status in ('pending', 'confirmed', 'unsubscribed')),
  lang                 text not null default 'hr' check (lang in ('hr', 'en')),
  source               text,          -- odakle prijava: 'popup' | 'header' | ...
  confirm_token        uuid not null default gen_random_uuid(),
  unsubscribe_token    uuid not null default gen_random_uuid(),
  created_at           timestamptz not null default now(),  -- trenutak prijave
  confirmed_at         timestamptz,   -- double opt-in potvrda (dokaz privole)
  unsubscribed_at      timestamptz,
  last_confirm_sent_at timestamptz    -- cooldown ponovnog slanja potvrde
);

create unique index if not exists uq_newsletter_email
  on public.newsletter_subscribers (lower(email));
create unique index if not exists uq_newsletter_confirm_token
  on public.newsletter_subscribers (confirm_token);
create unique index if not exists uq_newsletter_unsub_token
  on public.newsletter_subscribers (unsubscribe_token);

-- RLS: nitko osim service role (Edge Function) i admina (kroz funkciju
-- dolje) ne vidi ništa; FORCE da ni vlasnik tablice ne zaobilazi policyje
alter table public.newsletter_subscribers enable row level security;
alter table public.newsletter_subscribers force row level security;
drop policy if exists newsletter_admin_read on public.newsletter_subscribers;
create policy newsletter_admin_read on public.newsletter_subscribers
  for select using (public.is_admin());

create or replace function public.admin_newsletter_overview()
returns table (
  id              uuid,
  email           text,
  status          text,
  lang            text,
  source          text,
  created_at      timestamptz,
  confirmed_at    timestamptz,
  unsubscribed_at timestamptz
)
language sql
security definer
set search_path = public
as $$
  select s.id, s.email, s.status, s.lang, s.source,
         s.created_at, s.confirmed_at, s.unsubscribed_at
  from public.newsletter_subscribers s
  where public.is_admin()
  order by s.created_at desc
$$;

revoke all on function public.admin_newsletter_overview() from public;
revoke all on function public.admin_newsletter_overview() from anon;
grant execute on function public.admin_newsletter_overview() to authenticated;
