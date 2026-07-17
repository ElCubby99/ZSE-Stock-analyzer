import React, { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { useLang } from './i18n/LangContext.jsx'
import { dash, num } from './format.js'

/* M37: tab FINANCIJE — as-reported financijski izvještaji po dionici.
   Podaci: /data/fin/<TICKER>.json (scripts/build_financije.py). Pravila:
   ništa se ne izvodi ni ne preuređuje (izvedene veličine ostaju na
   Ključnim pokazateljima); rupe su "—" (nikad 0); svaka kolona linka na
   izvorni filing; HRK periodi nose badge; restatement ćelije nose badge
   i stariju vrijednost iza klika. */

const SUBTAB_KEYS = [['income', 'fin.income'], ['balance', 'fin.balance'],
  ['cashflow', 'fin.cashflow']]

function fmtVal(v, unit) {
  if (v === null || v === undefined) return dash
  return num(unit === 'mil' ? v / 1e6 : v / 1e3, unit === 'mil' ? 1 : 0)
}

function csvFor(view, st, unit, ticker, t) {
  const tbl = view.statements[st]
  if (!tbl) return ''
  const head = [t('fin.item'), ...view.periods.map((p) => `${p.label}${p.hrk ? ` (${t('fin.hrkBadge')})` : ''}`)]
  const unitNote = unit === 'mil' ? t('fin.unitMillions') : t('fin.unitThousands')
  const lines = [`# ${ticker} — ${t(`fin.${st}`)} (${unitNote}; as-reported)`,
    head.join(';')]
  for (const r of tbl.rows) {
    lines.push([t(`li.${r.item}`), ...view.periods.map((p) => {
      const v = r.values[p.key]
      return v === null || v === undefined ? dash : fmtVal(v, unit).replace(/ /g, '')
    })].join(';'))
  }
  return lines.join('\n')
}

function downloadCsv(view, st, unit, ticker, t) {
  const blob = new Blob(['\ufeff' + csvFor(view, st, unit, ticker, t)],
    { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${ticker}-${st}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}

function RestatePop({ meta, unit, t }) {
  return (
    <span className="fin-restate-pop">
      {t('fin.earlierPublication')} ({t('fin.prevQ4')}): <b>{fmtVal(meta.prev, unit)}</b>
      {meta.prev_url && <> · <a href={meta.prev_url} target="_blank"
        rel="noopener noreferrer">{t('common.sourceDoc')}</a></>}
    </span>
  )
}

function FinTable({ view, st, unit, t }) {
  const [openCell, setOpenCell] = useState(null)
  const tbl = view.statements[st]
  if (!tbl) return null
  return (
    <div className="mk-scroll">
      <table className="fin-table">
        <thead>
          <tr>
            <th className="fin-sticky">{t(`fin.${st}`)}
              <div className="fin-unit">{unit === 'mil' ? t('fin.unitMillions') : t('fin.unitThousands')}</div>
            </th>
            {view.periods.map((p) => (
              <th key={p.key} className="num">
                {p.url
                  ? <a href={p.url} target="_blank" rel="noopener noreferrer"
                      title={`${t('fin.sourceDocTitle')}${p.published ? ` (${t('fin.publication')} ${p.published})` : ''}`}>{p.label}</a>
                  : p.label}
                {p.hrk && <div className="fin-badge">{t('fin.hrkBadge')}</div>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tbl.rows.map((r) => (
            <tr key={r.item} className={r.bold ? 'fin-bold' : ''}>
              <td className="fin-sticky" style={{ paddingLeft: 10 + r.indent * 16 }}>{t(`li.${r.item}`)}</td>
              {view.periods.map((p) => {
                const meta = r.restated && r.restated[p.key]
                const cellKey = `${r.item}|${p.key}`
                return (
                  <td key={p.key} className="num">
                    {fmtVal(r.values[p.key], unit)}
                    {meta && (
                      <button type="button" className="fin-restate"
                        title={t('fin.restatedBadge')}
                        onClick={() => setOpenCell(openCell === cellKey ? null : cellKey)}>K</button>
                    )}
                    {meta && openCell === cellKey && <RestatePop meta={meta} unit={unit} t={t} />}
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
  const { lang, t } = useLang()
  const T = String(ticker || '').toUpperCase()
  const stockHref = lang === 'en' ? `/en/stock/${T.toLowerCase()}` : `/dionica/${T.toLowerCase()}`
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
      document.title = `${data.ticker} ${t('fin.docTitle')}`
    }
  }, [data, lang])

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
            <h1 className="page-h1">{t('fin.title')} — {T}</h1>
            <div className="prof-empty-box">{t('fin.noData')}{' '}
              <Link to={stockHref}>{t('common.backToStock')}</Link></div>
          </section>
        )}
        {!data && !err && <div className="loading">{t('common.loading')}</div>}
        {data && (
          <>
            <nav className="fin-crumbs">
              <Link to={stockHref}>← {data.ticker} — {t('common.backToStock')}</Link>
              <span> · {t('fin.docsNote')}</span>
            </nav>
            <h1 className="page-h1">{t('fin.title')} — {data.name}</h1>

            <div className="fin-controls">
              <div className="fin-subtabs">
                {SUBTAB_KEYS.map(([k, key]) => (
                  <button key={k} type="button" className={st === k ? 'on' : ''}
                    onClick={() => setSt(k)}>{t(key)}</button>
                ))}
              </div>
              <div className="fin-right">
                <div className="fin-kind">
                  <button type="button" className={kind === 'annual' ? 'on' : ''}
                    onClick={() => setKind('annual')}>{t('fin.annual')}</button>
                  <button type="button" className={kind === 'interim' ? 'on' : ''}
                    onClick={() => setKind('interim')}>{t('fin.quarterly')}</button>
                </div>
                {data.bases.length > 1 && (
                  <div className="fin-kind">
                    {data.bases.map((b) => (
                      <button key={b} type="button" className={basis === b ? 'on' : ''}
                        onClick={() => setBasis(b)}>{t(`fin.${b}`)}</button>
                    ))}
                  </div>
                )}
                {view && view.statements[st] && (
                  <button type="button" className="fin-csv"
                    onClick={() => downloadCsv(view, st, data.unit, data.ticker, t)}>
                    {t('common.download')}
                  </button>
                )}
              </div>
            </div>
            <div className="fin-activeview">
              {t('fin.view')}: {t(`fin.${data.views[basis] ? basis : data.bases[0]}`)}
              {kind === 'interim' && ` · ${t('fin.cumulative')}`}
            </div>

            {view && view.statements[st]
              ? <FinTable view={view} st={st} unit={data.unit} t={t} />
              : (
                <div className="prof-empty-box">
                  {t(`fin.${st}`)} {t('fin.notInDb')}
                  {(data.missing.find((m) => m.statement === st) || {}).doc_url && (
                    <> — {t('common.sourceDoc')}: <a
                      href={data.missing.find((m) => m.statement === st).doc_url}
                      target="_blank" rel="noopener noreferrer">→</a></>
                  )}.
                </div>
              )}

            {data.missing.length > 0 && view && view.statements[st] && (
              <div className="subnote" style={{ marginTop: 10 }}>
                {t('fin.missing')}: {data.missing.map((m, i) => (
                  <span key={m.statement}>{i > 0 && ' · '}{t(`fin.${m.statement}`)}
                    {m.doc_url && <> (<a href={m.doc_url} target="_blank"
                      rel="noopener noreferrer">{t('common.sourceDoc')}</a>)</>}</span>
                ))}
              </div>
            )}

            <div className="fin-note">
              <p>{t('fin.schemaNote')}</p>
              <p>{t('fin.restateNote')}{' '}
              <Link to={stockHref}>{t('common.backToStock')}</Link>.</p>
              <p className="disc">{t('common.disclaimerLong')}</p>
            </div>
          </>
        )}
      </main>
      <SiteFooter />
    </div>
  )
}
