import React, { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'

/* M37: tab FINANCIJE — as-reported financijski izvještaji po dionici.
   Podaci: /data/fin/<TICKER>.json (scripts/build_financije.py). Pravila:
   ništa se ne izvodi ni ne preuređuje (izvedene veličine ostaju na
   Ključnim pokazateljima); rupe su "—" (nikad 0); svaka kolona linka na
   izvorni filing; HRK periodi nose badge; restatement ćelije nose badge
   i stariju vrijednost iza klika. */

const BASIS_HR = { consolidated: 'konsolidirano', separate: 'nekonsolidirano' }
const SUBTABS = [
  ['income', 'Dobit i gubitak'],
  ['balance', 'Financijski položaj'],
  ['cashflow', 'Novčani tok'],
]

function fmtVal(v, unit) {
  if (v === null || v === undefined) return '—'
  const scaled = unit === 'mil' ? v / 1e6 : v / 1e3
  return scaled.toLocaleString('hr-HR', {
    minimumFractionDigits: unit === 'mil' ? 1 : 0,
    maximumFractionDigits: unit === 'mil' ? 1 : 0,
  })
}

function csvFor(view, st, unit, ticker) {
  const tbl = view.statements[st]
  if (!tbl) return ''
  const head = ['Stavka', ...view.periods.map((p) => `${p.label}${p.hrk ? ' (preračunato iz HRK)' : ''}`)]
  const unitNote = unit === 'mil' ? 'u milijunima EUR' : 'u tisućama EUR'
  const lines = [`# ${ticker} — ${tbl.label} (${unitNote}; as-reported, standardizirana shema ekstrakcije)`,
    head.join(';')]
  for (const r of tbl.rows) {
    lines.push([r.label, ...view.periods.map((p) => {
      const v = r.values[p.key]
      return v === null || v === undefined ? '—' : fmtVal(v, unit).replace(/ /g, '')
    })].join(';'))
  }
  return lines.join('\n')
}

function downloadCsv(view, st, unit, ticker) {
  const blob = new Blob(['﻿' + csvFor(view, st, unit, ticker)],
    { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${ticker}-${st}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}

function RestatePop({ meta, unit }) {
  return (
    <span className="fin-restate-pop">
      Ranija objava ({meta.prev_label}): <b>{fmtVal(meta.prev, unit)}</b>
      {meta.prev_url && <> · <a href={meta.prev_url} target="_blank"
        rel="noopener noreferrer">dokument</a></>}
    </span>
  )
}

function FinTable({ view, st, unit, ticker }) {
  const [openCell, setOpenCell] = useState(null)
  const tbl = view.statements[st]
  if (!tbl) return null
  return (
    <div className="mk-scroll">
      <table className="fin-table">
        <thead>
          <tr>
            <th className="fin-sticky">{tbl.label}
              <div className="fin-unit">{unit === 'mil' ? 'u milijunima EUR' : 'u tisućama EUR'}</div>
            </th>
            {view.periods.map((p) => (
              <th key={p.key} className="num">
                {p.url
                  ? <a href={p.url} target="_blank" rel="noopener noreferrer"
                      title={`Izvorni dokument${p.published ? ` (objava ${p.published})` : ''}`}>{p.label}</a>
                  : p.label}
                {p.hrk && <div className="fin-badge">preračunato iz HRK</div>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tbl.rows.map((r) => (
            <tr key={r.item} className={r.bold ? 'fin-bold' : ''}>
              <td className="fin-sticky" style={{ paddingLeft: 10 + r.indent * 16 }}>{r.label}</td>
              {view.periods.map((p) => {
                const meta = r.restated && r.restated[p.key]
                const cellKey = `${r.item}|${p.key}`
                return (
                  <td key={p.key} className="num">
                    {fmtVal(r.values[p.key], unit)}
                    {meta && (
                      <button type="button" className="fin-restate"
                        title="korigirano u kasnijem izvješću — klik za raniju vrijednost"
                        onClick={() => setOpenCell(openCell === cellKey ? null : cellKey)}>K</button>
                    )}
                    {meta && openCell === cellKey && <RestatePop meta={meta} unit={unit} />}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function FinancijePage() {
  const { ticker } = useParams()
  const T = String(ticker || '').toUpperCase()
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [st, setSt] = useState('income')
  const [kind, setKind] = useState('annual')
  const [basis, setBasis] = useState('consolidated')

  useEffect(() => {
    setData(null); setErr(null)
    fetch(`/data/fin/${T}.json`)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(setData)
      .catch((e) => setErr(e.message))
  }, [T])
  useEffect(() => {
    if (data) {
      document.title = `${data.ticker} financijski izvještaji — prihodi, dobit, bilanca | Burzovni list`
    }
  }, [data])

  const view = useMemo(() => {
    if (!data) return null
    const b = data.views[basis] ? basis : data.bases[0]
    return (data.views[b] && (data.views[b][kind] || data.views[b].annual)) || null
  }, [data, basis, kind])

  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        {err && (
          <section>
            <h1 className="page-h1">Financijski izvještaji — {T}</h1>
            <div className="prof-empty-box">Za ovu dionicu još nemamo
              ekstrahirane izvještaje u bazi. <Link to={`/dionica/${T.toLowerCase()}`}>Natrag na profil dionice</Link></div>
          </section>
        )}
        {!data && !err && <div className="loading">učitavam financije {T}…</div>}
        {data && (
          <>
            <nav className="fin-crumbs">
              <Link to={`/dionica/${T.toLowerCase()}`}>← {data.ticker} — profil dionice</Link>
              <span> · popis dokumenata: kartica IZVJEŠTAJI na profilu</span>
            </nav>
            <h1 className="page-h1">Financijski izvještaji — {data.name}</h1>

            <div className="fin-controls">
              <div className="fin-subtabs">
                {SUBTABS.map(([k, l]) => (
                  <button key={k} type="button" className={st === k ? 'on' : ''}
                    onClick={() => setSt(k)}>{l}</button>
                ))}
              </div>
              <div className="fin-right">
                <div className="fin-kind">
                  <button type="button" className={kind === 'annual' ? 'on' : ''}
                    onClick={() => setKind('annual')}>Godišnje</button>
                  <button type="button" className={kind === 'interim' ? 'on' : ''}
                    onClick={() => setKind('interim')}>Kvartalno</button>
                </div>
                {data.bases.length > 1 && (
                  <div className="fin-kind">
                    {data.bases.map((b) => (
                      <button key={b} type="button" className={basis === b ? 'on' : ''}
                        onClick={() => setBasis(b)}>{BASIS_HR[b] || b}</button>
                    ))}
                  </div>
                )}
                {view && view.statements[st] && (
                  <button type="button" className="fin-csv"
                    onClick={() => downloadCsv(view, st, data.unit, data.ticker)}>
                    Preuzmi CSV
                  </button>
                )}
              </div>
            </div>
            <div className="fin-activeview">
              Prikaz: {BASIS_HR[data.views[basis] ? basis : data.bases[0]]}
              {kind === 'interim' && ' · kumulativi od početka godine (kako su objavljeni)'}
            </div>

            {view && view.statements[st]
              ? <FinTable view={view} st={st} unit={data.unit} ticker={data.ticker} />
              : (
                <div className="prof-empty-box">
                  {SUBTABS.find(([k]) => k === st)?.[1]} za ovaj prikaz nije u bazi
                  {(data.missing.find((m) => m.statement === st) || {}).doc_url && (
                    <> — izvorni dokument: <a
                      href={data.missing.find((m) => m.statement === st).doc_url}
                      target="_blank" rel="noopener noreferrer">poveznica</a></>
                  )}.
                </div>
              )}

            {data.missing.length > 0 && view && view.statements[st] && (
              <div className="subnote" style={{ marginTop: 10 }}>
                Nije u bazi: {data.missing.map((m, i) => (
                  <span key={m.statement}>{i > 0 && ' · '}{m.label}
                    {m.doc_url && <> (<a href={m.doc_url} target="_blank"
                      rel="noopener noreferrer">izvorni dokument</a>)</>}</span>
                ))}
              </div>
            )}

            <div className="fin-note">
              <p>{data.note}</p>
              <p>Oznaka <b>K</b> uz vrijednost: korigirano u kasnijem izvješću —
              klik otvara raniju objavljenu vrijednost. Izvedene veličine (TTM,
              marže, po dionici) nalaze se na kartici Ključni pokazatelji na{' '}
              <Link to={`/dionica/${T.toLowerCase()}`}>profilu dionice</Link>.</p>
              <p className="disc">Prikazani podaci su informativni i analitički —
              ne predstavljaju investicijski savjet, preporuku ni poticaj na
              trgovanje. Zaključak je uvijek vaš.</p>
            </div>
          </>
        )}
      </main>
      <SiteFooter />
    </div>
  )
}
