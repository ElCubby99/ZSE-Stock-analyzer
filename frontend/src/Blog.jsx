import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'

/* Blog (dizajn B): statični JSON-ovi iz content/blog/*.md (scripts/build_blog.py).
   Kategorije: Edukacija / Analize / Tržište. Bez backend poziva. */

const CATS = ['Sve', 'Edukacija', 'Analize', 'Tržište']

export function BlogIndex() {
  const [posts, setPosts] = useState(null)
  const [cat, setCat] = useState('Sve')
  useEffect(() => {
    fetch('/blog/index.json').then((r) => r.json()).then(setPosts).catch(() => setPosts([]))
    document.title = 'Blog · ZSE analiza'
  }, [])
  const list = (posts || []).filter((p) => cat === 'Sve' || p.category === cat)
  return (
    <div className="wrap">
      <SiteHeader />
      <h1 className="page-h1">Blog</h1>
      <div className="prof-chips" style={{ margin: '14px 0 22px' }}>
        {CATS.map((c) => (
          <button key={c} className={`prof-chip ${cat === c ? 'on' : ''}`}
            onClick={() => setCat(c)}>{c.toUpperCase()}</button>
        ))}
      </div>
      {posts === null ? <div className="loading">učitavam…</div>
        : !list.length ? <div className="prof-empty-box">Nema objava u ovoj kategoriji.</div>
          : list.map((p) => (
            <Link to={`/blog/${p.slug}`} key={p.slug} className="blog-card">
              <div className="blog-meta">{p.category.toUpperCase()} · {p.date}</div>
              <div className="blog-title">{p.title}</div>
              <div className="blog-sum">{p.summary}</div>
            </Link>
          ))}
      <div className="disc" style={{ marginTop: 32 }}>
        Edukativni i informativni sadržaj — nije investicijski savjet ni preporuka.
      </div>
      <SiteFooter />
    </div>
  )
}

export function BlogPost() {
  const { slug } = useParams()
  const [post, setPost] = useState(null)
  const [err, setErr] = useState(null)
  useEffect(() => {
    setPost(null); setErr(null)
    fetch(`/blog/${slug}.json`)
      .then((r) => {
        if (!r.ok || !(r.headers.get('content-type') || '').includes('json')) throw new Error('nema posta')
        return r.json()
      })
      .then((p) => { setPost(p); document.title = `${p.title} · Blog` })
      .catch((e) => setErr(String(e.message || e)))
  }, [slug])
  return (
    <div className="wrap">
      <SiteHeader />
      {err && <section className="error">Greška: {err}</section>}
      {!post && !err && <div className="loading">učitavam…</div>}
      {post && (
        <article className="blog-post">
          <div className="blog-meta">{post.category.toUpperCase()} · {post.date} · <Link to="/blog">← svi članci</Link></div>
          <h1 className="page-h1">{post.title}</h1>
          <div className="blog-body" dangerouslySetInnerHTML={{ __html: post.html }} />
        </article>
      )}
    </div>
  )
}
