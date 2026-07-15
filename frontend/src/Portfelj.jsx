import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { SiteFooter, SiteHeader, useOverview } from './Shell.jsx'
import { dash, num, pct } from './format.js'
import { APPLE_ENABLED, DEMO, supabase, TERMS_VERSION } from './supabase.js'
import { pushEvent } from './consent.jsx'

/* Auth v2 (M26, nadogradnja M9): OAuth (Google/Facebook, Apple iza flaga) +
   email+password; terms gate za OAuth korisnike; portfelj na portfolios/
   portfolio_positions (RLS: vlasnik i nitko drugi); postavke računa s
   povezanim providerima, GDPR exportom i brisanjem računa.
   Lozinke NIKAD ne prolaze kroz naš kod — sve radi Supabase SDK. */

const EMAIL_NOTE = 'Email koristimo isključivo za prijavu i oporavak lozinke — bez newslettera i marketinga.'

/* ---------- OAuth gumbi (brand smjernice, bez custom stilizacije) ---------- */

const G_ICON = (
  <svg viewBox="0 0 18 18" width="18" height="18" aria-hidden="true">
    <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92a8.78 8.78 0 0 0 2.68-6.62z"/>
    <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z"/>
    <path fill="#FBBC05" d="M3.97 10.72a5.41 5.41 0 0 1 0-3.44V4.95H.96a9 9 0 0 0 0 8.1l3.01-2.33z"/>
    <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.59A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z"/>
  </svg>
)

const FB_ICON = (
  <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
    <path fill="#fff" d="M24 12a12 12 0 1 0-13.88 11.85v-8.38H7.08V12h3.04V9.36c0-3 1.79-4.67 4.53-4.67 1.31 0 2.68.24 2.68.24v2.95H15.8c-1.49 0-1.95.93-1.95 1.87V12h3.32l-.53 3.47h-2.79v8.38A12 12 0 0 0 24 12z"/>
  </svg>
)

const APPLE_ICON = (
  <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
    <path fill="#fff" d="M16.37 12.9c.03 3.2 2.81 4.27 2.84 4.28-.02.08-.44 1.52-1.46 3.01-.88 1.29-1.8 2.57-3.24 2.6-1.42.03-1.87-.84-3.5-.84-1.62 0-2.13.81-3.47.87-1.39.05-2.45-1.4-3.34-2.68C2.38 17.5 1 12.73 2.86 9.5a5.2 5.2 0 0 1 4.4-2.67c1.37-.03 2.66.92 3.5.92.83 0 2.4-1.14 4.05-.97.69.03 2.63.28 3.87 2.1-.1.06-2.31 1.35-2.31 4.02zM13.7 4.94c.74-.9 1.24-2.14 1.1-3.38-1.06.04-2.36.71-3.12 1.6-.69.79-1.29 2.06-1.13 3.28 1.19.09 2.4-.6 3.15-1.5z"/>
  </svg>
)

function OAuthButtons({ setMsg }) {
  const start = async (provider) => {
    setMsg(null)
    try { sessionStorage.setItem('bl_return_to', window.location.pathname) } catch { /* noop */ }
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    })
    if (error) {
      const dup = /already|registered|exists/i.test(error.message)
      setMsg({ t: 'err',
        s: dup
          ? 'Račun s ovim emailom već postoji — prijavi se izvornim načinom (email/Google/…) pa poveži račune u postavkama.'
          : error.message })
    }
  }
  return (
    <div className="oauth-box">
      <button type="button" className="oauth-btn oauth-google" onClick={() => start('google')}>
        {G_ICON}<span>Nastavi s Googleom</span>
      </button>
      <button type="button" className="oauth-btn oauth-facebook" onClick={() => start('facebook')}>
        {FB_ICON}<span>Nastavi s Facebookom</span>
      </button>
      {APPLE_ENABLED && (
        <button type="button" className="oauth-btn oauth-apple" onClick={() => start('apple')}>
          {APPLE_ICON}<span>Nastavi s Apple računom</span>
        </button>
      )}
      <div className="oauth-terms">
        Nastavkom prihvaćate <a href="/uvjeti-koristenja" target="_blank" rel="noreferrer">Uvjete
        korištenja</a> i <a href="/politika-privatnosti" target="_blank" rel="noreferrer">Politiku
        privatnosti</a>.
      </div>
      <div className="oauth-sep"><span>ili emailom</span></div>
    </div>
  )
}

/* ---------- email+password (M9, zadržano) ---------- */

export function AuthForms({ onDemo }) {
  const [mode, setMode] = useState('login') // login | signup | reset
  const [email, setEmail] = useState('')
  const [pass, setPass] = useState('')
  const [terms, setTerms] = useState(false) // NIKAD pre-checked (GDPR)
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState(false)

  const run = async (fn, okMsg, gtmEvent) => {
    setBusy(true); setMsg(null)
    const { error } = await fn()
    setBusy(false)
    setMsg(error ? { t: 'err', s: error.message } : { t: 'ok', s: okMsg })
    if (!error && gtmEvent) pushEvent(gtmEvent, { method: 'email' })
  }
  const submit = (e) => {
    e.preventDefault()
    if (mode === 'signup') {
      if (!terms) { // registracija bez prihvata uvjeta ne prolazi
        setMsg({ t: 'err', s: 'Za registraciju je potrebno prihvatiti Uvjete korištenja i Politiku privatnosti.' })
        return
      }
      run(() => supabase.auth.signUp({
        email, password: pass,
        options: {
          emailRedirectTo: `${window.location.origin}/portfelj`,
          // timestamp prihvata uvjeta uz korisnika; profiles trigger ga
          // kopira u profiles.terms_accepted_at
          data: {
            terms_accepted_at: new Date().toISOString(),
            terms_version: TERMS_VERSION,
          },
        },
      }), 'Registracija zaprimljena — provjeri email i potvrdi adresu, pa se prijavi.',
      'sign_up')
    } else if (mode === 'login') {
      // login event puša globalni auth listener (authEvents.js) na SIGNED_IN
      run(() => supabase.auth.signInWithPassword({ email, password: pass }),
        'Prijavljen.')
    } else {
      run(() => supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/portfelj`,
      }), 'Ako račun postoji, poslan je email s poveznicom za novu lozinku.')
    }
  }
  return (
    <div className="auth-box">
      <OAuthButtons setMsg={setMsg} />
      <div className="auth-tabs">
        {[['login', 'PRIJAVA'], ['signup', 'REGISTRACIJA'], ['reset', 'ZABORAVLJENA LOZINKA']].map(([k, l]) => (
          <button key={k} className={mode === k ? 'on' : ''} onClick={() => { setMode(k); setMsg(null) }}>{l}</button>
        ))}
      </div>
      <form onSubmit={submit} className="auth-form">
        <label>Email
          <input type="email" required autoComplete="email" value={email}
            onChange={(e) => setEmail(e.target.value)} />
        </label>
        {mode !== 'reset' && (
          <label>Lozinka
            <input type="password" required minLength={8}
              autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
              value={pass} onChange={(e) => setPass(e.target.value)} />
          </label>
        )}
        {mode === 'signup' && (
          <label className="auth-terms">
            <input type="checkbox" required checked={terms}
              onChange={(e) => setTerms(e.target.checked)} />
            <span>Pročitao/la sam i prihvaćam{' '}
              <a href="/uvjeti-koristenja" target="_blank" rel="noreferrer">Uvjete
              korištenja</a> i{' '}
              <a href="/politika-privatnosti" target="_blank" rel="noreferrer">Politiku
              privatnosti</a>.</span>
          </label>
        )}
        <button className="auth-submit" disabled={busy}>
          {mode === 'login' ? 'Prijavi se' : mode === 'signup' ? 'Registriraj se' : 'Pošalji poveznicu'}
        </button>
        {msg && <div className={`auth-msg ${msg.t}`}>{msg.s}</div>}
        <div className="auth-note">{EMAIL_NOTE} Lozinku pohranjuje i hashira Supabase — nikad naša baza.</div>
      </form>
      {onDemo && (
        <div className="auth-demo-hint">
          lokalni pregled bez računa: <button onClick={onDemo}>demo prikaz</button>
        </div>
      )}
    </div>
  )
}

function NewPasswordForm() {
  const [pass, setPass] = useState('')
  const [msg, setMsg] = useState(null)
  const submit = async (e) => {
    e.preventDefault()
    const { error } = await supabase.auth.updateUser({ password: pass })
    setMsg(error ? { t: 'err', s: error.message }
      : { t: 'ok', s: 'Lozinka promijenjena — prijavljen si.' })
  }
  return (
    <form onSubmit={submit} className="auth-form auth-box">
      <div className="prof-klabel">NOVA LOZINKA</div>
      <label>Nova lozinka
        <input type="password" required minLength={8} autoComplete="new-password"
          value={pass} onChange={(e) => setPass(e.target.value)} />
      </label>
      <button className="auth-submit">Postavi lozinku</button>
      {msg && <div className={`auth-msg ${msg.t}`}>{msg.s}</div>}
    </form>
  )
}

/* ---------- M26 1.2: terms gate za OAuth korisnike (blokira SVE) ---------- */

function TermsGate({ onAccepted }) {
  const [terms, setTerms] = useState(false)
  const [msg, setMsg] = useState(null)
  const submit = async (e) => {
    e.preventDefault()
    if (!terms) return
    const { data: { user } } = await supabase.auth.getUser()
    const { error } = await supabase.from('profiles')
      .update({ terms_accepted_at: new Date().toISOString(), terms_version: TERMS_VERSION })
      .eq('id', user.id)
    if (error) setMsg({ t: 'err', s: error.message })
    else onAccepted()
  }
  return (
    <div className="auth-box">
      <div className="prof-klabel">DOVRŠI REGISTRACIJU</div>
      <p className="imp-p">Još samo jedan korak: za korištenje računa potreban
      je prihvat uvjeta. Bez prihvata račun nije aktivan.</p>
      <form onSubmit={submit} className="auth-form">
        <label className="auth-terms">
          <input type="checkbox" required checked={terms}
            onChange={(e) => setTerms(e.target.checked)} />
          <span>Pročitao/la sam i prihvaćam{' '}
            <a href="/uvjeti-koristenja" target="_blank" rel="noreferrer">Uvjete
            korištenja</a> i{' '}
            <a href="/politika-privatnosti" target="_blank" rel="noreferrer">Politiku
            privatnosti</a>.</span>
        </label>
        <button className="auth-submit" disabled={!terms}>Prihvaćam i nastavi</button>
        {msg && <div className={`auth-msg ${msg.t}`}>{msg.s}</div>}
        <div className="auth-note">
          Ne želiš prihvatiti? <button type="button" className="cc-inline-link"
            onClick={() => supabase.auth.signOut()}>Odjavi se</button> — račun
          možeš obrisati emailom na info@burzovnilist.com.
        </div>
      </form>
    </div>
  )
}

/* ---------- M26 1.4 + DIO 3: postavke računa ---------- */

const PROVIDER_HR = { google: 'Google', facebook: 'Facebook', apple: 'Apple', email: 'Email + lozinka' }

function AccountSettings({ session, profile, onClose }) {
  const [identities, setIdentities] = useState(null)
  const [msg, setMsg] = useState(null)
  const [confirmEmail, setConfirmEmail] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    const { data, error } = await supabase.auth.getUserIdentities()
    if (!error) setIdentities(data?.identities || [])
  }, [])
  useEffect(() => { load() }, [load])

  const link = async (provider) => {
    setMsg(null)
    try { sessionStorage.setItem('bl_return_to', '/portfelj') } catch { /* noop */ }
    const { error } = await supabase.auth.linkIdentity({
      provider, options: { redirectTo: `${window.location.origin}/auth/callback` },
    })
    if (error) setMsg({ t: 'err', s: error.message })
  }
  const unlink = async (identity) => {
    setMsg(null)
    const { error } = await supabase.auth.unlinkIdentity(identity)
    if (error) setMsg({ t: 'err', s: error.message })
    else { setMsg({ t: 'ok', s: 'Provider odvezan.' }); load() }
  }

  const exportData = async () => {
    // GDPR export: profil + portfelji + pozicije (vlastiti podaci, RLS)
    const uid = session.user.id
    const [pf, pos] = await Promise.all([
      supabase.from('portfolios').select('*'),
      supabase.from('portfolio_positions').select('*'),
    ])
    const blob = new Blob([JSON.stringify({
      exported_at: new Date().toISOString(),
      user: { id: uid, email: session.user.email },
      profile,
      portfolios: pf.data || [],
      positions: pos.data || [],
    }, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'burzovnilist-moji-podaci.json'
    a.click()
    URL.revokeObjectURL(a.href)
  }

  const deleteAccount = async () => {
    if (confirmEmail !== session.user.email) {
      setMsg({ t: 'err', s: 'Za potvrdu upiši točan email računa.' })
      return
    }
    setBusy(true); setMsg(null)
    const { error } = await supabase.functions.invoke('delete-account', { method: 'POST' })
    setBusy(false)
    if (error) { setMsg({ t: 'err', s: `Brisanje nije uspjelo: ${error.message}` }); return }
    await supabase.auth.signOut()
    window.location.assign('/?racun=obrisan')
  }

  const linked = new Set((identities || []).map((i) => i.provider))
  const linkable = ['google', 'facebook', ...(APPLE_ENABLED ? ['apple'] : [])]
    .filter((p) => !linked.has(p))

  return (
    <div className="auth-box">
      <div className="cc-panel-head">
        <span className="prof-klabel" style={{ margin: 0 }}>POSTAVKE RAČUNA</span>
        <button type="button" className="cc-x" onClick={onClose} aria-label="Zatvori">×</button>
      </div>

      <div className="sec-label">Povezani načini prijave</div>
      {identities === null ? <div className="loading">učitavam…</div> : (
        <ul className="acct-list">
          {identities.map((i) => (
            <li key={i.identity_id || i.id}>
              <b>{PROVIDER_HR[i.provider] || i.provider}</b>
              {identities.length > 1 && (
                <button type="button" className="pf-del" onClick={() => unlink(i)}>odveži</button>
              )}
            </li>
          ))}
        </ul>
      )}
      {identities !== null && identities.length === 1 && (
        <div className="auth-note">Zadnji način prijave se ne može odvezati —
        prvo poveži drugi provider.</div>
      )}
      {linkable.length > 0 && (
        <div className="acct-link-row">
          poveži još: {linkable.map((p) => (
            <button type="button" key={p} className="cc-btn acct-link-btn"
              onClick={() => link(p)}>{PROVIDER_HR[p]}</button>
          ))}
        </div>
      )}

      <div className="sec-label" style={{ marginTop: 18 }}>Moji podaci (GDPR)</div>
      <button type="button" className="auth-submit" onClick={exportData}>
        Preuzmi svoje podatke (JSON)
      </button>

      <div className="sec-label" style={{ marginTop: 18 }}>Brisanje računa</div>
      <p className="auth-note">Brisanje je trajno: uklanja račun, profil i sve
      portfelje. Za potvrdu upiši email računa ({session.user.email}).</p>
      <div className="pf-add" style={{ margin: '8px 0' }}>
        <input type="email" placeholder="email za potvrdu" value={confirmEmail}
          onChange={(e) => setConfirmEmail(e.target.value)} style={{ width: 260 }} />
        <button type="button" className="acct-danger" disabled={busy} onClick={deleteAccount}>
          Obriši račun trajno
        </button>
      </div>
      {msg && <div className={`auth-msg ${msg.t}`}>{msg.s}</div>}
    </div>
  )
}

/* ---------- portfelj (v2 tablice) ---------- */

function PositionsView({ rows, ov, onAdd, onDelete, demo, email, onLogout, onSettings }) {
  const [t, setT] = useState(''); const [q, setQ] = useState(''); const [c, setC] = useState('')
  const byTicker = useMemo(
    () => Object.fromEntries((ov?.stocks || []).map((s) => [s.ticker, s])), [ov])
  const enriched = rows.map((r) => {
    const s = byTicker[r.ticker.toUpperCase()]
    const price = s?.price ?? null
    const value = price !== null ? price * r.quantity : null
    const cost = r.avg_price * r.quantity
    return { ...r,
      s,
      price,
      value,
      cost,
      pl: value !== null ? value - cost : null,
      illiquid: s?.illiquid || false }
  })
  const total = enriched.reduce((a, r) => a + (r.value || 0), 0)
  const totalCost = enriched.reduce((a, r) => a + r.cost, 0)
  const bySector = {}
  enriched.forEach((r) => {
    if (r.value === null) return
    const key = r.s?.sector || 'n/p'
    bySector[key] = (bySector[key] || 0) + r.value
  })
  const submit = (e) => {
    e.preventDefault()
    if (!t || !q || !c) return
    const tick = t.toUpperCase()
    if (!byTicker[tick]) return // ticker mora biti iz popisa praćenih dionica
    onAdd({ ticker: tick, quantity: parseFloat(q), avg_price: parseFloat(c) })
    setT(''); setQ(''); setC('')
  }
  return (
    <>
      <div className="pf-head">
        {demo
          ? <span className="flag">DEMO PRIKAZ — lokalno, bez prijave i bez spremanja</span>
          : <span className="pf-user">prijavljen: <b>{email}</b>{' '}
            <button className="pf-logout" onClick={onSettings}>postavke računa</button>{' '}
            <button className="pf-logout" onClick={onLogout}>odjava</button></span>}
      </div>
      <form className="pf-add" onSubmit={submit}>
        <input list="pf-tickers" placeholder="ticker" value={t}
          onChange={(e) => setT(e.target.value)} style={{ width: 110 }} />
        <datalist id="pf-tickers">
          {(ov?.stocks || []).map((s) => (
            <option key={s.ticker} value={s.ticker}>{s.name}</option>))}
        </datalist>
        <input type="number" step="any" min="0" placeholder="količina" value={q}
          onChange={(e) => setQ(e.target.value)} style={{ width: 110 }} />
        <input type="number" step="any" min="0" placeholder="pros. cijena €" value={c}
          onChange={(e) => setC(e.target.value)} style={{ width: 130 }} />
        <button>Dodaj poziciju</button>
      </form>
      <table>
        <thead><tr><th>Pozicija</th><th className="num">Kol.</th>
          <th className="num">Pros. cijena</th><th className="num">Zadnja</th>
          <th className="num">Vrijednost €</th><th className="num">D/G €</th><th /></tr></thead>
        <tbody>
          {enriched.map((r) => (
            <tr key={r.id}>
              <td>
                <a href={`/dionica/${String(r.s?.company || r.ticker).toLowerCase()}`}><b>{r.ticker}</b></a>{' '}
                <span className="fund-src">{r.s?.name || 'nije u sustavu'}</span>
                {r.illiquid && <span className="flag" style={{ marginLeft: 6 }}
                  title="slabo likvidna dionica — zadnja cijena može biti stara">indikativna vrijednost</span>}
              </td>
              <td className="num">{num(r.quantity, 0)}</td>
              <td className="num">{num(r.avg_price, 2)}</td>
              <td className="num">{r.price === null ? dash : num(r.price, 2)}</td>
              <td className="num">{r.value === null ? dash : num(r.value, 0)}</td>
              <td className="num" style={{ color: r.pl > 0 ? '#1F6E5A' : r.pl < 0 ? '#9E2B25' : undefined }}>
                {r.pl === null ? dash : (r.pl > 0 ? '+' : '') + num(r.pl, 0)}
              </td>
              <td><button className="pf-del" onClick={() => onDelete(r.id)}>ukloni</button></td>
            </tr>
          ))}
          {!enriched.length && (
            <tr><td colSpan={7} className="subnote">nema pozicija — dodaj prvu iznad</td></tr>)}
        </tbody>
      </table>
      <div className="pf-total">
        UKUPNO: <b>{num(total, 0)} €</b>
        {totalCost > 0 && total > 0 && (
          <span> · dobit/gubitak {total - totalCost > 0 ? '+' : ''}{num(total - totalCost, 0)} €
            ({pct((total - totalCost) / totalCost, 1)})</span>
        )}
      </div>
      {Object.keys(bySector).length > 0 && (
        <div className="pf-alloc">
          <div className="sec-label">Alokacija po sektoru</div>
          {Object.entries(bySector).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
            <div className="pf-alloc-row" key={k}>
              <span className="pf-alloc-name">{k}</span>
              <span className="pf-alloc-bar"><i style={{ width: `${(v / total) * 100}%` }} /></span>
              <span className="pf-alloc-pct">{pct(v / total, 1)}</span>
            </div>
          ))}
        </div>
      )}
      <p className="subnote">
        Vrijednosti su informativni izračun iz zadnjih službenih EOD cijena (ZSE);
        pozicije s oznakom "indikativna vrijednost" imaju slabu likvidnost pa je
        zadnja cijena moguće stara. Svaka pozicija linka na našu analizu.
        Ovo nije investicijski savjet ni preporuka.
      </p>
    </>
  )
}

export default function Portfelj() {
  const ov = useOverview()
  const [session, setSession] = useState(null)
  const [recovery, setRecovery] = useState(false)
  const [profile, setProfile] = useState(undefined) // undefined = učitava se
  const [portfolioId, setPortfolioId] = useState(null)
  const [rows, setRows] = useState([])
  const [demo, setDemo] = useState(DEMO)
  const [settings, setSettings] = useState(false)
  const [err, setErr] = useState(null)

  useEffect(() => {
    document.title = 'Portfelj · Burzovni list'
    // auth/portfelj rute se ne indeksiraju (SEO higijena)
    const m = document.createElement('meta')
    m.name = 'robots'; m.content = 'noindex'
    document.head.appendChild(m)
    return () => { document.head.removeChild(m) }
  }, [])

  useEffect(() => {
    if (!supabase) return undefined
    supabase.auth.getSession().then(({ data }) => setSession(data.session))
    const { data: sub } = supabase.auth.onAuthStateChange((event, s) => {
      setSession(s)
      if (event === 'PASSWORD_RECOVERY') setRecovery(true)
      if (event === 'SIGNED_OUT') { setProfile(undefined); setPortfolioId(null); setRows([]) }
    })
    return () => sub.subscription.unsubscribe()
  }, [])

  // profil (terms gate) — bez prihvata uvjeta NIŠTA dalje
  const loadProfile = useCallback(async () => {
    const { data, error } = await supabase.from('profiles')
      .select('id, display_name, terms_accepted_at, terms_version, created_at')
      .maybeSingle()
    if (error) { setErr(error.message); return }
    setErr(null); setProfile(data)
  }, [])
  useEffect(() => { if (session && !demo) loadProfile() }, [session, demo, loadProfile])

  // portfelj: default portfelj (kreira se ako ne postoji) + pozicije
  const load = useCallback(async () => {
    const pf = await supabase.from('portfolios').select('id').order('created_at').limit(1)
    if (pf.error) { setErr(pf.error.message); return }
    let pid = pf.data?.[0]?.id
    if (!pid) {
      const ins = await supabase.from('portfolios')
        .insert({ name: 'Moj portfelj' }).select('id').single()
      if (ins.error) { setErr(ins.error.message); return }
      pid = ins.data.id
    }
    setPortfolioId(pid)
    const { data, error } = await supabase.from('portfolio_positions')
      .select('id, ticker, quantity, avg_price').eq('portfolio_id', pid).order('created_at')
    if (error) setErr(error.message); else { setErr(null); setRows(data || []) }
  }, [])
  useEffect(() => {
    if (session && !demo && profile?.terms_accepted_at) load()
  }, [session, demo, profile, load])

  const add = async (p) => {
    if (demo) { setRows((r) => [...r, { ...p, id: Date.now() }]); return }
    const first = rows.length === 0
    const { error } = await supabase.from('portfolio_positions')
      .insert({ ...p, portfolio_id: portfolioId })
    if (error) setErr(error.message)
    else {
      if (first) pushEvent('portfolio_created') // prva pozicija = kreiran portfelj
      load()
    }
  }
  const del = async (id) => {
    if (demo) { setRows((r) => r.filter((x) => x.id !== id)); return }
    const { error } = await supabase.from('portfolio_positions').delete().eq('id', id)
    if (error) setErr(error.message); else load()
  }

  let body
  if (demo) {
    body = <PositionsView rows={rows} ov={ov} onAdd={add} onDelete={del} demo />
  } else if (!supabase) {
    body = (
      <div className="prof-unavail" style={{ padding: 32 }}>
        <div className="prof-klabel">PRIJAVA JOŠ NIJE AKTIVNA</div>
        <p style={{ maxWidth: 560 }}>
          Portfelj traži Supabase ključeve (VITE_SUPABASE_URL i
          VITE_SUPABASE_ANON_KEY u okruženju builda). Upute za postavljanje:
          docs/supabase_setup.md.
        </p>
        <button className="auth-submit" onClick={() => setDemo(true)}
          style={{ marginTop: 12 }}>demo prikaz (lokalno, bez spremanja)</button>
      </div>
    )
  } else if (recovery) {
    body = <NewPasswordForm />
  } else if (!session) {
    body = <AuthForms onDemo={() => setDemo(true)} />
  } else if (profile === undefined) {
    body = <div className="loading">učitavam račun…</div>
  } else if (!profile?.terms_accepted_at) {
    // M26 1.2: blokirajući ekran — OAuth korisnik bez zapisa prihvata ne može
    // ni do portfelja ni do postavki
    body = <TermsGate onAccepted={loadProfile} />
  } else if (settings) {
    body = <AccountSettings session={session} profile={profile}
      onClose={() => setSettings(false)} />
  } else {
    body = (
      <PositionsView rows={rows} ov={ov} onAdd={add} onDelete={del}
        email={session.user.email}
        onSettings={() => setSettings(true)}
        onLogout={() => supabase.auth.signOut()} />
    )
  }

  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        <div className="mk-title"><h1>Moj portfelj</h1></div>
        {err && <div className="auth-msg err">{err}</div>}
        {body}
      </main>
      <SiteFooter />
    </div>
  )
}
