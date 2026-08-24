-- NALOG M30 (interno M71): AI rasprave po dionici — faza 1.
-- Pokreće se JEDNOM u Supabase SQL editoru ili kroz db-sync workflow
-- (input discussions_sql=true). Idempotentno. Ovisi o migration_blog.sql
-- (public.is_admin()) i migration_authv2.sql (profiles).
--
-- Model: 4 AI debatera + moderator raspravljaju nad data_snapshotom iz
-- engina; runda ima fiksni protokol (volley 0-3 + zaključak). AI i ljudski
-- postovi su NEDVOSMISLENO odvojeni (author_type + CHECK). Nikad preporuka
-- kupi/prodaj — stance je ISKLJUČIVO relativno na fer-zonu.

-- ---------- agenti (config, ne hardcode) ----------
create table if not exists public.ai_agents (
  id              text primary key,          -- 'ai_value', 'ai_skeptic', ...
  display_name_hr text not null,
  display_name_en text not null,
  role_prompt     text not null,             -- system prompt (javan po dizajnu)
  model           text not null,             -- default; env može override
  is_active       boolean not null default true,
  bio_hr          text,
  bio_en          text,
  avatar_key      text,                      -- ključ za frontend avatar (boja/inicijali)
  created_at      timestamptz not null default now()
);

-- ---------- runde ----------
create table if not exists public.discussions (
  id            uuid primary key default gen_random_uuid(),
  ticker        text not null,
  round_no      int  not null,
  trigger       text not null default 'manual'
                check (trigger in ('scheduled', 'new_report', 'dividend', 'manual')),
  status        text not null default 'draft'
                check (status in ('draft', 'published', 'archived')),
  data_snapshot jsonb not null,             -- ulaz agenata (zona, metode, D_sust, EOD...)
  summary_hr    text,
  summary_en    text,
  agree_points    jsonb,
  disagree_points jsonb,
  questions_for_humans jsonb,
  created_at    timestamptz not null default now(),
  published_at  timestamptz,
  unique (ticker, round_no)
);
create index if not exists discussions_ticker_idx
  on public.discussions (ticker, round_no desc);
create index if not exists discussions_status_idx
  on public.discussions (status, published_at desc);

-- ---------- postovi (AI i ljudski u istoj niti, tvrdo razdvojeni) ----------
create table if not exists public.discussion_posts (
  id            uuid primary key default gen_random_uuid(),
  discussion_id uuid not null references public.discussions(id) on delete cascade,
  author_type   text not null check (author_type in ('ai', 'human')),
  agent_id      text references public.ai_agents(id),
  user_id       uuid references auth.users(id) on delete set null,
  volley_no     int,                        -- 0-3 za AI protokol; NULL za ljude
  reply_to      uuid references public.discussion_posts(id) on delete set null,
  body_hr       text not null,
  body_en       text,                       -- AI postovi prevedeni; ljudski NULL
  citations     jsonb not null default '[]'::jsonb,  -- [{label,value,source_url,source_type}]
  status        text not null default 'published'
                check (status in ('published', 'hidden', 'flagged', 'pending')),
  model_used    text,
  tokens_in     int,
  tokens_out    int,
  cost_usd      numeric,
  ip_hash       text,                       -- SAMO human: sha256(ip+salt), zaštita od zloupotrebe
  created_at    timestamptz not null default now(),
  check ((author_type = 'ai'    and agent_id is not null and user_id is null)
      or (author_type = 'human' and agent_id is null)),
  -- AI post MORA imati bar jedan citat (validira i orkestrator; baza je mreža)
  check (author_type <> 'ai' or jsonb_array_length(citations) > 0)
);
create index if not exists discussion_posts_disc_idx
  on public.discussion_posts (discussion_id, created_at);
create index if not exists discussion_posts_user_idx
  on public.discussion_posts (user_id) where user_id is not null;

-- ---------- pogledi agenata (track record; NIJE preporuka) ----------
create table if not exists public.agent_calls (
  id            uuid primary key default gen_random_uuid(),
  discussion_id uuid not null references public.discussions(id) on delete cascade,
  agent_id      text not null references public.ai_agents(id),
  ticker        text not null,
  stance        text not null check (stance in ('below_zone', 'in_zone', 'above_zone')),
  horizon_months int not null check (horizon_months in (3, 6, 12)),
  price_at_call numeric,
  zone_low      numeric,
  zone_high     numeric,
  invalidation_condition text not null,     -- "što bi me razuvjerilo"
  evaluated_at  timestamptz,
  price_at_eval numeric,
  outcome       text,
  created_at    timestamptz not null default now(),
  unique (discussion_id, agent_id)
);

-- ---------- @spomeni (gradi se; SUMMONS_ENABLED=false) ----------
create table if not exists public.agent_summons (
  id            uuid primary key default gen_random_uuid(),
  discussion_id uuid not null references public.discussions(id) on delete cascade,
  post_id       uuid not null references public.discussion_posts(id) on delete cascade,
  agent_id      text not null references public.ai_agents(id),
  user_id       uuid references auth.users(id) on delete set null,
  status        text not null default 'queued'
                check (status in ('queued', 'answered', 'rejected_limit',
                                  'rejected_filter', 'deferred')),
  reply_post_id uuid references public.discussion_posts(id) on delete set null,
  created_at    timestamptz not null default now(),
  processed_at  timestamptz
);
create index if not exists agent_summons_status_idx
  on public.agent_summons (status, created_at);

-- ---------- limiti (config, editabilno u /admin) ----------
create table if not exists public.usage_limits (
  key       text primary key,
  value_int int not null,
  note      text
);
insert into public.usage_limits (key, value_int, note) values
  ('summons_per_user_day',      1,   'spomena po korisniku dnevno'),
  ('summons_per_user_week',     5,   'spomena po korisniku tjedno'),
  ('summons_per_thread_day',    5,   'spomena po niti dnevno'),
  ('global_summons_per_day',    50,  'spomena globalno dnevno'),
  ('global_cost_cap_usd_day',   5,   'USD cap na API trošak dnevno'),
  ('new_account_cooldown_hours',48,  'min starost računa za komentiranje'),
  ('comment_max_chars',         2000,'max duljina komentara'),
  ('comments_per_user_hour',    10,  'komentara po korisniku na sat')
on conflict (key) do nothing;

-- ---------- flagovi po korisniku ----------
create table if not exists public.user_flags (
  user_id     uuid primary key references auth.users(id) on delete cascade,
  can_comment boolean not null default true,
  can_summon  boolean not null default true,
  is_banned   boolean not null default false,
  note        text
);

-- ---------- RLS ----------
alter table public.ai_agents        enable row level security;
alter table public.discussions      enable row level security;
alter table public.discussion_posts enable row level security;
alter table public.agent_calls      enable row level security;
alter table public.agent_summons    enable row level security;
alter table public.usage_limits     enable row level security;
alter table public.user_flags       enable row level security;

-- javno čitanje: agenti, objavljene runde, objavljeni postovi, pogledi
drop policy if exists ai_agents_select on public.ai_agents;
create policy ai_agents_select on public.ai_agents
  for select using (true);
drop policy if exists discussions_select on public.discussions;
create policy discussions_select on public.discussions
  for select using (status = 'published' or public.is_admin());
drop policy if exists discussion_posts_select on public.discussion_posts;
create policy discussion_posts_select on public.discussion_posts
  for select using (
    (status = 'published' and exists (select 1 from public.discussions d
        where d.id = discussion_id and d.status = 'published'))
    or public.is_admin()
    or (user_id is not null and user_id = auth.uid()));  -- vlastiti pending
drop policy if exists agent_calls_select on public.agent_calls;
create policy agent_calls_select on public.agent_calls
  for select using (exists (select 1 from public.discussions d
      where d.id = discussion_id and d.status = 'published')
    or public.is_admin());

-- pisanje rundi/AI postova: ISKLJUČIVO service role (Edge Function /
-- pipeline) — nema policyja; admin smije moderirati postove i objaviti runde
drop policy if exists discussions_admin_write on public.discussions;
create policy discussions_admin_write on public.discussions
  for update using (public.is_admin()) with check (public.is_admin());
drop policy if exists discussion_posts_admin_mod on public.discussion_posts;
create policy discussion_posts_admin_mod on public.discussion_posts
  for update using (public.is_admin()) with check (public.is_admin());

-- ljudski komentari idu kroz Edge Function discussion-comment (service role,
-- limiti + filter tamo). Izravni INSERT policy NE postoji namjerno — anon
-- ključ ne smije zaobići limite. Vlastiti post: skrivanje unutar 15 minuta.
drop policy if exists discussion_posts_own_hide on public.discussion_posts;
create policy discussion_posts_own_hide on public.discussion_posts
  for update using (
    author_type = 'human' and user_id = auth.uid()
    and created_at > now() - interval '15 minutes')
  with check (
    author_type = 'human' and user_id = auth.uid() and status = 'hidden');

-- summons/limits/flags: admin čita i uređuje; service role mimo RLS-a
drop policy if exists agent_summons_admin on public.agent_summons;
create policy agent_summons_admin on public.agent_summons
  for all using (public.is_admin()) with check (public.is_admin());
drop policy if exists usage_limits_admin on public.usage_limits;
create policy usage_limits_admin on public.usage_limits
  for all using (public.is_admin()) with check (public.is_admin());
drop policy if exists user_flags_admin on public.user_flags;
create policy user_flags_admin on public.user_flags
  for all using (public.is_admin()) with check (public.is_admin());

-- grantovi (auto-expose isključen — eksplicitno)
revoke all on public.ai_agents, public.discussions, public.discussion_posts,
  public.agent_calls, public.agent_summons, public.usage_limits,
  public.user_flags from anon, authenticated;
grant select on public.ai_agents, public.discussions, public.discussion_posts,
  public.agent_calls to anon, authenticated;
grant update on public.discussions, public.discussion_posts to authenticated;
grant select, insert, update, delete on public.agent_summons,
  public.usage_limits, public.user_flags to authenticated;  -- RLS = is_admin
do $$ begin
  if exists (select 1 from pg_roles where rolname = 'service_role') then
    grant all on public.ai_agents, public.discussions, public.discussion_posts,
      public.agent_calls, public.agent_summons, public.usage_limits,
      public.user_flags to service_role;
  end if;
end $$;

-- ---------- GDPR: brisanje računa anonimizira postove, NE briše nit ----------
create or replace function public.anonymize_discussion_posts()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  update public.discussion_posts
     set body_hr = '[obrisano]', body_en = null, user_id = null, ip_hash = null
   where user_id = old.id;
  return old;
end $$;
drop trigger if exists trg_anonymize_discussion_posts on auth.users;
create trigger trg_anonymize_discussion_posts
  before delete on auth.users
  for each row execute function public.anonymize_discussion_posts();

-- ---------- seed agenata (idempotentno; /admin ih smije uređivati) ----------
insert into public.ai_agents
  (id, display_name_hr, display_name_en, role_prompt, model, bio_hr, bio_en, avatar_key)
values
  ('ai_value', 'Vrijednosni', 'Value',
   'Ti si Vrijednosni — fundamentalni analitičar Burzovnog lista. Radiš ISKLJUČIVO s podacima iz data_snapshota i javnih stranica platforme. Fokus: fer-zona i metode iz kojih je nastala, kvaliteta dobiti (jednokratne stavke!), bilanca, D_sust i pokriće dividende. Svaku brojku citiraš (izvor iz snapshota ili URL). Nikad ne izgovaraš preporuku, cilj-cijenu ni riječi kupi/prodaj; tvoj stav je isključivo odnos cijene i fer-zone s obrazloženjem. Max 250 riječi po postu. Kada nemaš ništa novo za reći — šutiš.',
   'claude-sonnet-5',
   'Fundamentalist. Gleda fer-zonu, metode vrednovanja, kvalitetu dobiti i bilancu. Pristranost: vjeruje brojkama iz izvješća više nego tržišnom sentimentu. Pokreće ga model claude-sonnet-5.',
   'Fundamentalist. Looks at the fair-value zone, valuation methods, earnings quality and the balance sheet. Bias: trusts reported numbers over market sentiment. Powered by claude-sonnet-5.',
   'value'),
  ('ai_skeptic', 'Skeptik', 'Skeptic',
   'Ti si Skeptik — advocatus diaboli Burzovnog lista. Tvoj posao je RUŠITI tezu ostalih: jednokratne stavke u dobiti, nelikvidnost i staru cijenu, koncentrirano vlasništvo, računovodstvene zastavice, pretpostavke modela koje ne drže. NIKAD se ne slažeš prvi; ako je teza čvrsta, napadaš njezinu najslabiju pretpostavku. Svaku tvrdnju citiraš. Bez preporuka, bez kupi/prodaj; tvoj stav je isključivo odnos cijene i fer-zone. Max 250 riječi. Uljudnost i prepričavanje su zabranjeni.',
   'claude-sonnet-5',
   'Advocatus diaboli. Traži jednokratne stavke, nelikvidnost, upravljačke i računovodstvene zastavice. Pristranost: namjerno negativan — njegov posao je da teza preživi napad. Pokreće ga model claude-sonnet-5.',
   'Devil''s advocate. Hunts one-off items, illiquidity, governance and accounting red flags. Bias: deliberately negative — his job is to make the thesis survive an attack. Powered by claude-sonnet-5.',
   'skeptic'),
  ('ai_macro', 'Makro', 'Macro',
   'Ti si Makro — sektorski i makro kontekst Burzovnog lista. Fokus: kamatna okolina (HNB/ECB), ciklus sektora, globalni peer set iz snapshota (KONTEKST, ne sidro vrednovanja), tečajne i regulatorne teme. Ne ponavljaš firmine brojke koje su drugi već iznijeli — dodaješ okolinu. Svaku brojku citiraš (snapshot ili URL izvora). Bez preporuka, bez kupi/prodaj; stav isključivo kao odnos cijene i fer-zone. Max 250 riječi.',
   'claude-sonnet-5',
   'Sektor i okruženje: kamate, ciklus, globalni peerovi kao kontekst. Pristranost: vidi firmu kroz okolinu — ponekad podcijeni specifičnosti firme. Pokreće ga model claude-sonnet-5.',
   'Sector and environment: rates, the cycle, global peers as context. Bias: sees the company through its environment — can underweight company specifics. Powered by claude-sonnet-5.',
   'macro'),
  ('ai_owner', 'Vlasnički', 'Ownership',
   'Ti si Vlasnički — analitičar dividendi i kapitala Burzovnog lista. Fokus: payout politika i njezina dosljednost, D_sust naspram stvarnih isplata, top-10 dioničari i OMF udjeli (tko kontrolira odluke), free float, alokacija kapitala uprave (zadržana dobit, otkupi, investicije). Svaku brojku citiraš. Bez preporuka, bez kupi/prodaj; stav isključivo kao odnos cijene i fer-zone. Max 250 riječi.',
   'claude-sonnet-5',
   'Dividende i kapital: payout politika, D_sust, struktura vlasništva, alokacija kapitala. Pristranost: firmu gleda očima manjinskog dioničara koji živi od isplata. Pokreće ga model claude-sonnet-5.',
   'Dividends and capital: payout policy, sustainable dividend, ownership structure, capital allocation. Bias: sees the company through the eyes of a minority shareholder living off payouts. Powered by claude-sonnet-5.',
   'owner'),
  ('ai_mod', 'Moderator', 'Moderator',
   'Ti si Moderator rasprava Burzovnog lista. NEMAŠ stav. Otvaraš rundu s 5-8 ČINJENICA iz data_snapshota s izvorima, bez interpretacije. Zatvaraš rundu sažetkom: oko čega su se debateri složili, oko čega nisu (s imenima), i TOČNO 3 pitanja za ljudske čitatelje. Provjeravaš da svaka citirana brojka postoji u snapshotu ili ima URL. Bez preporuka; riječi kupi/prodaj ne postoje u tvom rječniku.',
   'claude-opus-4-8',
   'Bez stava. Otvara rundu činjenicama, zatvara sažetkom slaganja i neslaganja, provjerava citate. Pokreće ga model claude-opus-4-8.',
   'No stance. Opens the round with facts, closes with a summary of agreements and disagreements, checks citations. Powered by claude-opus-4-8.',
   'mod')
on conflict (id) do nothing;

-- ---------- M72: AI Forum — forumske teme (ETF, mirovinski fondovi) ----------
-- kind='ai_round' su runde 4 debatera; kind='topic' su teme koje moderator
-- otvara činjenicama (bez debate, bez calls) i koje žive na /forum/<slug>.
alter table public.discussions add column if not exists kind text not null default 'ai_round';
alter table public.discussions add column if not exists slug text;
alter table public.discussions add column if not exists title_hr text;
alter table public.discussions add column if not exists title_en text;
alter table public.discussions add column if not exists related_href text;
alter table public.discussions add column if not exists related_href_en text;
do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'discussions_kind_check') then
    alter table public.discussions add constraint discussions_kind_check
      check (kind in ('ai_round', 'topic'));
  end if;
end $$;
create unique index if not exists discussions_slug_uidx
  on public.discussions (slug) where slug is not null;

-- ---------- M72: protokol v2 — role_promptovi (repo je izvor istine) ----------
-- 1) moderator uz činjenice IMENUJE 1-2 točke spora i dodjeljuje volley 3
--    samo izravno napadnutom agentu; vodi i forumske teme
-- 2) Skeptik u TEZI ne vodi vlasničke argumente (lane Vlasničkog); u
--    pobijanju smije napasti svaku tezu
-- 3) Makro brojke uzima isključivo iz snapshota (macro blok kad postoji)
update public.ai_agents set role_prompt =
  'Ti si Moderator AI Foruma Burzovnog lista. NEMAŠ stav. Otvaraš rundu s 5-8 ČINJENICA iz data_snapshota s izvorima, bez interpretacije, i na kraju uvodnog posta IMENUJEŠ 1-2 točke spora koje runda mora razriješiti — napetosti koje podaci sami nose (npr. izvanredna isplata naspram D_sust, razmaknute metode, cijena na rubu zone). Zadnju riječ (volley 3) dodjeljuješ isključivo agentu čija je teza u volley 2 izravno napadnuta; ako takvog nema, runda ide na zaključak. Zatvaraš rundu sažetkom: oko čega su se debateri složili, oko čega nisu (s imenima), i TOČNO 3 pitanja za ljudske čitatelje. Za forumske teme (ETF-ovi, mirovinski fondovi) otvaraš temu činjenicama s izvorima i 2-3 pitanjima za čitatelje — bez debate i bez stava. Provjeravaš da svaka citirana brojka postoji u snapshotu ili ima URL. Bez preporuka; riječi kupi/prodaj ne postoje u tvom rječniku.'
  where id = 'ai_mod';
update public.ai_agents set role_prompt =
  'Ti si Skeptik — advocatus diaboli Burzovnog lista. Tvoj posao je RUŠITI tezu ostalih: jednokratne stavke, kvaliteta i ciklička napuhanost dobiti, nelikvidnost i stara/tanka cijena, računovodstvene zastavice, pretpostavke metodologije koje ne drže. U TEZI (volley 1) vlasnička struktura, payout politika i ponašanje kontrolora NISU tvoj teren — to je teren Vlasničkog; u pobijanju (volley 2+) smiješ napasti svačiju tezu, uključujući vlasničku. NIKAD se ne slažeš prvi; ako je teza čvrsta, napadaš njezinu najslabiju pretpostavku. Svaku tvrdnju citiraš. Bez preporuka, bez kupi/prodaj; tvoj stav je isključivo odnos cijene i fer-zone. Max 250 riječi. Uljudnost i prepričavanje su zabranjeni.'
  where id = 'ai_skeptic';
update public.ai_agents set role_prompt =
  'Ti si Makro — sektorski i makro kontekst Burzovnog lista. Fokus: kamatna okolina (HNB/ECB), ciklus sektora, globalni peer set iz snapshota (KONTEKST, ne sidro vrednovanja), tečajne i regulatorne teme. Ne ponavljaš firmine brojke koje su drugi već iznijeli — dodaješ okolinu. Ako data_snapshot sadrži makro/sektorske serije (blok macro), brojke uzimaš i citiraš ISKLJUČIVO iz njega; smjer bez brojke u snapshotu izričito označavaš kao kvalitativnu procjenu. Svaku brojku citiraš (snapshot ili URL izvora). Bez preporuka, bez kupi/prodaj; stav isključivo kao odnos cijene i fer-zone. Max 250 riječi.'
  where id = 'ai_macro';
