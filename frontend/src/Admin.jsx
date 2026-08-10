import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { supabase } from './supabase.js'
import { AuthForms } from './Portfelj.jsx'

/* M27: /admin — CMS za blog. Iza logina + profiles.is_admin (RLS je stvarna
   obrana; UI guard je UX). NE ulazi u sitemap, noindex. Markdown preview se
   UVIJEK sanitizira (DOMPurify) — sirovi HTML se nikad ne renderira, čak ni
   za admin-only unos. */

const kebab = (s) => String(s).toLowerCase()
  .normalize('NFKD').replace(/[̀-ͯ]/g, '')
  .replace(/đ/g, 'd').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')

const SLUG_RX = /^[a-z0-9]+(-[a-z0-9]+)*$/

const render = (md) => DOMPurify.sanitize(marked.parse(md || '', { async: false }))

const EMPTY = {
  id: null, slug: '', title: '', meta_description: '', content_md: '',
  tags: [], cover_image_url: '', status: 'draft', published_at: null,
}

function Editor({ post, onDone }) {
  const [p, setP] = useState({ ...EMPTY, ...post })
  const [slugTouched, setSlugTouched] = useState(!!post?.id)
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState(false)
  const set = (k, v) => setP((x) => ({ ...x, [k]: v }))

  const setTitle = (v) => {
    set('title', v)
    if (!slugTouched) set('slug', kebab(v))
  }

  const upload = async (file) => {
    setMsg(null)
    const path = `${Date.now()}-${kebab(file.name.replace(/\.[^.]+$/, ''))}.${file.name.split('.').pop()}`
    const { error } = await supabase.storage.from('blog-media').upload(path, file)
    if (error) { setMsg({ t: 'err', s: `Upload pao: ${error.message}` }); return }
    const { data } = supabase.storage.from('blog-media').getPublicUrl(path)
    set('cover_image_url', data.publicUrl)
  }

  const save = async (status) => {
    setMsg(null)
    if (!p.title.trim()) { setMsg({ t: 'err', s: 'Naslov je obavezan.' }); return }
    if (!SLUG_RX.test(p.slug)) { setMsg({ t: 'err', s: 'Slug mora biti kebab-case (mala slova, brojke, crtice).' }); return }
    if (!p.content_md.trim()) { setMsg({ t: 'err', s: 'Sadržaj je obavezan.' }); return }
    setBusy(true)
    // slug kolizija — provjera PRIJE spremanja
    const dup = await supabase.from('blog_posts').select('id').eq('slug', p.slug)
    if (dup.data?.some((r) => r.id !== p.id)) {
      setBusy(false)
      setMsg({ t: 'err', s: `Slug "${p.slug}" već postoji — odaberi drugi.` })
      return
    }
    const row = {
      slug: p.slug, title: p.title,
      meta_description: (p.meta_description || '').slice(0, 160) || null,
      content_md: p.content_md,
      tags: p.tags, cover_image_url: p.cover_image_url || null, status,
    }
    if (status === 'published' && !p.published_at) row.published_at = new Date().toISOString()
    const q = p.id
      ? supabase.from('blog_posts').update(row).eq('id', p.id)
      : supabase.from('blog_posts').insert(row)
    const { error } = await q
    if (error) { setBusy(false); setMsg({ t: 'err', s: error.message }); return }
    let deployMsg = ''
    if (status === 'published') {
      // rebuild produkcije — hook URL je secret Edge Functiona, ne frontenда
      const { data, error: fe } = await supabase.functions
        .invoke('trigger-deploy', { body: { slug: p.slug } })
      deployMsg = fe ? ' UPOZORENJE: deploy hook nije okinut — objavi ponovno ili pokreni build ručno.'
        : (data?.deploy_triggered ? ' Build je pokrenut (produkcija za par minuta).' : '')
    }
    setBusy(false)
    setMsg({ t: 'ok', s: (status === 'published' ? 'Objavljeno.' : 'Spremljeno kao draft.') + deployMsg })
    onDone()
  }

  const metaLen = (p.meta_description || '').length
  return (
    <section>
      <div className="sec-label">{p.id ? `Uređivanje: ${p.slug}` : 'Novi post'}</div>
      <div className="adm-form">
        <label>Naslov
          <input value={p.title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label>Slug (URL)
          <input value={p.slug}
            onChange={(e) => { setSlugTouched(true); set('slug', e.target.value) }} />
          {!SLUG_RX.test(p.slug) && p.slug && <span className="flag">nevaljan format</span>}
        </label>
        <label>Meta description
          <textarea rows={2} value={p.meta_description || ''}
            onChange={(e) => set('meta_description', e.target.value)} />
          <span className={metaLen > 160 ? 'flag' : 'fund-src'}>
            {metaLen}/160{metaLen > 160 ? ' — predugo, Google će odrezati' : ''}
          </span>
        </label>
        <label>Tagovi (zarezom odvojeni)
          <input value={(p.tags || []).join(', ')}
            onChange={(e) => set('tags', e.target.value.split(',').map((t) => t.trim()).filter(Boolean))} />
        </label>
        <label>Cover slika (https URL ili upload)
          <input value={p.cover_image_url || ''} placeholder="https://…"
            onChange={(e) => set('cover_image_url', e.target.value)} />
          <input type="file" accept="image/*"
            onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
          {!p.cover_image_url && (
            <span className="flag">bez cover slike — social share kartice će biti prazne</span>)}
        </label>
        <div className="adm-md">
          <label>Sadržaj (Markdown)
            <textarea rows={18} value={p.content_md}
              onChange={(e) => set('content_md', e.target.value)} />
          </label>
          <div>
            <div className="prof-klabel">PREGLED</div>
            <div className="blog-body adm-preview"
              dangerouslySetInnerHTML={{ __html: render(p.content_md) }} />
          </div>
        </div>
        <div className="cc-btns">
          <button type="button" className="auth-submit" disabled={busy}
            onClick={() => save('draft')}>Spremi kao draft</button>
          <button type="button" className="auth-submit" disabled={busy}
            onClick={() => save('published')}>
            {p.status === 'published' ? 'Ažuriraj (objavljeno)' : 'Objavi'}
          </button>
          <button type="button" className="cc-btn acct-link-btn" onClick={onDone}>Natrag</button>
        </div>
        {msg && <div className={`auth-msg ${msg.t}`}>{msg.s}</div>}
      </div>
    </section>
  )
}

function PostList({ posts, onEdit, onRefresh }) {
  const [filter, setFilter] = useState('svi')
  const rows = posts.filter((p) => filter === 'svi' || p.status === filter)

  const quickStatus = async (p, status) => {
    const row = { status }
    if (status === 'published' && !p.published_at) row.published_at = new Date().toISOString()
    await supabase.from('blog_posts').update(row).eq('id', p.id)
    if (status === 'published') {
      await supabase.functions.invoke('trigger-deploy', { body: { slug: p.slug } })
    }
    onRefresh()
  }
  const hardDelete = async (p) => {
    // prava delete samo uz izričitu potvrdu; standard je soft (archived)
    if (!window.confirm(`TRAJNO obrisati "${p.slug}"? Ovo se ne može vratiti.`)) return
    await supabase.from('blog_posts').delete().eq('id', p.id)
    onRefresh()
  }

  return (
    <section>
      <div className="sec-label">Postovi ({rows.length})</div>
      <div className="prof-chips" style={{ marginBottom: 10 }}>
        {['svi', 'draft', 'published', 'archived'].map((f) => (
          <button key={f} className={filter === f ? 'on' : ''}
            onClick={() => setFilter(f)}>{f.toUpperCase()}</button>
        ))}
      </div>
      <table>
        <thead><tr><th>Naslov</th><th>Slug</th><th>Status</th>
          <th>Objavljen</th><th /></tr></thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.id}>
              <td><b>{p.title}</b></td>
              <td className="fund-src">{p.slug}</td>
              <td>{p.status === 'published'
                ? <span className="okflag">objavljeno</span>
                : <span className="flag">{p.status}</span>}</td>
              <td className="fund-src">{p.published_at ? p.published_at.slice(0, 10) : '—'}</td>
              <td style={{ whiteSpace: 'nowrap' }}>
                <button className="pf-logout" onClick={() => onEdit(p)}>uredi</button>{' '}
                {p.status !== 'published' && (
                  <button className="pf-logout" onClick={() => quickStatus(p, 'published')}>objavi</button>)}{' '}
                {p.status === 'published' && (
                  <button className="pf-logout" onClick={() => quickStatus(p, 'draft')}>skini u draft</button>)}{' '}
                {p.status !== 'archived' && (
                  <button className="pf-del" onClick={() => quickStatus(p, 'archived')}>obriši (soft)</button>)}{' '}
                {p.status === 'archived' && (
                  <button className="pf-del" onClick={() => hardDelete(p)}>obriši TRAJNO</button>)}
              </td>
            </tr>
          ))}
          {!rows.length && <tr><td colSpan={5} className="subnote">nema postova</td></tr>}
        </tbody>
      </table>
    </section>
  )
}

/* ============ M30: Vijesti (news_items) ============ */

const NEWS_CATS = ['novo_izvjesce', 'dividenda', 'promjena_cijene', 'opce']
const NEWS_CAT_HR = {
  novo_izvjesce: 'novo izvješće',
  dividenda: 'dividenda',
  promjena_cijene: 'promjena cijene',
  opce: 'opće',
}
const NEWS_EMPTY = {
  id: null, ticker: '', category: 'opce', headline: '', body: '',
  link_path: '/', source_type: 'manual', status: 'draft', published_at: null,
}

function NewsEditor({ item, onDone }) {
  const [n, setN] = useState({ ...NEWS_EMPTY, ...item })
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState(false)
  const set = (k, v) => setN((x) => ({ ...x, [k]: v }))

  const save = async (status) => {
    setMsg(null)
    if (!n.headline.trim()) { setMsg({ t: 'err', s: 'Naslov je obavezan.' }); return }
    if (n.headline.length > 120) { setMsg({ t: 'err', s: 'Naslov: najviše 120 znakova.' }); return }
    if (!/^\//.test(n.link_path)) { setMsg({ t: 'err', s: 'Link mora biti interna ruta (počinje s /).' }); return }
    setBusy(true)
    const row = {
      ticker: n.ticker.trim() ? n.ticker.trim().toUpperCase() : null,
      category: n.category, headline: n.headline.trim(),
      body: n.body.trim() || null, link_path: n.link_path.trim(), status,
    }
    if (status === 'published' && !n.published_at) row.published_at = new Date().toISOString()
    const q = n.id
      ? supabase.from('news_items').update(row).eq('id', n.id)
      : supabase.from('news_items').insert(row)
    const { error } = await q
    setBusy(false)
    if (error) { setMsg({ t: 'err', s: error.message }); return }
    setMsg({ t: 'ok', s: status === 'published' ? 'Objavljeno (vidljivo nakon rebuilda).' : 'Spremljeno kao draft.' })
    onDone()
  }

  return (
    <section>
      <div className="sec-label">{n.id ? 'Uređivanje vijesti' : 'Nova vijest'}
        {n.source_type === 'auto' && <span className="flag" style={{ marginLeft: 8 }}>auto</span>}</div>
      <div className="adm-form">
        <label>Naslov (headline, ≤120)
          <input value={n.headline} maxLength={140}
            onChange={(e) => set('headline', e.target.value)} />
          <span className={n.headline.length > 120 ? 'flag' : 'fund-src'}>{n.headline.length}/120</span>
        </label>
        <label>Kategorija
          <select value={n.category} onChange={(e) => set('category', e.target.value)}>
            {NEWS_CATS.map((c) => <option key={c} value={c}>{NEWS_CAT_HR[c]}</option>)}
          </select>
        </label>
        <label>Ticker (opcionalno)
          <input value={n.ticker || ''} placeholder="npr. KOEI"
            onChange={(e) => set('ticker', e.target.value)} />
        </label>
        <label>Link (interna ruta na koju vijest upućuje)
          <input value={n.link_path} placeholder="/dionica/koei"
            onChange={(e) => set('link_path', e.target.value)} />
        </label>
        <label>Tekst (opcionalno — s tekstom vijest dobiva vlastitu stranicu)
          <textarea rows={6} value={n.body || ''}
            onChange={(e) => set('body', e.target.value)} />
        </label>
        <div className="cc-btns">
          <button type="button" className="auth-submit" disabled={busy}
            onClick={() => save('draft')}>Spremi kao draft</button>
          <button type="button" className="auth-submit" disabled={busy}
            onClick={() => save('published')}>
            {n.status === 'published' ? 'Ažuriraj (objavljeno)' : 'Objavi'}
          </button>
          <button type="button" className="cc-btn acct-link-btn" onClick={onDone}>Natrag</button>
        </div>
        {msg && <div className={`auth-msg ${msg.t}`}>{msg.s}</div>}
      </div>
    </section>
  )
}

function NewsList({ items, onEdit, onRefresh }) {
  const [status, setStatus] = useState('svi')
  const [cat, setCat] = useState('sve')
  const rows = items
    .filter((n) => status === 'svi' || n.status === status)
    .filter((n) => cat === 'sve' || n.category === cat)

  const publish = async (n) => {
    await supabase.from('news_items')
      .update({ status: 'published', published_at: n.published_at || new Date().toISOString() })
      .eq('id', n.id)
    onRefresh()
  }
  const unpublish = async (n) => {
    await supabase.from('news_items').update({ status: 'draft' }).eq('id', n.id)
    onRefresh()
  }
  const remove = async (n) => {
    if (!window.confirm(`Obrisati vijest "${n.headline}"?`)) return
    await supabase.from('news_items').delete().eq('id', n.id)
    onRefresh()
  }

  return (
    <section>
      <div className="sec-label">Vijesti ({rows.length})</div>
      <div className="prof-chips" style={{ marginBottom: 6 }}>
        {['svi', 'draft', 'published'].map((f) => (
          <button key={f} className={status === f ? 'on' : ''}
            onClick={() => setStatus(f)}>{f.toUpperCase()}</button>
        ))}
      </div>
      <div className="prof-chips" style={{ marginBottom: 10 }}>
        {['sve', ...NEWS_CATS].map((f) => (
          <button key={f} className={cat === f ? 'on' : ''}
            onClick={() => setCat(f)}>{(NEWS_CAT_HR[f] || f).toUpperCase()}</button>
        ))}
      </div>
      <table>
        <thead><tr><th>Naslov</th><th>Kategorija</th><th>Status</th>
          <th>Datum</th><th /></tr></thead>
        <tbody>
          {rows.map((n) => (
            <tr key={n.id}>
              <td><b>{n.headline}</b>{' '}
                {n.source_type === 'auto' && <span className="flag">auto</span>}
                {n.tweeted && <span className="okflag"> tweetano</span>}</td>
              <td className="fund-src">{NEWS_CAT_HR[n.category] || n.category}
                {n.ticker ? ` · ${n.ticker}` : ''}</td>
              <td>{n.status === 'published'
                ? <span className="okflag">objavljeno</span>
                : <span className="flag">draft</span>}</td>
              <td className="fund-src">{(n.published_at || n.created_at || '').slice(0, 10) || '—'}</td>
              <td style={{ whiteSpace: 'nowrap' }}>
                <button className="pf-logout" onClick={() => onEdit(n)}>uredi</button>{' '}
                {n.status !== 'published'
                  ? <button className="pf-logout" onClick={() => publish(n)}>objavi</button>
                  : <button className="pf-logout" onClick={() => unpublish(n)}>skini u draft</button>}{' '}
                <button className="pf-del" onClick={() => remove(n)}>obriši</button>
              </td>
            </tr>
          ))}
          {!rows.length && <tr><td colSpan={5} className="subnote">nema vijesti</td></tr>}
        </tbody>
      </table>
    </section>
  )
}

/* M62: pregled prijavljenih korisnika (portfelj) — podaci kroz SECURITY
   DEFINER rpc admin_users_overview (SAMA provjerava is_admin; ne-adminu
   vraća 0 redaka). Frontend nikad ne vidi service key. */
function UsersList({ rows, error }) {
  if (error) {
    return <p className="imp-p">Greška pri dohvatu korisnika: {error}. Ako funkcija
      ne postoji, pokreni supabase/migration_admin_users.sql u Supabase SQL editoru.</p>
  }
  const d = (s) => (s ? new Date(s).toLocaleDateString('hr-HR') : '—')
  const now = new Date()
  const thisMonth = rows.filter((r) => {
    const t = r.registered_at && new Date(r.registered_at)
    return t && t.getFullYear() === now.getFullYear() && t.getMonth() === now.getMonth()
  }).length
  const active = rows.filter((r) => r.n_positions > 0).length
  return (
    <section>
      <div className="sec-label">
        Prijavljeni korisnici: {rows.length} · ovaj mjesec: {thisMonth} ·
        s pozicijama u portfelju: {active}
      </div>
      <table>
        <thead>
          <tr><th>Email</th><th>Ime</th><th>Prijava preko</th><th>Registriran</th>
            <th>Zadnja prijava</th><th>Uvjeti</th><th>Portfelja</th><th>Pozicija</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.user_id}>
              <td>{r.email}</td>
              <td>{r.display_name || '—'}</td>
              <td>{r.provider}</td>
              <td>{d(r.registered_at)}</td>
              <td>{d(r.last_sign_in_at)}</td>
              <td>{r.terms_accepted_at ? 'prihvaćeni' : '—'}</td>
              <td className="num">{r.n_portfolios}</td>
              <td className="num">{r.n_positions}</td>
            </tr>
          ))}
          {!rows.length && <tr><td colSpan={8} className="subnote">nema prijavljenih korisnika</td></tr>}
        </tbody>
      </table>
      <p className="subnote">Redoslijed: najnovije registracije prve. Osobni podaci —
        samo za administraciju servisa, ne izvoziti.</p>
    </section>
  )
}

/* M67: pregled newsletter pretplatnika — SECURITY DEFINER rpc
   admin_newsletter_overview (SAMA provjerava is_admin). CSV export za
   slanje (potvrđeni!) — osobni podaci, samo za administraciju servisa. */
function NewsletterList({ rows, error }) {
  if (error) {
    return <p className="imp-p">Greška pri dohvatu pretplatnika: {error}. Ako
      funkcija ne postoji, pokreni supabase/migration_newsletter.sql u
      Supabase SQL editoru (ili db-sync s newsletter_sql=true).</p>
  }
  const d = (s) => (s ? new Date(s).toLocaleDateString('hr-HR') : '—')
  const confirmed = rows.filter((r) => r.status === 'confirmed')
  const pending = rows.filter((r) => r.status === 'pending').length
  const unsub = rows.filter((r) => r.status === 'unsubscribed').length
  const STATUS_HR = { confirmed: 'potvrđen', pending: 'čeka potvrdu', unsubscribed: 'odjavljen' }
  const exportCsv = () => {
    const csv = ['email;jezik;potvrdjen'].concat(confirmed.map(
      (r) => `${r.email};${r.lang};${(r.confirmed_at || '').slice(0, 10)}`)).join('\n')
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    a.download = 'newsletter-potvrdjeni.csv'
    a.click()
    URL.revokeObjectURL(a.href)
  }
  return (
    <section>
      <div className="sec-label">
        Newsletter: {confirmed.length} potvrđenih · {pending} čeka potvrdu ·
        {' '}{unsub} odjavljenih
      </div>
      <div className="cc-btns" style={{ marginBottom: 10 }}>
        <button type="button" className="cc-btn acct-link-btn" onClick={exportCsv}>
          Preuzmi CSV potvrđenih
        </button>
      </div>
      <table>
        <thead>
          <tr><th>Email</th><th>Status</th><th>Jezik</th><th>Izvor</th>
            <th>Prijava</th><th>Potvrda</th><th>Odjava</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{r.email}</td>
              <td>{r.status === 'confirmed'
                ? <span className="okflag">{STATUS_HR[r.status]}</span>
                : <span className="flag">{STATUS_HR[r.status] || r.status}</span>}</td>
              <td>{r.lang}</td>
              <td className="fund-src">{r.source || '—'}</td>
              <td className="fund-src">{d(r.created_at)}</td>
              <td className="fund-src">{d(r.confirmed_at)}</td>
              <td className="fund-src">{d(r.unsubscribed_at)}</td>
            </tr>
          ))}
          {!rows.length && <tr><td colSpan={7} className="subnote">nema prijava</td></tr>}
        </tbody>
      </table>
      <p className="subnote">Newsletter se šalje ISKLJUČIVO potvrđenima
        (double opt-in); svaki mail mora sadržavati link za odjavu
        (/newsletter/odjava?token=…). Odjavljene adrese ostaju kao lista
        isključenja — ne uklanjati ih ručno.</p>
    </section>
  )
}

export default function Admin() {
  const [session, setSession] = useState(null)
  const [isAdmin, setIsAdmin] = useState(undefined) // undefined = provjera traje
  const [posts, setPosts] = useState([])
  const [editing, setEditing] = useState(null) // null | {} (novi) | post
  const [tab, setTab] = useState('blog') // 'blog' | 'vijesti' | 'korisnici' | 'newsletter'
  const [news, setNews] = useState([])
  const [editingNews, setEditingNews] = useState(null)
  const [users, setUsers] = useState([])
  const [usersError, setUsersError] = useState(null)
  const [nl, setNl] = useState([])
  const [nlError, setNlError] = useState(null)

  useEffect(() => {
    document.title = 'Admin · Burzovni list'
    const m = document.createElement('meta')
    m.name = 'robots'; m.content = 'noindex'
    document.head.appendChild(m)
    return () => { document.head.removeChild(m) }
  }, [])

  useEffect(() => {
    if (!supabase) return undefined
    supabase.auth.getSession().then(({ data }) => setSession(data.session))
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s))
    return () => sub.subscription.unsubscribe()
  }, [])

  useEffect(() => {
    if (!session) { setIsAdmin(undefined); return }
    supabase.from('profiles').select('is_admin').eq('id', session.user.id)
      .maybeSingle().then(({ data }) => setIsAdmin(!!data?.is_admin))
  }, [session])

  const load = useCallback(async () => {
    const { data } = await supabase.from('blog_posts')
      .select('*').order('created_at', { ascending: false })
    setPosts(data || [])
  }, [])
  const loadNews = useCallback(async () => {
    const { data } = await supabase.from('news_items')
      .select('*').order('created_at', { ascending: false })
    setNews(data || [])
  }, [])
  const loadUsers = useCallback(async () => {
    const { data, error } = await supabase.rpc('admin_users_overview')
    setUsers(data || [])
    setUsersError(error ? (error.message || String(error)) : null)
  }, [])
  const loadNl = useCallback(async () => {
    const { data, error } = await supabase.rpc('admin_newsletter_overview')
    setNl(data || [])
    setNlError(error ? (error.message || String(error)) : null)
  }, [])
  useEffect(() => {
    if (session && isAdmin) { load(); loadNews(); loadUsers(); loadNl() }
  }, [session, isAdmin, load, loadNews, loadUsers, loadNl])

  let body
  if (!supabase) {
    body = <section><p className="imp-p">Supabase ključevi nisu postavljeni.</p></section>
  } else if (!session) {
    body = <AuthForms />
  } else if (isAdmin === undefined) {
    body = <div className="loading">provjeravam ovlasti…</div>
  } else if (!isAdmin) {
    body = (
      <section>
        <div className="sec-label">Pristup odbijen</div>
        <p className="imp-p">Prijavljeni račun nema administratorske ovlasti.
        Admin se postavlja isključivo SQL-om u Supabase dashboardu
        (profiles.is_admin) — ne kroz sučelje. <a href="/">Natrag na naslovnicu</a>.</p>
      </section>
    )
  } else if (editing !== null) {
    body = <Editor post={editing.id ? editing : null}
      onDone={() => { setEditing(null); load() }} />
  } else if (editingNews !== null) {
    body = <NewsEditor item={editingNews.id ? editingNews : null}
      onDone={() => { setEditingNews(null); loadNews() }} />
  } else {
    body = (
      <>
        <div className="prof-chips" style={{ margin: '8px 0' }}>
          <button className={tab === 'blog' ? 'on' : ''}
            onClick={() => setTab('blog')}>BLOG</button>
          <button className={tab === 'vijesti' ? 'on' : ''}
            onClick={() => setTab('vijesti')}>VIJESTI</button>
          <button className={tab === 'korisnici' ? 'on' : ''}
            onClick={() => setTab('korisnici')}>KORISNICI</button>
          <button className={tab === 'newsletter' ? 'on' : ''}
            onClick={() => setTab('newsletter')}>NEWSLETTER</button>
          {tab === 'blog'
            && <button className="on" onClick={() => setEditing({})}>+ NOVI POST</button>}
          {tab === 'vijesti'
            && <button className="on" onClick={() => setEditingNews({})}>+ NOVA VIJEST</button>}
        </div>
        {tab === 'blog'
          && <PostList posts={posts} onEdit={(p) => setEditing(p)} onRefresh={load} />}
        {tab === 'vijesti'
          && <NewsList items={news} onEdit={(n) => setEditingNews(n)} onRefresh={loadNews} />}
        {tab === 'korisnici'
          && <UsersList rows={users} error={usersError} />}
        {tab === 'newsletter'
          && <NewsletterList rows={nl} error={nlError} />}
      </>
    )
  }

  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap-wide">
        <div className="mk-title"><h1>Admin</h1></div>
        {body}
      </main>
      <SiteFooter />
    </div>
  )
}
