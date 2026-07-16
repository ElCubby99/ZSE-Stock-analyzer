import React, { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { IndexChart } from './Indeksi.jsx'
import { num } from './format.js'

/* M-BOND: /obveznice (sve uvrštene: državne/municipalne/korporativne;
   sort/filter) i /obveznica/<oznaka> (detalji + graf cijene + raspored
   kupona). Cijene su ČISTE, u % nominale (jasno označeno). Deterministička
   analiza prinosa (YTM/duracija/obračunata kamata — formule na
   /metodologija); bez fer-zone i bez preporuka. */

export function useObveznice() {
  const [d, setD] = useState(null)
  useEffect(() => {
    fetch('/data/obveznice.json').then((r) => r.json()).then(setD)
      .catch(() => setD({ rows: [], as_of: null }))
  }, [])
  return d
}

const fmtHr = (iso) => {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  return `${Number(d)}.${Number(m)}.${y}.`
}
const pct = (v, d = 2) => (v === null || v === undefined ? 'n/p' : `${num(v, d)} %`)

const TYPES = ['sve', 'državna', 'korporativna', 'municipalna']

const COLS = [
  ['symbol', 'OZNAKA', 'l'], ['issuer', 'IZDAVATELJ', 'l'], ['btype', 'TIP', 'l'],
  ['maturity_date', 'DOSPIJEĆE', 'l'], ['coupon_pct', 'KUPON', 'r'],
  ['price_pct', 'CIJENA (% NOM.)', 'r'], ['ytm_pct', 'YTM', 'r'],
  ['duration', 'MOD. DURACIJA', 'r'],
]

export function ObvezniceIndex() {
  const d = useObveznice()
  const [tip, setTip] = useState('sve')
  const [sk, setSk] = useState('maturity_date')
  const [dir, setDir] = useState(1)
  useEffect(() => {
    document.title = 'Obveznice na Zagrebačkoj burzi — prinosi (YTM) i dospijeća · Burzovni list'
  }, [])
  const rows = useMemo(() => {
    const list = (d?.rows || []).filter((r) => tip === 'sve' || r.btype === tip)
    const val = (r) => (sk === 'duration' ? r.duration?.modified : r[sk])
    return [...list].sort((a, b) => {
      const av = val(a); const bv = val(b)
      if (typeof av === 'string' || typeof bv === 'string') {
        return String(av ?? '').localeCompare(String(bv ?? '')) * dir
      }
      const an = av === null || av === undefined ? Infinity * dir : av
      const bn = bv === null || bv === undefined ? Infinity * dir : bv
      return (an - bn) * dir
    })
  }, [d, tip, sk, dir])
  const sort = (k) => () => { setDir(sk === k ? -dir : 1); setSk(k) }
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        <div className="mk-title"><h1>Obveznice na Zagrebačkoj burzi — prinosi i dospijeća</h1>
          <span>državne (uklj. narodne obveznice), municipalne i korporativne ·
            čiste cijene u % nominale{d?.as_of ? ` · zadnje trgovanje ${fmtHr(d.as_of)}` : ''}</span></div>
        <div className="prof-chips" style={{ margin: '10px 0' }}>
          {TYPES.map((t) => (
            <button key={t} className={`prof-chip ${tip === t ? 'on' : ''}`}
              onClick={() => setTip(t)}>{t.toUpperCase()}</button>
          ))}
        </div>
        {!d ? <div className="loading">učitavam…</div> : (
          <div className="mk-scroll">
            <table>
              <thead><tr>{COLS.map(([k, l, ta]) => (
                <th key={k} className={ta === 'r' ? 'num' : ''}>
                  <button className="th-sort" onClick={sort(k)}>{l}{sk === k ? (dir === 1 ? ' ↑' : ' ↓') : ''}</button>
                </th>))}</tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.symbol}>
                    <td><Link to={`/obveznica/${r.symbol.toLowerCase()}`}><b>{r.symbol}</b></Link>
                      {r.stale && <i className="mk-ill" title="cijena starija od zadnjeg tržišnog dana — indikativna"> ILIKV.</i>}</td>
                    <td>{r.issuer || <span className="flag">master data u obradi</span>}</td>
                    <td className="basis">{r.btype}</td>
                    <td className="mono">{fmtHr(r.maturity_date)}</td>
                    <td className="num">{pct(r.coupon_pct, 3)}</td>
                    <td className="num">{r.price_pct !== null && r.price_pct !== undefined
                      ? `${num(r.price_pct, 2)}` : 'n/p'}
                      {r.price_date && <div className="fund-src">{fmtHr(r.price_date)}</div>}</td>
                    <td className="num">{pct(r.ytm_pct)}</td>
                    <td className="num">{r.duration ? num(r.duration.modified, 2) : 'n/p'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="disc" style={{ marginTop: 24 }}>
          Obveznicama se na ZSE trguje rijetko — cijene su često stare i
          indikativne (ILIKV. oznaka). Izračuni prinosa su deterministički iz
          čiste cijene, kupona i dospijeća (formule na{' '}
          <Link to="/metodologija">Metodologiji</Link>); frekvencija kupona i
          konvencija dana nose oznaku pretpostavke dok ih prospekt ne potvrdi.
          Informativno — nije investicijski savjet ni preporuka.
        </div>
      </main>
      <SiteFooter />
    </div>
  )
}

export function ObveznicaDetail() {
  const { symbol } = useParams()
  const d = useObveznice()
  const r = d?.rows?.find((x) => x.symbol.toLowerCase() === symbol)
  useEffect(() => {
    if (r) document.title = `${r.symbol} obveznica — prinos (YTM), kupon i dospijeće · Burzovni list`
  }, [r])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        {!d ? <div className="loading">učitavam…</div>
          : !r ? (
            <section><div className="mk-title"><h1>Obveznica nije pronađena</h1></div>
              <p className="imp-p"><Link to="/obveznice">← sve obveznice</Link></p></section>
          ) : (
            <>
              <div className="mk-title">
                <h1>{r.symbol} — {r.issuer || 'izdavatelj u obradi'} ({r.btype} obveznica)</h1>
                <span>{r.series_name || r.isin} · dospijeće {fmtHr(r.maturity_date)}
                  {r.stale ? ' · cijena indikativna (ILIKV.)' : ''}</span>
              </div>
              <div className="kv" style={{ marginBottom: 16 }}>
                <div className="cell"><div className="k">ČISTA CIJENA (% NOM.)</div>
                  <div className="v">{r.price_pct !== null && r.price_pct !== undefined ? num(r.price_pct, 2) : 'n/p'}</div>
                  <div className="n">{r.price_date ? `EOD ${fmtHr(r.price_date)}` : 'nema trgovanja'}</div></div>
                <div className="cell"><div className="k">KUPON</div>
                  <div className="v">{pct(r.coupon_pct, 3)}</div>
                  <div className="n">godišnje{r.freq_assumed ? ' · pretpostavka' : ''}</div></div>
                <div className="cell"><div className="k">YTM</div>
                  <div className="v">{pct(r.ytm_pct)}</div>
                  <div className="n">prinos do dospijeća</div></div>
                <div className="cell"><div className="k">TEKUĆI PRINOS</div>
                  <div className="v">{pct(r.current_yield_pct)}</div></div>
                <div className="cell"><div className="k">MOD. DURACIJA</div>
                  <div className="v">{r.duration ? num(r.duration.modified, 2) : 'n/p'}</div>
                  <div className="n">{r.duration ? `Macaulay ${num(r.duration.macaulay, 2)} g` : ''}</div></div>
                <div className="cell"><div className="k">OBRAČUNATA KAMATA</div>
                  <div className="v">{r.accrued_pct !== null && r.accrued_pct !== undefined ? num(r.accrued_pct, 3) : 'n/p'}</div>
                  <div className="n">% nominale · {r.day_count}{r.day_count_assumed ? ' · pretpostavka' : ''}</div></div>
              </div>
              {r.series?.length > 1 && (
                <IndexChart series={r.series.map((p) => ({ date: p.date, value: p.price_pct }))}
                  label={`${r.symbol} · ČISTA CIJENA (% NOMINALE)`} />
              )}
              {r.schedule?.length > 0 && (
                <section style={{ marginTop: 24 }}>
                  <div className="sec-label">Raspored budućih isplata (na 100 nominale)</div>
                  <table>
                    <thead><tr><th>Datum</th><th className="num">Iznos (% nominale)</th><th>Vrsta</th></tr></thead>
                    <tbody>
                      {r.schedule.map((c) => (
                        <tr key={c.date}>
                          <td className="mono">{fmtHr(c.date)}</td>
                          <td className="num">{num(c.amount_pct, 3)}</td>
                          <td className="basis">{c.amount_pct > 90 ? 'kupon + glavnica' : 'kupon'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="fund-src">Raspored izveden iz kupona i dospijeća
                  ({r.freq_assumed ? 'godišnja frekvencija — pretpostavka; ' : ''}izvor
                  master podataka: ZSE tečajnica uvrštenja).</p>
                </section>
              )}
              <div className="disc" style={{ marginTop: 24 }}>
                Deterministički izračuni iz javnih ulaza — formule na{' '}
                <Link to="/metodologija">Metodologiji</Link>. Informativno —
                nije investicijski savjet ni preporuka.
              </div>
            </>
          )}
      </main>
      <SiteFooter />
    </div>
  )
}
