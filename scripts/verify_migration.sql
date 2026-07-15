-- M32: verifikacija migracije pipeline baze u Supabase.
-- Očekivani brojevi redaka su iz IZVORA (lokalni Postgres, dump
-- data/migration/zse_pipeline_2026-07-15.sql.gz, stanje 15.07.2026.).
-- Pokretanje: psql "$SUPABASE_DB_URL" -f scripts/verify_migration.sql
-- Svaki red mora biti OK; DIFF ili MISSING = migracija nije potpuna.
with ocekivano(tablica, redaka) as (values
  ('announcements', 1288::bigint),
  ('api_usage', 0::bigint),
  ('business_profiles', 19::bigint),
  ('calibrations', 18::bigint),
  ('companies', 70::bigint),
  ('dividends', 150::bigint),
  ('filings', 686::bigint),
  ('financials', 19549::bigint),
  ('growth_estimates', 7::bigint),
  ('holdings', 11::bigint),
  ('index_eod', 503::bigint),
  ('pipeline_runs', 430::bigint),
  ('prices_eod', 14540::bigint),
  ('ratios', 0::bigint),
  ('segment_financials', 5::bigint),
  ('share_classes', 73::bigint),
  ('shareholders', 710::bigint),
  ('valuation_changelog', 121::bigint),
  ('valuations', 111::bigint),
  ('watcher_state', 0::bigint)
)
select o.tablica,
       o.redaka                         as izvor,
       s.cnt                            as odrediste,
       case when s.cnt = o.redaka then 'OK'
            when s.cnt is null    then 'MISSING'
            else 'DIFF' end             as status
from ocekivano o
left join lateral (
  select case when to_regclass('public.' || o.tablica) is null then null
              else (xpath('/row/c/text()',
                     query_to_xml(format('select count(*) as c from public.%I',
                                         o.tablica), false, true, ''))
                   )[1]::text::bigint
         end as cnt
) s on true
order by o.tablica;
