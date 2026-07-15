import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'

/* M30: /vijesti — kratke vijesti (auto iz pipelinea + ručne), grupirane po
   danu. Podaci dolaze iz statičnog /data/vijesti.json kojeg build (prerender)
   puni iz Supabase news_items (SAMO status='published' — RLS garantira za
   anon ključ). Zadano je svaka vijest pokazivač na postojeću stranicu
   (link_path); detail ruta /vijesti/<slug> postoji samo kad vijest ima body
   (izbjegavamo duplicate content). */

export const CATEGORY_HR = {
  novo_izvjesce: 'NOVO IZVJEŠĆE',
  dividenda: 'DIVIDENDA',
  promjena_cijene: 'CIJENA',
  opce: 'OPĆE',
}

export const XFollow = ({ compact }) => {
  const handle = (import.meta.env.VITE_X_HANDLE || '').replace(/^@/, '')
  if (!handle) return null // prazna env varijabla -> bez razbijenog linka
  return (
    <a className={compact ? '' : 'x-follow'} href={`https://x.com/${handle}`}
      target="_blank" rel="noopener noreferrer">
      {compact ? `X: @${handle}` : `Prati nas na X — @${handle}`}
    </a>
  )
}

const fmtDay = (iso) => {
  if (!iso) return '—'
  const [y, m, d] = iso.slice(0, 10).split('-')
  return `${Number(d)}.${Number(m)}.${y}.`
}

function NewsRow({ n }) {
  const label = CATEGORY_HR[n.category] || 'OPĆE'
  const target = n.slug ? `/vijesti/${n.slug}` : n.link_path
  return (
    <Link to={target} className="news-row">
      <span className="blog-meta">{label}{n.ticker ? ` · ${n.ticker}` : ''}</span>
      <span className="news-headline">{n.headline}</span>
    </Link>
  )
}

export function VijestiIndex() {
  const [items, setItems] = useState(null)
  useEffect(() => {
    document.title = 'Vijesti · Burzovni list'
    fetch('/data/vijesti.json').then((r) => r.json()).then(setItems).catch(() => setItems([]))
  }, [])
  const byDay = new Map()
  for (const n of items || []) {
    const day = (n.published_at || '').slice(0, 10) || '—'
    if (!byDay.has(day)) byDay.set(day, [])
    byDay.get(day).push(n)
  }
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
        <div className="mk-title"><h1>Vijesti</h1></div>
        <p className="imp-p">Kratke obavijesti o novim izvješćima, dividendama i
        ažuriranjima analiza — svaka vodi na postojeću stranicu s podacima i
        izvorima. <XFollow /></p>
        {items === null ? <div className="loading">učitavam…</div>
          : !items.length ? <div className="prof-empty-box">Trenutno nema objavljenih vijesti.</div>
            : [...byDay.entries()].map(([day, list]) => (
              <section key={day}>
                <div className="sec-label">{fmtDay(day)}</div>
                {list.map((n) => <NewsRow n={n} key={n.id} />)}
              </section>
            ))}
        <div className="disc" style={{ marginTop: 32 }}>
          Informativni sadržaj — nije investicijski savjet ni preporuka.
        </div>
      </main>
      <SiteFooter />
    </div>
  )
}

export function VijestDetail() {
  const { slug } = useParams()
  const [items, setItems] = useState(null)
  useEffect(() => {
    fetch('/data/vijesti.json').then((r) => r.json()).then(setItems).catch(() => setItems([]))
  }, [])
  const n = (items || []).find((x) => x.slug === slug)
  useEffect(() => {
    if (n) document.title = `${n.headline} · Burzovni list`
  }, [n])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
        {items === null ? <div className="loading">učitavam…</div>
          : !n ? (
            <section>
              <div className="mk-title"><h1>Vijest nije pronađena</h1></div>
              <p className="imp-p"><Link to="/vijesti">← sve vijesti</Link></p>
            </section>
          ) : (
            <article className="blog-post">
              <div className="blog-meta">
                {CATEGORY_HR[n.category] || 'OPĆE'}
                {n.ticker ? ` · ${n.ticker}` : ''} · {fmtDay(n.published_at)}
                {' · '}<Link to="/vijesti">← sve vijesti</Link>
              </div>
              <h1 className="page-h1">{n.headline}</h1>
              {(n.body || '').split(/\n{2,}/).filter(Boolean).map((par) => (
                <p className="imp-p" key={par.slice(0, 40)}>{par}</p>
              ))}
              <p className="imp-p"><Link to={n.link_path}>→ pogledaj stranicu s podacima</Link></p>
            </article>
          )}
      </main>
      <SiteFooter />
    </div>
  )
}
