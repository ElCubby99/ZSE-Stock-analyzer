import React, {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
} from 'react'

/* M24: GDPR/ePrivacy pristanak na kolačiće — vlastita komponenta, bez
   third-party consent SaaS-a.

   Pravila (strogo):
   - ne-nužne skripte se NE učitavaju dok korisnik ne da izričit pristanak
   - nema pre-checked kućica za ne-nužne kategorije
   - tri gumba jednake vizualne težine; odbijanje ne blokira stranicu
   - pristanak je opoziv u svakom trenutku (footer "Postavke kolačića")
   - pristanak vrijedi max 12 mjeseci; bump CONSENT_VERSION -> banner ponovno */

export const CONSENT_VERSION = 2 // mora odgovarati verziji na /politika-kolacica
// v2 (15.07.2026.): uveden Google Tag Manager (analitička kategorija) —
// promjena politike poništava stare pristanke i banner se prikazuje ponovno.
const KEY = 'bl_consent'
const MAX_AGE_MS = 365 * 24 * 3600 * 1000 // 12 mjeseci

/* Marketinška kategorija je pripremljena ali SKRIVENA dok nema marketinških
   skripti — uključiti tek kad se stvarno dodaju (i ažurirati politiku). */
const MARKETING_ENABLED = false

export function readStoredConsent() {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    const c = JSON.parse(raw)
    if (c.version !== CONSENT_VERSION) return null // nova verzija politike
    if (!c.timestamp || Date.now() - Date.parse(c.timestamp) > MAX_AGE_MS) {
      return null // pristanak stariji od 12 mjeseci -> ponovno pitati
    }
    return {
      version: c.version,
      timestamp: c.timestamp,
      necessary: true,
      analytics: !!c.analytics,
      marketing: !!c.marketing,
    }
  } catch {
    return null
  }
}

function storeConsent(analytics, marketing) {
  const c = {
    version: CONSENT_VERSION,
    timestamp: new Date().toISOString(),
    necessary: true,
    analytics: !!analytics,
    marketing: !!marketing,
  }
  try { localStorage.setItem(KEY, JSON.stringify(c)) } catch { /* noop */ }
  return c
}

/* ---- Google Consent Mode v2 ----
   GTM je STATIČKI u index.html, ali s defaultovima 'denied' postavljenima
   PRIJE snippeta (Consent Mode v2). Ovdje se šalju SAMO consent update
   signali — Googleovi tagovi ne postavljaju kolačiće dok je storage denied
   (zahtjevi nose gcs=G100), a nakon privole prelaze na granted (gcs=G111)
   bez reloada. */

function gtag() { // eslint-disable-line func-style
  window.dataLayer = window.dataLayer || []
  window.dataLayer.push(arguments) // eslint-disable-line prefer-rest-params
}

export function pushEvent(event, params = {}) {
  window.dataLayer = window.dataLayer || []
  window.dataLayer.push({ event, ...params })
}

function deleteGaCookies() {
  // povlačenje privole: _ga i _ga_* se brišu (path=/, apex i trenutna domena)
  const doms = ['', '; domain=.burzovnilist.com', `; domain=${window.location.hostname}`]
  document.cookie.split(';').forEach((c) => {
    const name = c.split('=')[0].trim()
    if (name === '_ga' || name.startsWith('_ga_')) {
      doms.forEach((d) => {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/${d}`
      })
    }
  })
}

export function applyConsentToGoogle(analytics, marketing, prev) {
  gtag('consent', 'update', {
    analytics_storage: analytics ? 'granted' : 'denied',
    ad_storage: marketing ? 'granted' : 'denied',
    ad_user_data: marketing ? 'granted' : 'denied',
    ad_personalization: marketing ? 'granted' : 'denied',
  })
  pushEvent('consent_updated') // custom event za GTM triggere
  if (prev?.analytics && !analytics) deleteGaCookies()
}

const Ctx = createContext({
  consent: null, openSettings: () => {}, decide: () => {},
})

export const useConsent = () => useContext(Ctx)

function CategoryRow({ title, desc, locked, checked, onChange }) {
  return (
    <label className={`cc-cat${locked ? ' cc-locked' : ''}`}>
      <input type="checkbox" checked={checked} disabled={locked}
        onChange={(e) => onChange && onChange(e.target.checked)} />
      <span>
        <b>{title}</b>{locked && <em className="cc-always">uvijek aktivni</em>}
        <small>{desc}</small>
      </span>
    </label>
  )
}

function Banner({ onAcceptAll, onNecessary, onSettings }) {
  return (
    <div className="cc-bar" role="dialog" aria-label="Pristanak na kolačiće">
      <div className="cc-in">
        <p className="cc-txt">
          Nužne kolačiće i pohranu koristimo da stranica radi (prijava,
          pamćenje ovog izbora). Analitičke koristimo <b>samo uz vaš
          pristanak</b> — bez njega se ništa ne-nužno ne učitava. Detalji:{' '}
          <a href="/politika-kolacica">Politika kolačića</a>.
        </p>
        <div className="cc-btns">
          <button type="button" className="cc-btn" onClick={onAcceptAll}>Prihvati sve</button>
          <button type="button" className="cc-btn" onClick={onNecessary}>Samo nužni</button>
          <button type="button" className="cc-btn" onClick={onSettings}>Postavke</button>
        </div>
      </div>
    </div>
  )
}

function SettingsPanel({ current, onSave, onClose }) {
  const [analytics, setAnalytics] = useState(!!current?.analytics)
  const [marketing, setMarketing] = useState(!!current?.marketing)
  return (
    <div className="cc-overlay" role="dialog" aria-modal="true"
      aria-label="Postavke kolačića">
      <div className="cc-panel">
        <div className="cc-panel-head">
          <span className="sec-label" style={{ margin: 0 }}>Postavke kolačića</span>
          <button type="button" className="cc-x" onClick={onClose} aria-label="Zatvori">×</button>
        </div>
        <CategoryRow locked checked title="Nužni"
          desc="Prijava i sesija korisničkog računa (Supabase) te pohrana samog
                izbora o kolačićima. Bez njih stranica ne radi; ne mogu se
                isključiti." />
        <CategoryRow title="Analitički" checked={analytics} onChange={setAnalytics}
          desc="Web analitika posjeta (Google Tag Manager) — koje se stranice
                čitaju. Učitava se tek nakon vašeg pristanka; možete ga povući
                u svakom trenutku." />
        {MARKETING_ENABLED && (
          <CategoryRow title="Marketinški" checked={marketing} onChange={setMarketing}
            desc="Kolačići za oglašavanje. Trenutno ih ne koristimo." />
        )}
        <div className="cc-btns cc-panel-btns">
          <button type="button" className="cc-btn"
            onClick={() => onSave(true, MARKETING_ENABLED ? marketing : false)}>
            Prihvati sve
          </button>
          <button type="button" className="cc-btn" onClick={() => onSave(false, false)}>
            Samo nužni
          </button>
          <button type="button" className="cc-btn"
            onClick={() => onSave(analytics, MARKETING_ENABLED ? marketing : false)}>
            Spremi odabir
          </button>
        </div>
        <p className="cc-note">
          Odbijanje ne ograničava korištenje stranice. Pristanak vrijedi
          najviše 12 mjeseci; opoziv je uvijek dostupan kroz „Postavke
          kolačića" u podnožju. <a href="/politika-kolacica">Politika
          kolačića</a> · <a href="/politika-privatnosti">Politika privatnosti</a>
        </p>
      </div>
    </div>
  )
}

export function ConsentProvider({ children }) {
  const [consent, setConsent] = useState(() => readStoredConsent())
  const [panelOpen, setPanelOpen] = useState(false)

  // povratni posjet: consent default u index.html već je vratio granted/denied
  // PRIJE GTM-a; ovdje nema što učitavati (GTM je statički, Consent Mode).

  const decide = useCallback((analytics, marketing) => {
    const prev = readStoredConsent()
    const c = storeConsent(analytics, marketing)
    setConsent(c)
    setPanelOpen(false)
    // granted/denied ide Googleu odmah — bez reloada; na povlačenje se
    // _ga/_ga_* kolačići brišu
    applyConsentToGoogle(analytics, marketing, prev)
  }, [])

  const openSettings = useCallback(() => setPanelOpen(true), [])

  const value = useMemo(
    () => ({ consent, openSettings, decide }), [consent, openSettings, decide])

  return (
    <Ctx.Provider value={value}>
      {children}
      {!consent && !panelOpen && (
        <Banner
          onAcceptAll={() => decide(true, false)}
          onNecessary={() => decide(false, false)}
          onSettings={() => setPanelOpen(true)} />
      )}
      {panelOpen && (
        <SettingsPanel current={consent}
          onSave={decide} onClose={() => setPanelOpen(false)} />
      )}
    </Ctx.Provider>
  )
}
