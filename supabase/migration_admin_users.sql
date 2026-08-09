-- M62: pregled prijavljenih korisnika (portfelj) za ADMINA — /admin tab
-- "Korisnici". Pokreće se JEDNOM u Supabase SQL editoru (idempotentno;
-- pretpostavlja migration_authv2.sql + migration_blog.sql: profiles,
-- portfolios, portfolio_positions, public.is_admin()).
--
-- Frontend NEMA service key — emailove iz auth.users smije vidjeti samo
-- admin, pa pristup ide kroz SECURITY DEFINER funkciju koja SAMA provjerava
-- public.is_admin(): ne-adminu vraća 0 redaka (bez curenja), adminu popis
-- prijava s brojem portfelja/pozicija po korisniku.

-- portfolios/portfolio_positions su FORCE RLS (ni vlasnik tablice ne
-- zaobilazi policyje) — adminu treba eksplicitni SELECT policy da funkcija
-- može izbrojati portfelje/pozicije po korisniku (policyji se OR-aju s
-- postojećim "vlasnik vidi svoje")
drop policy if exists portfolios_admin_read on public.portfolios;
create policy portfolios_admin_read on public.portfolios
  for select using (public.is_admin());
drop policy if exists portfolio_positions_admin_read on public.portfolio_positions;
create policy portfolio_positions_admin_read on public.portfolio_positions
  for select using (public.is_admin());

create or replace function public.admin_users_overview()
returns table (
  user_id          uuid,
  email            text,
  display_name     text,
  provider         text,
  registered_at    timestamptz,
  last_sign_in_at  timestamptz,
  terms_accepted_at timestamptz,
  n_portfolios     bigint,
  n_positions      bigint
)
language sql
security definer
set search_path = public
as $$
  select u.id,
         u.email::text,
         p.display_name,
         coalesce(u.raw_app_meta_data->>'provider', 'email'),
         u.created_at,
         u.last_sign_in_at,
         p.terms_accepted_at,
         (select count(*) from public.portfolios pf where pf.user_id = u.id),
         (select count(*)
            from public.portfolio_positions pp
            join public.portfolios pf2 on pf2.id = pp.portfolio_id
           where pf2.user_id = u.id)
  from auth.users u
  left join public.profiles p on p.id = u.id
  where public.is_admin()
  order by u.created_at desc
$$;

revoke all on function public.admin_users_overview() from public;
revoke all on function public.admin_users_overview() from anon;
grant execute on function public.admin_users_overview() to authenticated;
