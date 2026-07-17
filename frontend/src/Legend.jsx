import React from 'react'
import { useLang } from './i18n/LangContext.jsx'

/* Legenda pojmova — jedna rečenica OBIČNIM jezikom po pojmu (dizajn:
   dvorazinski princip — jednostavno vidljivo, tehnički detalj iza klika).
   M38: tekst živi u i18n rječniku (lg.k.* = naziv, lg.d.* = definicija);
   <Term t="..."> i dalje prima HR id pojma (stabilan API za komponente).
   Tekst je edukativan, bez ocjena (MAR). */

/* id pojma (kako ga koriste <Term t="...">) -> slug ključa u rječniku.
   Id-ovi s dijakritikom su zapisani unicode escapeom (i18n lint). */
export const TERM_KEYS = {
  'P/E': 'pe',
  'P/B': 'pb',
  'EV/EBITDA': 'evEbitda',
  DCF: 'dcf',
  comps: 'comps',
  SOTP: 'sotp',
  DDM: 'ddm',
  ROE: 'roe',
  EBITDA: 'ebitda',
  backlog: 'backlog',
  'fer-zona': 'ferZona',
  sidro: 'sidro',
  beta: 'beta',
  'tro\u0161ak kapitala': 'trosakKapitala', // 'trošak kapitala'
  r: 'r',
  rf: 'rf',
  ERP: 'erp',
  CRP: 'crp',
  TTM: 'ttm',
  g: 'g',
  g1: 'g1',
  CAGR: 'cagr',
  payout: 'payout',
  D_sust: 'dSust',
  'dividendni pod': 'divPod',
  medijan: 'medijan',
}

/* Pojam s tooltipom — točkasto podcrtan; definicija na hover (title). */
export function Term({ t: term, children }) {
  const { t } = useLang()
  const slug = TERM_KEYS[term]
  if (!slug) return children ?? term
  return <span className="term" title={t(`lg.d.${slug}`)}>{children ?? t(`lg.k.${slug}`)}</span>
}

export function Legend({ open = false }) {
  const { t } = useLang()
  return (
    <details className="legend" open={open}>
      <summary>{t('lg.summary')}</summary>
      <dl>
        {Object.entries(TERM_KEYS).map(([id, slug]) => (
          <div className="legend-row" key={id} id={`legenda-${id.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}`}>
            <dt>{t(`lg.k.${slug}`)}</dt>
            <dd>{t(`lg.d.${slug}`)}</dd>
          </div>
        ))}
      </dl>
      <div className="legend-note">{t('lg.note')}</div>
    </details>
  )
}
