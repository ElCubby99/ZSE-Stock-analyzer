import React, { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { supabase } from './supabase.js'
import { fbqTrack, pushEvent, readStoredConsent } from './consent.jsx'
import { useLang } from './i18n/LangContext.jsx'

/* M67: newsletter prijava — GDPR/ZEK usklađeno:
   - DOUBLE OPT-IN: forma šalje zahtjev, korisnik potvrđuje klikom na link
     iz maila (bez potvrde se ništa ne šalje; dokaz privole = confirmed_at)
   - bez pre-checked kućica; sama predaja forme je izričita radnja SAMO za
     newsletter, uz jasan tekst o odjavi i link na Politiku privatnosti
   - odjava jednim klikom (/newsletter/odjava?token=... iz svakog maila)
   - popup: nenametljiv (tek nakon 30 s, ne dok je consent banner otvoren,
     ne na privatnim rutama), pamti odbijanje 60 dana (localStorage bl_nl,
     nužno-funkcionalno — vidi Politiku kolačića) */

const NL_KEY = 'bl_nl'
const DISMISS_DAYS = 60
const POPUP_DELAY_MS = 30_000

function readNlState() {
  try { return JSON.parse(localStorage.getItem(NL_KEY)) || {} } catch { return {} }
}
function writeNlState(patch) {
  try {
    localStorage.setItem(NL_KEY, JSON.stringify({ ...readNlState(), ...patch }))
  } catch { /* noop */ }
}

export function markNewsletterDone() { writeNlState({ done: true }) }

function popupAllowed(pathname) {
  const st = readNlState()
  if (st.done) return false
  if (st.dismissedAt
      && Date.now() - Date.parse(st.dismissedAt) < DISMISS_DAYS * 24 * 3600 * 1000) {
    return false
  }
  // privatne/tehničke rute i sama newsletter potvrda: bez popupa
  const skip = ['/admin', '/auth', '/portfelj', '/newsletter', '/en/newsletter']
  return !skip.some((p) => pathname === p || pathname.startsWith(`${p}/`))
}

/* forma — koristi je landing (/newsletter), header modal i popup; 'website'
   polje je honeypot (skriveno pravim korisnicima; bot koji ga popuni se
   tiho ignorira).

   M68 mjerni lijevak (sve kroz dataLayer/GTM, NIKAD izravni gtag i NIKAD
   email adresa u dataLayeru):
   - newsletter_submit  {source, method:'email'}  SAMO nakon OK odgovora
     backenda (klik koji padne nije konverzija); jednom po uspješnom upisu
     (forma nakon 'sent' nestaje pa dvostruko slanje nije moguće)
   - newsletter_error   {source, reason: invalid_email | server_error}
   - honeypot popunjen -> NIJEDAN event (boti ne ulaze u brojke)
   source vrijednosti: 'page' (landing) | 'header' (gumb u navigaciji) |
   'popup' — iste koje se spremaju uz prijavu u bazi. */
export function NewsletterForm({ source, onDone }) {
  const { lang, t } = useLang()
  const [email, setEmail] = useState('')
  const [hp, setHp] = useState('')
  const [state, setState] = useState('idle') // idle | busy | sent | err
  const privacyHref = lang === 'en' ? '/en/privacy' : '/politika-privatnosti'

  const submit = async (e) => {
    e.preventDefault()
    const isBot = hp.trim() !== ''
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim())) {
      setState('erremail')
      if (!isBot) pushEvent('newsletter_error', { source, reason: 'invalid_email' })
      return
    }
    if (!supabase) {
      setState('err')
      if (!isBot) pushEvent('newsletter_error', { source, reason: 'server_error' })
      return
    }
    setState('busy')
    const { data, error } = await supabase.functions.invoke('newsletter', {
      body: { action: 'subscribe', email: email.trim(), lang, source, website: hp },
    })
    if (error || !data?.ok) {
      setState('err')
      if (!isBot) pushEvent('newsletter_error', { source, reason: 'server_error' })
      return
    }
    setState('sent')
    markNewsletterDone()
    if (!isBot) {
      pushEvent('newsletter_submit', { source, method: 'email' })
      fbqTrack('Lead')
    }
    if (onDone) onDone()
  }

  if (state === 'sent') return <p className="nl-sent">{t('nl.sent')}</p>
  return (
    <form className="nl-form" onSubmit={submit}>
      <div className="nl-row">
        <input type="email" value={email} placeholder={t('nl.placeholder')}
          autoComplete="email" required
          onChange={(e) => { setEmail(e.target.value); if (state === 'erremail') setState('idle') }} />
        {/* honeypot — izvan vidljivog toka, tabIndex -1 */}
        <input type="text" value={hp} onChange={(e) => setHp(e.target.value)}
          className="nl-hp" tabIndex={-1} autoComplete="off" aria-hidden="true"
          name="website" placeholder="website" />
        <button type="submit" className="auth-submit" disabled={state === 'busy'}>
          {t('nl.submit')}
        </button>
      </div>
      {state === 'erremail' && <p className="nl-err">{t('nl.errEmail')}</p>}
      {state === 'err' && <p className="nl-err">{t('nl.errSend')}</p>}
      <p className="nl-note">
        {t('nl.consentNote')}{' '}
        <Link to={privacyHref}>{t('nl.privacyLink')}</Link>.
      </p>
    </form>
  )
}

export function NewsletterModal({ source, onClose }) {
  const { t } = useLang()
  // nakon uspješne prijave "Ne, hvala" više nema smisla -> "Zatvori"
  const [sent, setSent] = useState(false)
  useEffect(() => {
    // M68: forma postala vidljiva — jednom po otvaranju (mount), ne po
    // re-renderu; modal se svakim otvaranjem montira iznova
    pushEvent('newsletter_view', { source })
  }, [source])
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div className="cc-overlay nl-overlay" role="dialog" aria-modal="true"
      aria-label={t('nl.title')} onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="cc-panel nl-panel">
        <div className="cc-panel-head">
          <span className="sec-label" style={{ margin: 0 }}>{t('nl.title')}</span>
          <button type="button" className="cc-x" onClick={onClose}
            aria-label={t('nl.close')}>×</button>
        </div>
        {!sent && <p className="nl-lead">{t('nl.lead')}</p>}
        <NewsletterForm source={source} onDone={() => setSent(true)} />
        <div className="cc-btns" style={{ marginTop: 8 }}>
          <button type="button" className="cc-btn acct-link-btn" onClick={onClose}>
            {sent ? t('nl.close') : t('nl.notNow')}
          </button>
        </div>
      </div>
    </div>
  )
}

/* popup za posjetitelje — montiran u RootLayout (main.jsx) */
export function NewsletterPopup() {
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  const fired = useRef(false) // najviše jednom po učitavanju stranice
  useEffect(() => {
    if (fired.current || !popupAllowed(pathname)) return undefined
    const tick = () => {
      // ne preko consent bannera — pričekaj odluku pa pokušaj ponovno
      if (!readStoredConsent()) { timer.id = setTimeout(tick, POPUP_DELAY_MS); return }
      if (!fired.current && popupAllowed(window.location.pathname)) {
        fired.current = true
        setOpen(true)
      }
    }
    const timer = { id: setTimeout(tick, POPUP_DELAY_MS) }
    return () => clearTimeout(timer.id)
    // pathname namjerno NIJE dependency: timer teče od prvog učitavanja
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  if (!open) return null
  const close = () => {
    writeNlState({ dismissedAt: new Date().toISOString() })
    setOpen(false)
  }
  return <NewsletterModal source="popup" onClose={close} />
}

/* ---------- M68: /newsletter — landing za oglase + SEO ----------
   Forma vidljiva odmah, bez klika i bez scrolla; isti backend poziv kao
   modal. Klijentski router ne dira query string pa UTM parametri iz
   oglasa ostaju u URL-u za GTM/GA4. */
export function NewsletterPage() {
  const { t } = useLang()
  const viewFired = useRef(false)
  useEffect(() => { document.title = `${t('nl.pageTitle')} · Burzovni list` }, [t])
  useEffect(() => {
    // newsletter_view jednom po učitavanju stranice, ne po re-renderu
    if (viewFired.current) return
    viewFired.current = true
    pushEvent('newsletter_view', { source: 'page' })
  }, [])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
        <h1 className="page-h1">{t('nl.pageTitle')}</h1>
        <section>
          <p className="imp-p">{t('nl.pageLead')}</p>
          <NewsletterForm source="page" />
        </section>
        <section>
          <div className="sec-label">{t('nl.whatH')}</div>
          <ul className="imp-p">
            <li>{t('nl.b1')}</li>
            <li>{t('nl.b2')}</li>
            <li>{t('nl.b3')}</li>
            <li>{t('nl.b4')}</li>
          </ul>
          <p className="imp-p">{t('nl.freq')}</p>
        </section>
        <section>
          <div className="sec-label">{t('nl.doiH')}</div>
          <p className="imp-p">{t('nl.doiTxt')}</p>
          <p className="imp-p"><em>{t('common.notAdvice')}</em></p>
        </section>
      </main>
      <SiteFooter />
    </div>
  )
}

/* ---------- /newsletter/potvrda i /newsletter/odjava ---------- */

function useNoindex(title) {
  useEffect(() => {
    document.title = `${title} · Burzovni list`
    const m = document.createElement('meta')
    m.name = 'robots'; m.content = 'noindex'
    document.head.appendChild(m)
    return () => { document.head.removeChild(m) }
  }, [title])
}

function tokenFromSearch(search) {
  const tok = new URLSearchParams(search).get('token') || ''
  return /^[0-9a-f-]{36}$/.test(tok) ? tok : null
}

function TokenPage({ action, title, workingKey, okKey, alreadyKey, badKey, extra }) {
  const { t } = useLang()
  const { search } = useLocation()
  const token = tokenFromSearch(search)
  const [state, setState] = useState(token ? 'busy' : 'notoken')
  useNoindex(title)
  useEffect(() => {
    if (!token || !supabase) {
      if (token && !supabase) setState('bad')
      // link bez valjanog tokena (okrnjen pri kopiranju i sl.)
      if (action === 'confirm' && !token) {
        pushEvent('newsletter_error', { source: 'email_link', reason: 'invalid_token' })
      }
      return
    }
    supabase.functions.invoke('newsletter', { body: { action, token } })
      .then(({ data, error }) => {
        if (error || !data?.ok) setState('bad')
        else setState(data.already ? 'already' : 'ok')
        if (action === 'confirm') {
          /* M68: klik iz maila je NOVA sesija (izvor direct/email), pa se
             newsletter_confirmed u GA4 NE pripisuje oglasu koji je doveo
             korisnika. Konverzija kampanje je newsletter_submit;
             newsletter_confirmed je mjera kvalitete (postotak potvrda).
             Ne spajati kroz cross-session atribuciju. */
          if (!error && data?.ok) {
            markNewsletterDone()
            // samo svježa potvrda — ponovni klik na isti link nije nova potvrda
            if (!data.already) pushEvent('newsletter_confirmed', { source: 'email_link' })
          } else {
            pushEvent('newsletter_error', { source: 'email_link', reason: 'invalid_token' })
          }
        }
      })
  }, [action, token])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
        <h1 className="page-h1">{title}</h1>
        <section>
          {state === 'busy' && <div className="loading">{t(workingKey)}</div>}
          {state === 'ok' && <p className="imp-p okflag">{t(okKey)}</p>}
          {state === 'already' && <p className="imp-p">{t(alreadyKey)}</p>}
          {state === 'bad' && <p className="imp-p">{t(badKey)}</p>}
          {state === 'notoken' && extra}
        </section>
      </main>
      <SiteFooter />
    </div>
  )
}

export function NewsletterPotvrda() {
  const { t } = useLang()
  return (
    <TokenPage action="confirm" title={t('nl.confirmTitle')}
      workingKey="nl.confirmWorking" okKey="nl.confirmOk"
      alreadyKey="nl.confirmAlready" badKey="nl.confirmBad"
      extra={<p className="imp-p">{t('nl.confirmBad')}</p>} />
  )
}

export function NewsletterOdjava() {
  const { t } = useLang()
  return (
    <TokenPage action="unsubscribe" title={t('nl.unsubTitle')}
      workingKey="nl.unsubWorking" okKey="nl.unsubOk"
      alreadyKey="nl.unsubAlready" badKey="nl.unsubBad"
      extra={<p className="imp-p">{t('nl.unsubHowTo')}</p>} />
  )
}
