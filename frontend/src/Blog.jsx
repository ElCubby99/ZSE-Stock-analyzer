import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { useLang } from './i18n/LangContext.jsx'

/* Blog (dizajn B): statični JSON-ovi iz content/blog/*.md (scripts/build_blog.py)
   + CMS postovi (Supabase, prerender ih spušta u iste JSON-ove).
   M70: dvojezično — EN čita /blog/en/... (isti slug spaja HR i EN par);
   kategorije u podacima ostaju HR, prikazni naziv ide kroz i18n. */

/* vrijednosti kategorija su PODACI (ključevi u blog JSON-ovima), ne prikazni
   tekst — prikaz ide kroz t(CAT_KEY[...]); dijakritika kroz \u escape da
   i18n lint ne vidi hardkodirani HR string */
const CAT_MARKET = 'Tr\u017ei\u0161te'
const CATS = ['Sve', 'Edukacija', 'Analize', CAT_MARKET]
const CAT_KEY = {
  Sve: 'blog.catAll',
  Edukacija: 'blog.catEdu',
  Analize: 'blog.catAnalyses',
  [CAT_MARKET]: 'blog.catMarket',
}

export function BlogIndex() {
  const { lang, t } = useLang()
  const [posts, setPosts] = useState(null)
  const [cat, setCat] = useState('Sve')
  const base = lang === 'en' ? '/blog/en' : '/blog'
  const linkBase = lang === 'en' ? '/en/blog' : '/blog'
  useEffect(() => {
    fetch(`${base}/index.json`).then((r) => r.json()).then(setPosts).catch(() => setPosts([]))
    document.title = `Blog · Burzovni list`
  }, [base])
  const list = (posts || []).filter((p) => cat === 'Sve' || p.category === cat)
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
      <h1 className="page-h1">Blog</h1>
      <div className="prof-chips" style={{ margin: '14px 0 22px' }}>
        {CATS.map((c) => (
          <button key={c} className={`prof-chip ${cat === c ? 'on' : ''}`}
            onClick={() => setCat(c)}>{t(CAT_KEY[c]).toUpperCase()}</button>
        ))}
      </div>
      {posts === null ? <div className="loading">{t('common.loading')}</div>
        : !list.length ? <div className="prof-empty-box">{t('blog.emptyCat')}</div>
          : list.map((p) => (
            <Link to={`${linkBase}/${p.slug}`} key={p.slug} className="blog-card">
              <div className="blog-meta">{t(CAT_KEY[p.category] || 'blog.catAll').toUpperCase()} · {p.date}</div>
              <div className="blog-title">{p.title}</div>
              <div className="blog-sum">{p.summary}</div>
            </Link>
          ))}
      <div className="disc" style={{ marginTop: 32 }}>
        {t('blog.disc')}
      </div>
      </main>
      <SiteFooter />
    </div>
  )
}

export function BlogPost() {
  const { lang, t } = useLang()
  const { slug } = useParams()
  const [post, setPost] = useState(null)
  const [err, setErr] = useState(null)
  const base = lang === 'en' ? '/blog/en' : '/blog'
  const linkBase = lang === 'en' ? '/en/blog' : '/blog'
  useEffect(() => {
    setPost(null); setErr(null)
    fetch(`${base}/${slug}.json`)
      .then((r) => {
        if (!r.ok || !(r.headers.get('content-type') || '').includes('json')) throw new Error(lang === 'en' ? 'post not found' : 'nema posta')
        return r.json()
      })
      .then((p) => { setPost(p); document.title = `${p.title} · Blog` })
      .catch((e) => setErr(String(e.message || e)))
  }, [slug, base, lang])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
      {err && <section className="error">{t('common.error')}: {err}</section>}
      {!post && !err && <div className="loading">{t('common.loading')}</div>}
      {post && (
        <article className="blog-post">
          <div className="blog-meta">{t(CAT_KEY[post.category] || 'blog.catAll').toUpperCase()} · {post.date} · <Link to={linkBase}>{t('blog.allArticles')}</Link></div>
          <h1 className="page-h1">{post.title}</h1>
          <div className="blog-body" dangerouslySetInnerHTML={{ __html: post.html }} />
        </article>
      )}
      </main>
      <SiteFooter />
    </div>
  )
}
