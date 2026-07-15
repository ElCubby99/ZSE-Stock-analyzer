-- M30: Vijesti — news_items (javna stranica /vijesti + izvor za X objave).
-- Pokreće se JEDNOM u Supabase SQL editoru. Idempotentno.
-- Auto-expose je isključen -> grantovi eksplicitno. Ovisi o migration_blog.sql
-- (public.is_admin()).

create table if not exists public.news_items (
  id               uuid primary key default gen_random_uuid(),
  ticker           text,             -- nullable: vijest može biti opća
  category         text not null
                   check (category in
                          ('novo_izvjesce', 'dividenda', 'promjena_cijene', 'opce')),
  headline         text not null check (char_length(headline) between 1 and 120),
  body             text,             -- prazno = vijest je samo pokazivač na link_path
  link_path        text not null check (link_path ~ '^/'),  -- interna ruta
  source_type      text not null default 'manual'
                   check (source_type in ('manual', 'auto')),
  auto_source_ref  text,             -- npr. 'filing:123' / 'dividend:45' (dedup)
  status           text not null default 'draft'
                   check (status in ('draft', 'published')),
  published_at     timestamptz,
  created_at       timestamptz not null default now(),
  tweeted          boolean not null default false
);

-- dedup: isti EOD run ne smije istu stvar generirati dvaput
create unique index if not exists news_items_auto_ref_uq
  on public.news_items (auto_source_ref) where auto_source_ref is not null;

create index if not exists news_items_status_idx
  on public.news_items (status, published_at desc);

alter table public.news_items enable row level security;

-- SELECT: published smiju SVI (anon + authenticated); draft vidi SAMO admin
drop policy if exists news_items_select_published on public.news_items;
create policy news_items_select_published on public.news_items
  for select using (status = 'published' or public.is_admin());

-- pisanje: SAMO admin (auto-generacija i X agent idu kroz Edge Functione sa
-- service role, autorizirane x-api-key headerom — ne kroz ove policyje)
drop policy if exists news_items_write on public.news_items;
create policy news_items_write on public.news_items
  for all using (public.is_admin()) with check (public.is_admin());

revoke all on public.news_items from anon;
revoke all on public.news_items from authenticated;
grant select on public.news_items to anon;
grant select, insert, update, delete on public.news_items to authenticated;

-- M32.3: isti razlog kao u migration_blog.sql — service_role grant za
-- Edge Functione kad se migracija izvršava kroz Management API.
do $$ begin
  if exists (select 1 from pg_roles where rolname = 'service_role') then
    grant all on public.news_items to service_role;
  end if;
end $$;
