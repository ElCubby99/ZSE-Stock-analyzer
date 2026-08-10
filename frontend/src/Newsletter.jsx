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

/* forma — koristi je i header modal i popup; 'website' polje je honeypot
   (skriveno pravim korisnicima; bot koji ga popuni se tiho ignorira) */
export function NewsletterForm({ source, onDone }) {
  const { lang, t } = useLang()
  const [email, setEmail] = useState('')
  const [hp, setHp] = useState('')
  const [state, setState] = useState('idle') // idle | busy | sent | err
  const privacyHref = lang === 'en' ? '/en/privacy' : '/politika-privatnosti'

  const submit = async (e) => {
    e.preventDefault()
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim())) { setState('erremail'); return }
    if (!supabase) { setState('err'); return }
    setState('busy')
    const { data, error } = await supabase.functions.invoke('newsletter', {
      body: { action: 'subscribe', email: email.trim(), lang, source, website: hp },
    })
    if (error || !data?.ok) { setState('err'); return }
    setState('sent')
    markNewsletterDone()
    pushEvent('newsletter_signup', { source })
    fbqTrack('Lead')
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
        <p className="nl-lead">{t('nl.lead')}</p>
        <NewsletterForm source={source} />
        <div className="cc-btns" style={{ marginTop: 8 }}>
          <button type="button" className="cc-btn acct-link-btn" onClick={onClose}>
            {t('nl.notNow')}
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
    if (!token || !supabase) { if (token && !supabase) setState('bad'); return }
    supabase.functions.invoke('newsletter', { body: { action, token } })
      .then(({ data, error }) => {
        if (error || !data?.ok) setState('bad')
        else setState(data.already ? 'already' : 'ok')
        if (!error && data?.ok && action === 'confirm') markNewsletterDone()
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
