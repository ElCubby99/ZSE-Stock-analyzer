/* Supabase klijent — SAMO anon key (public) u frontendu; service_role NIKAD.
   Ključevi dolaze iz Vercel env varijabli (VITE_*); bez njih je auth ugašen
   i Portfelj prikazuje uputu za postavljanje. Lozinke ne prolaze kroz naš
   kod ni logove — cijeli auth flow (hash, verifikacija, reset) je Supabase. */
import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const anon = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = (url && anon)
  ? createClient(url, anon, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true, // password-reset/verifikacijski linkovi
    },
  })
  : null

/* DEMO režim (samo lokalni razvoj): VITE_PORTFELJ_DEMO=1 renderira portfelj
   s pozicijama u memoriji BEZ prijave — jasno označeno na stranici.
   U produkciji se NE postavlja. */
export const DEMO = import.meta.env.VITE_PORTFELJ_DEMO === '1'
