import React, { useEffect, useMemo, useState } from 'react'
import { SiteFooter, SiteHeader, useOverview } from './Shell.jsx'
import { dash, num, pct } from './format.js'
import { DEMO, supabase } from './supabase.js'
import { pushEvent } from './consent.jsx'

/* Faza 3 (M9): portfelj iza prijave — Supabase Auth (email+password).
   Lozinke NIKAD ne prolaze kroz naš kod: sve forme zovu Supabase SDK.
   Pozicije žive u Supabase Postgresu s RLS-om (user vidi samo svoje).
   MAR: vrijednost i kontekst, bez preporuka. */

const EMAIL_NOTE = 'Email koristimo isključivo za prijavu i oporavak lozinke — bez newslettera i marketinga.'

function AuthForms({ onDemo }) {
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
    if (!error && gtmEvent) pushEvent(gtmEvent) // GTM konverzijski event
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
          // timestamp prihvata uvjeta uz korisnika (user_metadata)
          data: {
            terms_accepted_at: new Date().toISOString(),
            terms_version: '15.07.2026.',
          },
        },
      }), 'Registracija zaprimljena — provjeri email i potvrdi adresu, pa se prijavi.',
      'sign_up')
    } else if (mode === 'login') {
      run(() => supabase.auth.signInWithPassword({ email, password: pass }),
        'Prijavljen.', 'login')
    } else {
      run(() => supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/portfelj`,
      }), 'Ako račun postoji, poslan je email s poveznicom za novu lozinku.')
    }
  }
  return (
    <div className="auth-box">
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

function PositionsView({ rows, ov, onAdd, onDelete, demo, email, onLogout }) {
  const [t, setT] = useState(''); const [q, setQ] = useState(''); const [c, setC] = useState('')
  const byTicker = useMemo(
    () => Object.fromEntries((ov?.stocks || []).map((s) => [s.ticker, s])), [ov])
  const enriched = rows.map((r) => {
    const s = byTicker[r.ticker.toUpperCase()]
    const price = s?.price ?? null
    const value = price !== null ? price * r.qty : null
    const cost = r.avg_cost * r.qty
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
    onAdd({ ticker: t.toUpperCase(), qty: parseFloat(q), avg_cost: parseFloat(c) })
    setT(''); setQ(''); setC('')
  }
  return (
    <>
      <div className="pf-head">
        {demo
          ? <span className="flag">DEMO PRIKAZ — lokalno, bez prijave i bez spremanja</span>
          : <span className="pf-user">prijavljen: <b>{email}</b>{' '}
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
              <td className="num">{num(r.qty, 0)}</td>
              <td className="num">{num(r.avg_cost, 2)}</td>
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
  const [rows, setRows] = useState([])
  const [demo, setDemo] = useState(DEMO)
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
    })
    return () => sub.subscription.unsubscribe()
  }, [])

  const load = async () => {
    // user_id NE šaljemo i NE filtriramo klijentski: RLS na positions
    // pušta isključivo retke s auth.uid() iz verificiranog JWT-a
    const { data, error } = await supabase.from('positions')
      .select('id,ticker,qty,avg_cost').order('created_at')
    if (error) setErr(error.message); else { setErr(null); setRows(data || []) }
  }
  useEffect(() => { if (session && !demo) load() }, [session, demo]) // eslint-disable-line

  const add = async (p) => {
    if (demo) { setRows((r) => [...r, { ...p, id: Date.now() }]); return }
    const first = rows.length === 0
    const { error } = await supabase.from('positions').insert(p) // user_id = default auth.uid()
    if (error) setErr(error.message)
    else {
      if (first) pushEvent('portfolio_created') // prva pozicija = kreiran portfelj
      load()
    }
  }
  const del = async (id) => {
    if (demo) { setRows((r) => r.filter((x) => x.id !== id)); return }
    const { error } = await supabase.from('positions').delete().eq('id', id)
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
  } else {
    body = (
      <PositionsView rows={rows} ov={ov} onAdd={add} onDelete={del}
        email={session.user.email}
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
