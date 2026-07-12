import React, { useEffect } from 'react'
import { SiteFooter, SiteHeader } from './Shell.jsx'

export default function Portfelj() {
  useEffect(() => { document.title = 'Portfelj · Burzovni list' }, [])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        <div className="mk-title"><h1>Moj portfelj</h1></div>
        <div className="prof-unavail" style={{ minHeight: 220, display: 'flex',
          alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
          <div>
            <div className="prof-klabel">U PRIPREMI</div>
            <p style={{ maxWidth: 520 }}>
              Portfelj dolazi s fazom prijave korisnika — praćenje pozicija,
              raskorak naspram fer-zone i alokacija po sektoru.
            </p>
          </div>
        </div>
      </main>
      <SiteFooter />
    </div>
  )
}
