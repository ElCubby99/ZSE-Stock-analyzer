import React from 'react'
import { Link } from 'react-router-dom'
import { useLang } from './i18n/LangContext.jsx'
import { tx } from './i18n/dataText.mjs'
import { dash, num } from './format.js'

/* M17 DIO 2: "Kako je nastala ova procjena" — sklopivo, dno stranice dionice.
   Sadržaj je GENERIRAN iz istih podataka koji su dali valuaciju
   (data.methodology iz exporta) — bez ručno pisanog teksta po firmi.
   M38: UI tekstovi kroz t(), podatkovni (story/why/razlozi) kroz tx(). */

export default function MethodologyNote({ m }) {
  const { lang, t } = useLang()
  if (!m) return null
  const methodHref = lang === 'en' ? '/en/methodology' : (m.link || '/metodologija')
  return (
    <details className="legend" style={{ marginTop: 34 }}>
      <summary>{t('mn.summary')}</summary>
      <div className="mnote">
        <div className="prof-klabel">{t('mn.archetype')}</div>
        <p className="mnote-story">{tx(m.story, lang)}</p>

        <div className="prof-klabel">{t('mn.params')}</div>
        <div className="mnote-params">
          {m.parameters.map((p) => (
            <div className="mnote-param" key={p.k}>
              <span className="mnote-k">{tx(p.k, lang)}</span>
              <span className="mnote-v">{tx(p.v, lang)}</span>
              <span className="mnote-why">{tx(p.why, lang)}</span>
            </div>
          ))}
        </div>

        {m.limitations.length > 0 && (
          <>
            <div className="prof-klabel">{t('mn.limitations')}</div>
            <ul className="mnote-lims">
              {m.limitations.map((l, i) => <li key={i}>{tx(l, lang)}</li>)}
            </ul>
          </>
        )}

        {m.changelog.length > 0 && (
          <>
            <div className="prof-klabel">{t('mn.changelog')}</div>
            <table>
              <thead><tr><th>{t('common.date')}</th><th className="num">{t('mn.colOld')}</th>
                <th className="num">{t('mn.colNew')}</th><th>{t('mn.colReason')}</th></tr></thead>
              <tbody>
                {m.changelog.map((c, i) => (
                  <tr key={i}>
                    <td className="num">{c.date}</td>
                    <td className="num">{c.old_low !== null && c.old_low !== undefined
                      ? `${num(c.old_low, 2)}–${num(c.old_high, 2)}` : dash}</td>
                    <td className="num">{c.new_low !== null && c.new_low !== undefined
                      ? `${num(c.new_low, 2)}–${num(c.new_high, 2)}` : dash}</td>
                    <td style={{ fontSize: 12.5 }}>{tx(c.reason, lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        <ul className="mnote-notes">
          {m.notes.map((n, i) => <li key={i}>{tx(n, lang)}</li>)}
        </ul>
        <div className="mnote-foot">
          <Link to={methodHref}>{t('mn.fullLink')}</Link>
          <span className="mnote-mar">{tx(m.mar, lang)}</span>
        </div>
      </div>
    </details>
  )
}
