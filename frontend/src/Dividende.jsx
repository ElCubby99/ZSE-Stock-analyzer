import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { num } from './format.js'

/* M22: agregirani dividendni kalendar (/dividende) — činjenični pregled svih
   isplata i najava iz EHO objava. MAR: bez rankinga "najboljih" prinosa —
   sortiranje je korisnikov izbor; prijedlog je vidljivo označen kao
   neizglasan. Podaci: /data/dividende.json (build_dividende.py). */

const FILTERS = [
  ['sve', 'SVE'], ['paid', 'ISPLAĆENO'], ['upcoming', 'NADOLAZEĆE'],
  ['proposed', 'PRIJEDLOZI'],
]

const COLS = [
  ['company', 'DIONICA', 'l'], ['amount_eur', 'IZNOS €', 'r'],
  ['yield_now', 'PRINOS', 'r'], ['payout_ratio', '% DOBITI', 'r'],
  ['continuity', 'KONTINUITET', 'r'],
  ['ex_date', 'EX-DATUM', 'r'], ['payment_date', 'ISPLATA', 'r'],
  ['status', 'STATUS', 'l'],
]

/* v3 DIV: filter po TIPU isplate (default: sve; jednokratne su vizualno
   označene badgeom u svakom retku) */
const TYPE_FILTERS = [
  ['sve', 'SVI TIPOVI'], ['redovna', 'REDOVNE'],
  ['jednokratna', 'JEDNOKRATNE'], ['iz_zadrzane_dobiti', 'IZ ZADRŽANE DOBITI'],
]

export function TypeBadge({ t }) {
  if (!t || t === 'redovna') {
    return t ? <span className="div-onoff reg">redovna</span> : null
  }
  return <span className="div-onoff">
    {t === 'iz_zadrzane_dobiti' ? 'iz zadržane dobiti' : 'izvanredna'}</span>
}

/* % dobiti pripadne fiskalne godine; >100% eksplicitno; bez dobiti u bazi
   '—' s objašnjenjem (NIKAD prema krivoj godini) */
export function PayoutCell({ r }) {
  if (r.payout_ratio === null || r.payout_ratio === undefined) {
    return <i className="np" title={`dobit FY${r.fiscal_year ?? '?'} nije dostupna u bazi`}>—</i>
  }
  if (r.payout_ratio > 1) {
    return <span title={r.classified_reason || ''}>&gt; 100% (iz zadržane dobiti)</span>
  }
  return <span title={r.classified_reason || ''}>{num(r.payout_ratio * 100, 0)} %</span>
}

function StatusBadge({ s }) {
  if (s === 'paid') return <span className="okflag">ISPLAĆENA</span>
  if (s === 'proposed') {
    return <span className="flag">PRIJEDLOG — još nije izglasano</span>
  }
  return <span className="div-upcoming">IZGLASANA · NADOLAZEĆA</span>
}

const fmtD = (d) => (d ? `${d.slice(8, 10)}.${d.slice(5, 7)}.${d.slice(0, 4)}.` : '—')

function Row({ r, nav, hist }) {
  const h = hist?.[r.company]
  return (
    <div className="mk-row div-row" onClick={() => nav(`/dionica/${String(r.company).toLowerCase()}`)}>
      <span className="mk-name"><b>{r.class_ticker}</b><em>{r.name}</em></span>
      <span className="r mono">{num(r.amount_eur, 2)}</span>
      <span className="r mono">{r.yield_now === null || r.yield_now === undefined
        ? <i className="np">n/p</i> : `${num(r.yield_now * 100, 2)} %`}</span>
      <span className="r mono" title={h ? `podaci od FY${h.coverage_from}; prosjek do 5 g.: ${num(h.avg_amount_5y, 2)} €` : undefined}>
        {h ? `${h.paid_years_of_5}/5` : '—'}</span>
      <span className="r mono"><PayoutCell r={r} /></span>
      <span className="r mono">{fmtD(r.ex_date)}</span>
      <span className="r mono dim">{fmtD(r.payment_date)}</span>
      <span>
        <StatusBadge s={r.status} />
        {' '}
        <TypeBadge t={r.payout_type} />
        {' '}
        <a className="fund-src" href={r.source_url} target="_blank" rel="noreferrer"
          onClick={(e) => e.stopPropagation()}>izvor</a>
      </span>
    </div>
  )
}

export default function Dividende() {
  const nav = useNavigate()
  const [data, setData] = useState(null)
  const [filter, setFilter] = useState('sve')
  const [tfilter, setTfilter] = useState('sve')
  const [sk, setSk] = useState('ex_date'); const [dir, setDir] = useState(1)
  useEffect(() => {
    fetch('/data/dividende.json').then((r) => r.json()).then(setData).catch(() => setData({ rows: [] }))
    document.title = 'Dividende · Burzovni list'
  }, [])
  const today = new Date().toISOString().slice(0, 10)

  const rows = useMemo(() => {
    if (!data) return []
    let list = data.rows.filter((r) => filter === 'sve' || r.status === filter)
    list = list.filter((r) => tfilter === 'sve' || r.payout_type === tfilter)
    const val = (r) => r[sk]
    list = [...list].sort((a, b) => {
      if (sk === 'ex_date') {
        // kronološki: što dolazi sljedeće gore — budući ex-datumi uzlazno,
        // zatim prošli silazno (jučerašnja odmah ispod nadolazećih)
        const ka = a.ex_date || '9999'; const kb = b.ex_date || '9999'
        const fa = ka >= today; const fb = kb >= today
        if (fa !== fb) return (fa ? -1 : 1) * dir
        return (fa ? ka.localeCompare(kb) : kb.localeCompare(ka)) * dir
      }
      const av = val(a); const bv = val(b)
      if (typeof av === 'string' || typeof bv === 'string') {
        return String(av ?? '').localeCompare(String(bv ?? '')) * dir
      }
      const an = av === null || av === undefined ? -Infinity * dir : av
      const bn = bv === null || bv === undefined ? -Infinity * dir : bv
      return (bn - an) * dir
    })
    return list
  }, [data, filter, tfilter, sk, dir, today])

  const soon = useMemo(() => {
    if (!data) return []
    const lim = new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10)
    return data.rows.filter((r) => r.status !== 'paid' && r.ex_date
      && r.ex_date >= today && r.ex_date <= lim)
      .sort((a, b) => a.ex_date.localeCompare(b.ex_date))
  }, [data, today])

  const sort = (k) => () => { setDir(sk === k ? -dir : 1); setSk(k) }
  if (!data) return <div className="shellpg"><SiteHeader /><div className="loading">učitavam…</div></div>
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        <div className="mk-title">
          <h1>Dividendni kalendar</h1>
          <span>isplate i najave iz službenih EHO objava · stanje {fmtD(data.as_of)}</span>
        </div>

        {soon.length > 0 && (
          <section className="div-soon">
            <div className="sec-label">Ex-datum u sljedećih 30 dana</div>
            <div className="mk-scroll"><div className="div-table">
              <div className="mk-hd div-hd-static">
                <span>DIONICA</span><span className="r">IZNOS €</span><span className="r">PRINOS</span>
                <span className="r">EX-DATUM</span><span className="r">ISPLATA</span><span>STATUS</span>
              </div>
              {soon.map((r, i) => <Row r={r} nav={nav} hist={data.history} key={i} />)}
            </div></div>
            <div className="subnote">
              Tko drži dionicu na kraju dana prije ex-datuma ima pravo na isplatu;
              na sam ex-datum dionica se trguje bez tog prava. Prijedlog postaje
              isplata tek odlukom glavne skupštine.
            </div>
          </section>
        )}

        <div className="mk-title2">
          <h2 className="mk-h2">Sve isplate i najave ({new Date().getFullYear()}.)</h2>
          <div className="prof-chips">
            {FILTERS.map(([k, l]) => (
              <button key={k} className={`prof-chip ${filter === k ? 'on' : ''}`}
                onClick={() => setFilter(k)}>{l}</button>
            ))}
            <span className="dim">·</span>
            {TYPE_FILTERS.map(([k, l]) => (
              <button key={k} className={`prof-chip ${tfilter === k ? 'on' : ''}`}
                onClick={() => setTfilter(k)}>{l}</button>
            ))}
          </div>
        </div>
        <div className="mk-scroll">
          <div className="div-table">
            <div className="mk-hd">
              {COLS.map(([k, l, ta]) => (
                <button key={k} className={ta} onClick={sort(k)}>
                  {l}{sk === k ? (dir === 1 ? ' ↑' : ' ↓') : ''}
                </button>
              ))}
            </div>
            {rows.length ? rows.map((r, i) => <Row r={r} nav={nav} hist={data.history} key={i} />)
              : <div className="prof-empty-box">Nema zapisa za odabrani filter.</div>}
            <div className="mk-legend">
              <span>PRINOS = iznos / zadnja cijena te klase — informativan podatak, ne rang ni preporuka</span>
              <span>% DOBITI = ukupna isplata firme za tu fiskalnu godinu / neto dobit iste godine; — = dobit te godine nije u bazi</span>
              <span><b>redovna</b> = isplata u liniji s dosadašnjima · <b>izvanredna</b> = više od 150% medijana prethodnih redovnih · <b>iz zadržane dobiti</b> = ukupna isplata veća od dobiti godine iz koje se isplaćuje — činjenične oznake, ne ocjene</span>
              <span>— = datum nije objavljen · n/p = nema cijene</span>
            </div>
          </div>
        </div>
        <div className="disc">
          {data.note} Činjenični kalendar bez preporuka — visok prinos sam po
          sebi nije "dobra" dionica (može odražavati pad cijene ili jednokratnu
          isplatu); zaključak je čitateljev.
        </div>
      </main>
      <SiteFooter />
    </div>
  )
}
