import React from 'react'
import { Link } from 'react-router-dom'
import { dash, num } from './format.js'

/* M17 DIO 2: "Kako je nastala ova procjena" — sklopivo, dno stranice dionice.
   Sadržaj je GENERIRAN iz istih podataka koji su dali valuaciju
   (data.methodology iz exporta) — bez ručno pisanog teksta po firmi. */

export default function MethodologyNote({ m }) {
  if (!m) return null
  return (
    <details className="legend" style={{ marginTop: 34 }}>
      <summary>KAKO JE NASTALA OVA PROCJENA — metodološka napomena (klik za otvaranje)</summary>
      <div className="mnote">
        <div className="prof-klabel">ARHETIP I SIDRO</div>
        <p className="mnote-story">{m.story}</p>

        <div className="prof-klabel">KLJUČNI PARAMETRI OVE PROCJENE</div>
        <div className="mnote-params">
          {m.parameters.map((p) => (
            <div className="mnote-param" key={p.k}>
              <span className="mnote-k">{p.k}</span>
              <span className="mnote-v">{p.v}</span>
              <span className="mnote-why">{p.why}</span>
            </div>
          ))}
        </div>

        {m.limitations.length > 0 && (
          <>
            <div className="prof-klabel">OGRANIČENJA OVE PROCJENE</div>
            <ul className="mnote-lims">
              {m.limitations.map((l, i) => <li key={i}>{l}</li>)}
            </ul>
          </>
        )}

        {m.changelog.length > 0 && (
          <>
            <div className="prof-klabel">POVIJEST PROMJENA PROCJENE</div>
            <table>
              <thead><tr><th>Datum</th><th className="num">Stara zona €</th>
                <th className="num">Nova zona €</th><th>Razlog</th></tr></thead>
              <tbody>
                {m.changelog.map((c, i) => (
                  <tr key={i}>
                    <td className="num">{c.date}</td>
                    <td className="num">{c.old_low !== null && c.old_low !== undefined
                      ? `${num(c.old_low, 2)}–${num(c.old_high, 2)}` : dash}</td>
                    <td className="num">{c.new_low !== null && c.new_low !== undefined
                      ? `${num(c.new_low, 2)}–${num(c.new_high, 2)}` : dash}</td>
                    <td style={{ fontSize: 12.5 }}>{c.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        <ul className="mnote-notes">
          {m.notes.map((n, i) => <li key={i}>{n}</li>)}
        </ul>
        <div className="mnote-foot">
          <Link to={m.link}>Puna metodologija — kako procjenjujemo →</Link>
          <span className="mnote-mar">{m.mar}</span>
        </div>
      </div>
    </details>
  )
}
