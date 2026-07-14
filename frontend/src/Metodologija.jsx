import React, { useEffect, useState } from 'react'
import { SiteFooter, SiteHeader } from './Shell.jsx'

/* M17 DIO 1: globalna stranica "Kako procjenjujemo" — renderira
   /data/metodologija.json (izvor istine: docs/metodologija.md). */

export default function Metodologija() {
  const [doc, setDoc] = useState(null)
  useEffect(() => { document.title = 'Metodologija · Burzovni list' }, [])
  useEffect(() => {
    fetch('/data/metodologija.json').then((r) => r.json()).then(setDoc)
      .catch(() => setDoc(false))
  }, [])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
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
