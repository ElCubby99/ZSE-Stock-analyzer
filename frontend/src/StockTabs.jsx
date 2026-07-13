import React from 'react'
import { Term } from './Legend.jsx'
import { GapCell, SECTOR_HR, useOverview } from './Shell.jsx'
import { dash, num, pct } from './format.js'

/* Tab-struktura stranice dionice (dizajn 4). Sve iz postojećih podataka;
   BEZ 'tehničke analize' i BEZ ratinga/ocjena (MAR). */

export const TABS = [
  ['pregled', 'PREGLED'],
  ['analiza', 'ANALIZA VRIJEDNOSTI'],
  ['pokazatelji', 'KLJUČNI POKAZATELJI'],
  ['usporedba', 'USPOREDBA'],
  ['izvjestaji', 'IZVJEŠTAJI'],
  ['dionicari', 'DIONIČARI'],
  ['novosti', 'NOVOSTI'],
]

export function TabBar({ tab, setTab }) {
  return (
    <div className="stab">
      {TABS.map(([k, l]) => (
        <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>
      ))}
    </div>
  )
}

/* Ključni pokazatelji: tržišni omjeri + POLOŽAJ NASPRAM FER-ZONE (fer P/E =
   sredina sidrene zone / EPS; fer P/B analogno) — činjenica, ne ocjena. */
export function KeyIndicators({ data }) {
  const rec = data.valuation?.reconciliation
  const m = data.metrics || {}
  const zoneMid = rec && rec.zone_low !== null ? (rec.zone_low + rec.zone_high) / 2 : null
  const ferPe = zoneMid && m.eps > 0 ? zoneMid / m.eps : null
  const ferPb = zoneMid && m.bvps > 0 ? zoneMid / m.bvps : null
  const rows = (m.per_class || []).map((c) => ({
    t: c.class_ticker, price: c.price, pe: c.pe, pb: c.pb, dy: c.div_yield,
  }))
  return (
    <section>
      <div className="sec-label">Omjeri po klasi — tržišni vs fer-zona</div>
      <table>
        <thead><tr><th>Klasa</th><th className="num">Cijena €</th>
          <th className="num"><Term t="P/E">P/E</Term></th>
          <th className="num"><Term t="P/E">fer P/E*</Term></th>
          <th className="num"><Term t="P/B">P/B</Term></th>
          <th className="num"><Term t="P/B">fer P/B*</Term></th>
          <th className="num">Div. prinos</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.t}>
              <td><b>{r.t}</b></td>
              <td className="num">{r.price === null ? dash : num(r.price, 2)}</td>
              <td className="num">{r.pe === null ? dash : num(r.pe, 1)}</td>
              <td className="num pine-t">{ferPe === null ? dash : num(ferPe, 1)}</td>
              <td className="num">{r.pb === null ? dash : num(r.pb, 2)}</td>
              <td className="num pine-t">{ferPb === null ? dash : num(ferPb, 2)}</td>
              <td className="num">{r.dy ? pct(r.dy, 2) : dash}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="subnote">
        * fer P/E i fer P/B = sredina sidrene fer-zone ({rec && rec.zone_low !== null
          ? `${num(rec.zone_low, 0)}–${num(rec.zone_high, 0)} €` : dash}) podijeljena
        EPS-om odn. knjigom po dionici — pokazuje koliko bi omjer iznosio na razini naše
        procjene; usporedba s tržišnim omjerom je činjenica, ne ocjena.
      </div>
    </section>
  )
}

/* Usporedba: dionica vs klase ISTOG sektora (overview.json — stvarni podaci);
   valuacijski peer skup (docs/peers.md) citiran iz params.sources. */
export function Comparison({ data }) {
  const ov = useOverview()
  if (!ov) return <div className="loading">učitavam…</div>
  const mine = new Set((data.share_classes || []).map((c) => c.ticker))
  const rows = ov.stocks.filter((s) => s.sector === data.sector)
  const peerSrc = data.valuation?.params?.sources?.peers
  return (
    <section>
      <div className="sec-label">
        Usporedba — sektor: {SECTOR_HR[data.sector] || data.sector || dash}
      </div>
      {rows.length <= mine.size ? (
        <div className="subnote"><span className="np">n/p</span> — u sustavu trenutačno
          nema drugih praćenih firmi istog sektora; usporedba po sektoru nije moguća
          bez izmišljanja (vidi peer napomenu ispod).</div>
      ) : (
        <div className="mk-scroll">
          <table>
            <thead><tr><th>Dionica</th><th className="num">Cijena €</th><th className="num">P/E</th>
              <th className="num">P/B</th><th className="num">Prinos</th><th>Raskorak</th></tr></thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.ticker} className={mine.has(s.ticker) ? 'cmp-self' : ''}>
                  <td><b>{s.ticker}</b> <span className="fund-src">{s.name}</span>
                    {mine.has(s.ticker) && <span className="okflag" style={{ marginLeft: 6 }}>ova dionica</span>}</td>
                  <td className="num">{s.price === null ? dash : num(s.price, 2)}</td>
                  <td className="num">{s.pe === null || s.pe === undefined ? dash : num(s.pe, 1)}</td>
                  <td className="num">{s.pb === null || s.pb === undefined ? dash : num(s.pb, 2)}</td>
                  <td className="num">{s.div_yield ? pct(s.div_yield, 1) : dash}</td>
                  <td><GapCell s={s} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="subnote">
        Usporedba po sektorskoj oznaci nad praćenim firmama (isti izvor kao Screener).
        {peerSrc ? <> Valuacijski peer skup ove firme: {peerSrc}</> : null}
      </div>
    </section>
  )
}

export function NewsTab({ news }) {
  const items = news?.items || []
  return (
    <section>
      <div className="sec-label">Novosti — službene objave izdavatelja (EHO)</div>
      {!items.length ? (
        <div className="subnote"><span className="flag">nema u bazi</span>{' '}
          nema uvezenih objava za ovu firmu.</div>
      ) : (
        <div className="news-list">
          {items.map((n, i) => (
            <a key={i} className="news-row" href={n.url} target="_blank" rel="noreferrer">
              <span className="news-date">{n.date || dash}</span>
              <span className="news-title">{n.title}</span>
            </a>
          ))}
        </div>
      )}
      <div className="subnote">{news?.note}.</div>
    </section>
  )
}
