import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { num } from './format.js'

/* M-FOND: /mirovinski-fondovi — vrijednosti obračunskih jedinica OMF-ova
   (A/B/C) i Mirex (izvor HANFA, MJESEČNI ritam) + sinergija s našim
   podacima: ZSE dionice u čijim se top-10 popisima pojavljuju OMF-ovi.
   BEZ rangiranja fondova (abecedni redoslijed) — činjenični prikaz. */

export function useFondovi() {
  const [d, setD] = useState(null)
  useEffect(() => {
    fetch('/data/fondovi.json').then((r) => r.json()).then(setD)
      .catch(() => setD({ units: [], mirex: [], synergy: [], units_available: false }))
  }, [])
  return d
}

const pct = (v) => (v === null || v === undefined ? 'n/p'
  : `${v >= 0 ? '+' : '−'}${num(Math.abs(v) * 100, 2)} %`)
const fmtHr = (iso) => {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  return `${Number(d)}.${Number(m)}.${y}.`
}

export default function MirovinskiFondovi() {
  const d = useFondovi()
  useEffect(() => {
    document.title = 'Mirovinski fondovi (OMF) — jedinice i prinosi · Burzovni list'
  }, [])
  const byTicker = useMemo(() => {
    const m = new Map()
    for (const s of d?.synergy || []) {
      if (!m.has(s.ticker)) m.set(s.ticker, { name: s.company_name, as_of: s.as_of, funds: [] })
      m.get(s.ticker).funds.push(s)
    }
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  }, [d])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        <div className="mk-title"><h1>Mirovinski fondovi (OMF) — obračunske jedinice i prinosi</h1>
          <span>izvor: HANFA javne objave · mjesečni ritam · bez rangiranja (abecedno)</span></div>
        {!d ? <div className="loading">učitavam…</div> : (
          <>
            {['A', 'B', 'C'].map((cat) => (
              <section key={cat} style={{ marginTop: 14 }}>
                <div className="sec-label">Kategorija {cat}</div>
                <table>
                  <thead><tr><th>Fond</th><th className="num">Jedinica</th>
                    <th className="num">YTD</th><th className="num">1g</th>
                    <th className="num">3g</th><th className="num">5g</th><th>Datum</th></tr></thead>
                  <tbody>
                    {d.units.filter((u) => u.category === cat).map((u) => (
                      <tr key={u.fund}>
                        <td>{u.fund} OMF — kategorija {cat}</td>
                        <td className="num">{u.unit_value !== null && u.unit_value !== undefined
                          ? num(u.unit_value, 4) : <span className="np">čeka uvoz</span>}</td>
                        <td className="num">{pct(u.ytd)}</td>
                        <td className="num">{pct(u.y1)}</td>
                        <td className="num">{pct(u.y3)}</td>
                        <td className="num">{pct(u.y5)}</td>
                        <td className="fund-src">{fmtHr(u.value_date)}</td>
                      </tr>
                    ))}
                    {(() => {
                      const mx = d.mirex.find((m) => m.category === cat)
                      return (
                        <tr className="sotp-total" key="mirex">
                          <td>Mirex {cat} (usporedba)</td>
                          <td className="num">{mx?.value !== null && mx?.value !== undefined
                            ? num(mx.value, 4) : <span className="np">čeka uvoz</span>}</td>
                          <td className="num">{pct(mx?.ytd)}</td>
                          <td className="num" colSpan={3} />
                          <td className="fund-src">{fmtHr(mx?.value_date)}</td>
                        </tr>
                      )
                    })()}
                  </tbody>
                </table>
              </section>
            ))}
            {!d.units_available && (
              <div className="subnote" style={{ marginTop: 8 }}>
                Prvi mjesečni uvoz HANFA podataka još nije obavljen — vrijednosti
                jedinica i prinosi pojavit će se nakon prve objave koju sustav povuče.
              </div>
            )}
            <section style={{ marginTop: 22 }}>
              <div className="sec-label">ZSE dionice s OMF-ovima među top 10 dioničara
                {byTicker[0]?.[1]?.as_of ? ` · snapshot ${fmtHr(byTicker[0][1].as_of)}` : ''}</div>
              {byTicker.length ? (
                <table>
                  <thead><tr><th>Dionica</th><th>Fond (kategorija)</th>
                    <th className="num">Udjel</th></tr></thead>
                  <tbody>
                    {byTicker.map(([ticker, info]) => (
                      <tr key={ticker}>
                        <td><Link to={`/dionica/${ticker.toLowerCase()}`}><b>{ticker}</b></Link>{' '}
                          <span className="basis">{info.name}</span></td>
                        <td>{info.funds.map((f) => `${f.fund} (${f.category})`).join(', ')}</td>
                        <td className="num">{num(info.funds.reduce((a, f) => a + (f.pct || 0), 0), 2)} %</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : <div className="subnote">nema OMF pozicija u dostupnim top-10 popisima</div>}
              <p className="fund-src">Iz naših podataka o top 10 dioničara (ZSE/SKDD
              snapshoti); pravila prepoznavanja OMF računa dokumentirana su u
              izvorima podataka. Zbroj = ukupni udjel svih OMF kategorija u firmi.</p>
            </section>
            <div className="disc" style={{ marginTop: 24 }}>
              Podaci o jedinicama dolaze iz HANFA javnih objava u mjesečnom
              ritmu; prinosi su izračunati iz povijesti jedinica. Bez
              rangiranja i bez preporuka — činjenični prikaz. Nije
              investicijski savjet.
            </div>
          </>
        )}
      </main>
      <SiteFooter />
    </div>
  )
}

/* Sekcija za stranicu dionice: OMF-ovi među top 10 te firme. */
export function OmfHolders({ ticker }) {
  const d = useFondovi()
  const rows = (d?.synergy || []).filter((s) => s.ticker === ticker)
  if (!rows.length) return null
  return (
    <section>
      <div className="sec-label">Mirovinski fondovi među dioničarima
        {rows[0]?.as_of ? ` · snapshot ${fmtHr(rows[0].as_of)}` : ''}</div>
      <table>
        <thead><tr><th>Fond</th><th className="num">Udjel</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.holder_name}>
              <td>{r.fund} OMF — kategorija {r.category}
                <div className="fund-src">{r.holder_name}</div></td>
              <td className="num">{num(r.pct, 2)} %</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="fund-src">Iz top 10 dioničara (ZSE/SKDD); više na{' '}
        <Link to="/mirovinski-fondovi">stranici mirovinskih fondova</Link>.</p>
    </section>
  )
}
