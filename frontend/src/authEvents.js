/* M26 1.5: sign_up/login analytics eventi s method parametrom.
   Globalni listener (importa ga main.jsx) — radi neovisno o stranici na koju
   se korisnik vrati nakon OAuth redirecta. Razlikovanje:
   profiles.created_at unutar zadnjih 60 s = sign_up, inače login.
   Dedupe po korisniku u sessionStorage (tab-sesija) da refresh tokena ili
   povratak na tab ne puša event ponovno. */
import { fbqTrack, pushEvent } from './consent.jsx'
import { supabase } from './supabase.js'

function method(user) {
  // zadnji korišteni provider; email+password nema provider -> 'email'
  const p = user?.app_metadata?.provider
  return p && p !== 'email' ? p : 'email'
}

async function onSignedIn(session) {
  const user = session?.user
  if (!user) return
  const key = `bl_auth_evt_${user.id}`
  try {
    if (sessionStorage.getItem(key)) return
    sessionStorage.setItem(key, '1')
  } catch { /* bez sessionStoragea radije ništa nego duplo */ return }
  const m = method(user)
  // email sign_up event puša registracijska forma u trenutku registracije
  // (session nastaje tek nakon email potvrde) — ovdje email uvijek = login
  let isNew = false
  if (m !== 'email') {
    try {
      const { data } = await supabase
        .from('profiles').select('created_at').eq('id', user.id).maybeSingle()
      isNew = !!data && (Date.now() - Date.parse(data.created_at)) < 60_000
    } catch { /* profil nedostupan -> tretiraj kao login */ }
  }
  pushEvent(isNew ? 'sign_up' : 'login', { method: m })
  // Meta Pixel: registracija = standardni CompleteRegistration event
  // (OAuth registracije; email registracije puša forma u Portfelj.jsx)
  if (isNew) fbqTrack('CompleteRegistration', { method: m })
}

export function initAuthEvents() {
  if (!supabase) return
  supabase.auth.onAuthStateChange((event, session) => {
    if (event === 'SIGNED_IN') onSignedIn(session)
    if (event === 'SIGNED_OUT') {
      try {
        Object.keys(sessionStorage)
          .filter((k) => k.startsWith('bl_auth_evt_'))
          .forEach((k) => sessionStorage.removeItem(k))
      } catch { /* noop */ }
    }
  })
}
