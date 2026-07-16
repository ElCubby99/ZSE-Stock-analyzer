import React, { useEffect, useState } from 'react'
import { SiteFooter, SiteHeader } from './Shell.jsx'

/* M17 DIO 1: globalna stranica "Kako procjenjujemo" — renderira
   /data/metodologija.json (izvor istine: docs/metodologija.md). */

export default function Metodologija() {
  const [doc, setDoc] = useState(null)
  useEffect(() => { document.title = 'Metodologija · Burzovni list' }, [])
  const [alert, setAlert] = useState(null)
  useEffect(() => {
    fetch('/data/overview.json').then((r) => r.json())
      .then((o) => setAlert(o.calibration_alert || null)).catch(() => {})
  }, [])
  useEffect(() => {
    fetch('/data/metodologija.json').then((r) => r.json()).then(setDoc)
      .catch(() => setDoc(false))
  }, [])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
        {alert && alert.active && (
          <div className="prof-illiq" style={{ marginBottom: 14 }}>
            <span className="prof-illiq-t">ZONE U PROVJERI ZA DIO DIONICA</span>
            <span className="prof-illiq-n">
              {alert.share_pct} % najlikvidnijih dionica ima raskorak veći od
              30 % naspram naše fer-zone — to je signal za provjeru naših
              pretpostavki, ne tržišta. Zone provjeravamo; ne prilagođavamo ih
              cijenama.
            </span>
          </div>
        )}
        {doc === null && <div className="loading">učitavam…</div>}
        {doc === false && <div className="error">metodologija nije dostupna</div>}
        {doc && (
          <>
            <div className="mk-title" style={{ marginBottom: 4 }}>
              <h1>{doc.title}</h1>
            </div>
            <div className="prof-klabel" style={{ marginBottom: 18 }}>
              METODOLOGIJA {doc.version} · AŽURIRANO {doc.updated}
            </div>
            <article className="blog-body" dangerouslySetInnerHTML={{ __html: doc.html }} />
          </>
        )}
      </main>
      <SiteFooter />
    </div>
  )
}
