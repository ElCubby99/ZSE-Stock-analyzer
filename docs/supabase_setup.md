# Supabase setup — korak po korak (Boris)

Faza 3 (M9): auth za portfelj. **Ti kreiraš projekt i ključeve — kod ih samo
čita iz env varijabli.** Lozinke korisnika ne dodiruju ni naš kod ni našu bazu.

## 1. Kreiraj Supabase projekt (~3 min)

1. [supabase.com](https://supabase.com) → Sign in → **New project**
2. Organization: osobna; Name: `burzovni-list`; Database password: generiraj i
   spremi u password manager (to je lozinka Postgresa, NE korisnička);
   Region: **eu-central-1 (Frankfurt)** — najbliže korisnicima.
3. Pričekaj da se projekt digne (~1 min).

## 2. Pokreni schemu + RLS (~1 min)

1. Lijevi izbornik → **SQL Editor** → **New query**
2. Zalijepi CIJELI sadržaj datoteke **`supabase/schema.sql`** iz repo-a → **Run**.
3. Provjera: **Table Editor** → tablica `positions` postoji; na njoj piše
   "RLS enabled".

## 3. Auth postavke (~2 min)

1. **Authentication → Providers → Email**: uključen (default). Provjeri:
   - **Confirm email = ON** (verifikacijski mail prije prvog logina)
   - Secure email change = ON (default)
2. **Authentication → URL Configuration**:
   - Site URL: `https://<tvoja-vercel-domena>`
   - Redirect URLs: dodaj `https://<tvoja-vercel-domena>/portfelj`
     (i `http://localhost:4173/portfelj` ako želiš lokalno testirati)
3. **Authentication → Rate Limits**: ostavi defaulte (Supabase već limitira
   sign-in/sign-up pokušaje) — ništa ne treba mijenjati.

## 4. Ključevi u Vercel env (~2 min)

Supabase: **Project Settings → API**. Trebaju dva podatka:

| Supabase | Vercel env varijabla | Gdje smije |
|---|---|---|
| Project URL | `VITE_SUPABASE_URL` | frontend (javno) — OK |
| `anon` `public` key | `VITE_SUPABASE_ANON_KEY` | frontend (javno) — OK |
| `service_role` key | **NIGDJE za sada** | SAMO server env ako ikad zatreba; NIKAD u frontend/repo |

Vercel: **Project → Settings → Environment Variables** → dodaj obje `VITE_*`
varijable za Production (i Preview ako želiš) → **Redeploy**.

> `anon` ključ je javan po dizajnu — sva zaštita podataka je u RLS policama
> (dokaz da drže: `supabase/rls_test.sql`, svih 5 testova prolazi).
> `service_role` ključ ZAOBILAZI RLS pa ne smije ni blizu frontenda.

## 5. Test (nakon redeploya)

1. Otvori `/portfelj` → REGISTRACIJA → tvoj email + lozinka (≥8 znakova).
2. Stigne verifikacijski mail → klik na link → prijava.
3. Dodaj poziciju (npr. KODT, 3 kom, 3.100 €) → vidiš vrijednost, D/G,
   alokaciju; odjava/prijava — pozicije ostaju.
4. ZABORAVLJENA LOZINKA → mail → nova lozinka.
5. (Po želji) drugi email kao drugi korisnik → njegov portfelj je prazan —
   RLS izolacija radi i u produkciji.

## Sigurnosni sažetak (što je već u kodu)

- `user_id` se NIKAD ne šalje s klijenta: kolona ima `default auth.uid()`, a
  RLS `with check` odbija svaki pokušaj upisa tuđeg ID-a (test 4).
- Frontend ne logira tokene ni lozinke; session drži Supabase SDK
  (autoRefreshToken, verifikacijski/reset linkovi kroz `detectSessionInUrl`).
- Analitička baza (VPS) ostaje odvojena i neizložena — korisnički podaci žive
  isključivo u Supabaseu.
- Bez ključeva u env-u stranica jasno kaže da prijava nije aktivna (i nudi
  lokalni demo prikaz bez spremanja).

---

## Auth v2 (M26): OAuth + portfelj v2 + GDPR — koraci za Borisa

### 1. Migracija sheme (jednom)
SQL Editor → New query → zalijepi CIJELI `supabase/migration_authv2.sql` →
Run. Kreira `profiles` (+trigger na auth.users), `portfolios`,
`portfolio_positions`, RLS + grantove, i seli postojeće `positions` retke u
default portfelj po korisniku (stara tablica se briše). Postojeći
email+password korisnici rade dalje bez ikakve promjene.

### 2. OAuth provideri (Authentication → Providers)
Zajedničko: Supabase callback URL je
`https://<project-ref>.supabase.co/auth/v1/callback` — njega upisuješ kod
providera. U **Authentication → URL Configuration**: Site URL =
`https://burzovnilist.com`; Redirect URLs dodaj:
`https://burzovnilist.com/auth/callback` i
`https://*-<vercel-team>.vercel.app/auth/callback` (preview deployi).

- **Google**: console.cloud.google.com → OAuth consent screen (External,
  logo, privacy = burzovnilist.com/politika-privatnosti) → Credentials →
  OAuth Client ID (Web) → Authorized redirect URI = Supabase callback →
  Client ID + Secret u Supabase Google provider.
- **Facebook**: developers.facebook.com → App (Consumer) → Facebook Login →
  Valid OAuth Redirect URIs = Supabase callback → App ID + Secret u
  Supabase; app prebaci u Live mode (traži Privacy Policy URL).
- **Apple**: TEK kad je plaćen Apple Developer Program — Services ID,
  key + team ID u Supabase, pa u Vercelu postavi
  `VITE_AUTH_APPLE_ENABLED=true` (do tada je gumb skriven).
- **Account linking**: Authentication → Settings → uključi
  "Link accounts with the same email" ako opcija postoji na planu; u
  suprotnom aplikacija već prikazuje poruku i ručno povezivanje u
  postavkama računa radi preko `linkIdentity`.

### 3. Edge Function za brisanje računa (GDPR)
```
supabase functions deploy delete-account
```
(`SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` su
automatski dostupni kao secreti Edge runtimea — service role NIKAD u
frontend.) Funkcija briše isključivo pozivatelja (JWT), bez parametara.

### 4. Provjera (acceptance)
- Google/Facebook login end-to-end na produkciji I Vercel previewu
  (redirect natrag na stranicu s koje je login krenuo).
- Novi OAuth korisnik dobiva "Dovrši registraciju" i ne može do portfelja
  dok ne prihvati uvjete (profiles.terms_accepted_at se popuni).
- dataLayer: sign_up/login s method=google|facebook|email.
- Brisanje računa: auth user + profil + portfelji nestaju; ponovna prijava
  istim emailom = svjež račun.
