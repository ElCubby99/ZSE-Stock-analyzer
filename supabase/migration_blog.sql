-- M27: Blog CMS — blog_posts + profiles.is_admin + storage + publish log.
-- Pokreće se JEDNOM u Supabase SQL editoru. Idempotentno.
-- Auto-expose je isključen -> grantovi eksplicitno.

-- ============ 1) ADMIN ULOGA ============
alter table public.profiles add column if not exists is_admin boolean not null default false;
-- PRVOG admina postavlja Boris ručno (NE kroz UI):
--   update public.profiles set is_admin = true where id = '<Borisov auth.users id>';

create or replace function public.is_admin()
returns boolean language sql stable security definer set search_path = public as
$$ select coalesce((select is_admin from public.profiles where id = auth.uid()), false) $$;

-- ============ 2) BLOG_POSTS ============
create table if not exists public.blog_posts (
  id                uuid primary key default gen_random_uuid(),
  slug              text unique not null
                    check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  title             text not null check (char_length(title) between 1 and 200),
  meta_description  text check (meta_description is null
                                or char_length(meta_description) <= 160),
  content_md        text not null,
  tags              text[] default '{}',
  cover_image_url   text check (cover_image_url is null
                                or cover_image_url ~ '^https://'),
  status            text not null default 'draft'
                    check (status in ('draft', 'published', 'archived')),
  published_at      timestamptz,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  author_id         uuid references auth.users (id)
);

create index if not exists blog_posts_status_idx on public.blog_posts (status, published_at desc);

create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end $$;

drop trigger if exists blog_posts_touch on public.blog_posts;
create trigger blog_posts_touch before update on public.blog_posts
  for each row execute function public.touch_updated_at();

alter table public.blog_posts enable row level security;

-- SELECT: objavljeno smiju SVI (build + client čitaju samo published);
-- draft/archived vidi SAMO admin
drop policy if exists blog_posts_select_published on public.blog_posts;
create policy blog_posts_select_published on public.blog_posts
  for select using (status = 'published' or public.is_admin());

-- pisanje: SAMO admin (agent ide kroz Edge Function sa service role,
-- autoriziran BLOG_API_KEY headerom — ne kroz ove policyje)
drop policy if exists blog_posts_write on public.blog_posts;
create policy blog_posts_write on public.blog_posts
  for all using (public.is_admin()) with check (public.is_admin());

revoke all on public.blog_posts from anon;
revoke all on public.blog_posts from authenticated;
grant select on public.blog_posts to anon;
grant select, insert, update, delete on public.blog_posts to authenticated;

-- ============ 3) PUBLISH LOG (za nadzor agentovih objava) ============
create table if not exists public.blog_publish_log (
  id          bigint generated always as identity primary key,
  slug        text not null,
  status      text not null,
  via         text not null, -- 'api_key' | 'admin_ui'
  called_at   timestamptz not null default now()
);
alter table public.blog_publish_log enable row level security;
drop policy if exists blog_publish_log_admin on public.blog_publish_log;
create policy blog_publish_log_admin on public.blog_publish_log
  for select using (public.is_admin());
revoke all on public.blog_publish_log from anon;
revoke all on public.blog_publish_log from authenticated;
grant select on public.blog_publish_log to authenticated;
-- insert radi ISKLJUČIVO Edge Function (service role)

-- ============ 4) STORAGE: bucket blog-media ============
-- public read, write samo admin; cover_image_url prima i bilo koji vanjski
-- https URL (podržano oboje)
insert into storage.buckets (id, name, public)
values ('blog-media', 'blog-media', true)
on conflict (id) do nothing;

drop policy if exists blog_media_read on storage.objects;
create policy blog_media_read on storage.objects
  for select using (bucket_id = 'blog-media');

drop policy if exists blog_media_write on storage.objects;
create policy blog_media_write on storage.objects
  for insert with check (bucket_id = 'blog-media' and public.is_admin());

drop policy if exists blog_media_update on storage.objects;
create policy blog_media_update on storage.objects
  for update using (bucket_id = 'blog-media' and public.is_admin());

drop policy if exists blog_media_delete on storage.objects;
create policy blog_media_delete on storage.objects
  for delete using (bucket_id = 'blog-media' and public.is_admin());

-- M32.3 (nalaz s produkcije): kad se migracija izvršava kroz Management API
-- (a ne SQL editor), Supabaseove default privilegije se NE primjenjuju pa
-- service_role ostaje bez pristupa — Edge Functioni tada padaju s
-- "permission denied". Grant je idempotentan i bezopasan u oba slučaja.
do $$ begin
  if exists (select 1 from pg_roles where rolname = 'service_role') then
    grant all on public.blog_posts, public.blog_publish_log to service_role;
    grant usage, select on all sequences in schema public to service_role;
  end if;
end $$;
