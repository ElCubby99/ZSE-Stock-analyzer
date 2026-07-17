import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { useLang } from './i18n/LangContext.jsx'
import { fmtDate } from './format.js'

/* M30: /vijesti — kratke vijesti (auto iz pipelinea + ručne), grupirane po
   danu. Podaci dolaze iz statičnog /data/vijesti.json kojeg build (prerender)
   puni iz Supabase news_items (SAMO status='published' — RLS garantira za
   anon ključ). Zadano je svaka vijest pokazivač na postojeću stranicu
   (link_path); detail ruta /vijesti/<slug> postoji samo kad vijest ima body
   (izbjegavamo duplicate content). */

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



function NewsRow({ n, t }) {
  const label = t(`newscat.${n.category}`) || t('newscat.opce')
  const target = n.slug ? `/vijesti/${n.slug}` : n.link_path
  return (
    <Link to={target} className="news-row">
      <span className="blog-meta">{label}{n.ticker ? ` · ${n.ticker}` : ''}</span>
      <span className="news-headline">{n.headline}</span>
    </Link>
  )
}

export function VijestiIndex() {
  const { lang, t } = useLang()
  const [items, setItems] = useState(null)
  useEffect(() => {
    document.title = `${t('news.title')} · Burzovni list`
    fetch('/data/vijesti.json').then((r) => r.json()).then(setItems).catch(() => setItems([]))
  }, [lang])
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
        <div className="mk-title"><h1>{t('news.title')}</h1></div>
        <p className="imp-p">{t('news.intro')} <XFollow /></p>
        {items === null ? <div className="loading">{t('common.loading')}</div>
          : !items.length ? <div className="prof-empty-box">{t('news.empty')}</div>
            : [...byDay.entries()].map(([day, list]) => (
              <section key={day}>
                <div className="sec-label">{fmtDate(day)}</div>
                {list.map((n) => <NewsRow n={n} t={t} key={n.id} />)}
              </section>
            ))}
        <div className="disc" style={{ marginTop: 32 }}>
          {t('common.notAdvice')}
        </div>
      </main>
      <SiteFooter />
    </div>
  )
}

export function VijestDetail() {
  const { t } = useLang()
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
        {items === null ? <div className="loading">{t('common.loading')}</div>
          : !n ? (
            <section>
              <div className="mk-title"><h1>{t('news.notFound')}</h1></div>
              <p className="imp-p"><Link to="/vijesti">← {t('news.all')}</Link></p>
            </section>
          ) : (
            <article className="blog-post">
              <div className="blog-meta">
                {t(`newscat.${n.category}`)}
                {n.ticker ? ` · ${n.ticker}` : ''} · {fmtDate(n.published_at)}
                {' · '}<Link to="/vijesti">← {t('news.all')}</Link>
              </div>
              <h1 className="page-h1">{n.headline}</h1>
              {(n.body || '').split(/\n{2,}/).filter(Boolean).map((par) => (
                <p className="imp-p" key={par.slice(0, 40)}>{par}</p>
              ))}
              <p className="imp-p"><Link to={n.link_path}>→ {t('news.dataPage')}</Link></p>
            </article>
          )}
      </main>
      <SiteFooter />
    </div>
  )
}
