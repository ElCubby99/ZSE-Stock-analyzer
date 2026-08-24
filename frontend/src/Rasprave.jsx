import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { supabase } from './supabase.js'
import { useLang } from './i18n/LangContext.jsx'
import { fmtDate } from './format.js'

/* NALOG M30: AI rasprave — 4 agenta + moderator raspravljaju nad podacima
   iz engina; ljudski komentari su odvojeni i moderirani. AI i human postovi
   su NEDVOSMISLENO označeni značkom uz ime (ne u hoveru). Nikad preporuka.
   AI runda dolazi iz statičnih exporta (/data/rasprave/*, SSG); komentari
   su dinamički (Supabase + Edge Function discussion-comment). */

const AGENT_COLOR = {
  ai_value: '#1F6E5A', ai_skeptic: '#9E2B25', ai_macro: '#2F5D86',
  ai_owner: '#8a6d1a', ai_mod: '#262E33',
}

function agentName(agents, id, lang) {
  const a = (agents || []).find((x) => x.id === id)
  if (!a) return id
  return lang === 'en' ? a.display_name_en : a.display_name_hr
}

function Badge({ type }) {
  const { t } = useLang()
  return (
    <span className={`disc-badge ${type}`}>
      {type === 'ai' ? t('disc.badgeAi') : t('disc.badgeHuman')}
    </span>
  )
}

function Citations({ citations }) {
  const { t } = useLang()
  if (!citations || !citations.length) return null
  return (
    <ol className="disc-cits">
      {citations.map((c, i) => (
        <li key={i}>
          {c.label}{c.value ? `: ${c.value}` : ''}
          {c.source_url && <> — <a href={c.source_url}>{t('disc.source')}</a></>}
        </li>
      ))}
    </ol>
  )
}

function AiPost({ post, agents }) {
  const { lang } = useLang()
  const body = (lang === 'en' && post.body_en) ? post.body_en : post.body_hr
  const color = AGENT_COLOR[post.agent_id] || '#262E33'
  return (
    <div className="disc-post ai" style={{ borderLeftColor: color }}>
      <div className="disc-head">
        <Link to={lang === 'en' ? `/en/agent/${post.agent_id}` : `/agent/${post.agent_id}`}
          className="disc-author" style={{ color }}>
          {agentName(agents, post.agent_id, lang)}
        </Link>
        <Badge type="ai" />
      </div>
      <div className="disc-body">{body.split('\n\n').map((par, i) => <p key={i}>{par}</p>)}</div>
      <Citations citations={post.citations} />
    </div>
  )
}

/* ---------- ljudski komentari (dinamički) ---------- */

function Comments({ discussionId }) {
  const { t } = useLang()
  const [session, setSession] = useState(null)
  const [rows, setRows] = useState([])
  const [body, setBody] = useState('')
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!supabase) return undefined
    supabase.auth.getSession().then(({ data }) => setSession(data.session))
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s))
    return () => sub.subscription.unsubscribe()
  }, [])
  const load = () => {
    if (!supabase || !discussionId) return
    supabase.from('discussion_posts')
      .select('id,user_id,body_hr,status,created_at')
      .eq('discussion_id', discussionId).eq('author_type', 'human')
      .order('created_at')
      .then(({ data }) => setRows((data || []).filter((r) => r.status !== 'hidden')))
  }
  useEffect(load, [discussionId, session]) // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async (e) => {
    e.preventDefault()
    if (!body.trim()) return
    setBusy(true); setMsg(null)
    const { data, error } = await supabase.functions.invoke('discussion-comment', {
      body: { discussion_id: discussionId, body: body.trim() },
    })
    setBusy(false)
    if (error || !data?.ok) {
      let detail = ''
      try { detail = (await error?.context?.json())?.error || '' } catch { /* noop */ }
      setMsg({ t: 'err', s: detail || t('disc.cErr') })
      return
    }
    setBody('')
    setMsg({ t: 'ok', s: t('disc.cPending') })
    load()
  }
  const hide = async (r) => {
    await supabase.from('discussion_posts').update({ status: 'hidden' }).eq('id', r.id)
    load()
  }
  const report = async (r) => {
    // prijava zloupotrebe — post ide na admin pregled
    await supabase.from('discussion_posts').update({ status: 'flagged' }).eq('id', r.id)
      .then(() => setMsg({ t: 'ok', s: t('disc.cReported') }))
  }

  return (
    <section>
      <div className="sec-label">{t('disc.commentsH')}</div>
      {rows.length === 0 && <p className="subnote">{t('disc.cNone')}</p>}
      {rows.map((r) => (
        <div key={r.id} className="disc-post human">
          <div className="disc-head">
            <span className="disc-author">{t('disc.readerName')}</span>
            <Badge type="human" />
            <span className="fund-src">{fmtDate(r.created_at.slice(0, 10))}</span>
            {r.status === 'pending' && <span className="flag">{t('disc.cPendingBadge')}</span>}
          </div>
          <div className="disc-body"><p>{r.body_hr}</p></div>
          <div className="disc-actions">
            {session && r.user_id === session.user.id
              && <button type="button" className="pf-logout" onClick={() => hide(r)}>{t('disc.cHide')}</button>}
            <button type="button" className="pf-logout" onClick={() => report(r)}>{t('disc.cReport')}</button>
          </div>
        </div>
      ))}
      {supabase && session ? (
        <form onSubmit={submit} className="disc-form">
          <textarea rows={4} value={body} maxLength={2000}
            placeholder={t('disc.cPlaceholder')}
            onChange={(e) => setBody(e.target.value)} />
          <div className="cc-btns">
            <button type="submit" className="auth-submit" disabled={busy}>{t('disc.cSubmit')}</button>
          </div>
          <p className="nl-note">{t('disc.cRules')}</p>
          {msg && <div className={`auth-msg ${msg.t}`}>{msg.s}</div>}
        </form>
      ) : (
        <p className="imp-p">
          {t('disc.cLoginCta')} <Link to="/portfelj">{t('disc.cLoginLink')}</Link>
        </p>
      )}
    </section>
  )
}

/* ---------- nit rasprave po dionici ---------- */

export function RaspravaPage() {
  const { lang, t } = useLang()
  const { ticker } = useParams()
  const [data, setData] = useState(undefined) // undefined=učitava, null=nema
  useEffect(() => {
    setData(undefined)
    fetch(`/data/rasprave/${String(ticker).toUpperCase()}.json`)
      .then((r) => { if (!r.ok) throw new Error('404'); return r.json() })
      .then(setData).catch(() => setData(null))
  }, [ticker])
  useEffect(() => {
    document.title = `${String(ticker).toUpperCase()} · ${t('disc.tabTitle')} · Burzovni list`
  }, [ticker, t])
  const stockHref = lang === 'en'
    ? `/en/stock/${String(ticker).toLowerCase()}` : `/dionica/${String(ticker).toLowerCase()}`
  const d = data?.discussion
  const agents = data?.agents
  const sum = d && ((lang === 'en' && d.summary_en) ? d.summary_en : d.summary_hr)
  const pick = (o) => ((lang === 'en' && o?.en) ? o.en : (o?.hr ?? o))
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
        <h1 className="page-h1">{t('disc.threadH')} · {String(ticker).toUpperCase()}</h1>
        <p className="imp-p"><Link to={stockHref}>{t('common.backToStock')}</Link></p>
        <div className="disc-disclaimer">{t('disc.disclaimer')}</div>
        <div className="disc-invite">{t('disc.invite')}</div>
        {data === undefined && <div className="loading">{t('common.loading')}</div>}
        {data === null && <p className="imp-p">{t('disc.none')}</p>}
        {d && (
          <>
            <p className="subnote">{t('disc.roundMeta')} {d.round_no} ·{' '}
              {d.published_at ? fmtDate(d.published_at.slice(0, 10)) : ''} ·{' '}
              {t('disc.dataAsOf')} {d.data_snapshot?.as_of || ''}</p>
            {(data.posts || []).map((p) => <AiPost key={p.id} post={p} agents={agents} />)}
            {sum && (
              <section>
                <div className="sec-label">{t('disc.summaryH')}</div>
                <div className="disc-body"><p>{sum}</p></div>
                {d.disagree_points?.length > 0 && (
                  <>
                    <div className="prof-klabel">{t('disc.disagreeH')}</div>
                    <ul className="imp-p">{d.disagree_points.map((x, i) => <li key={i}>{pick(x)}</li>)}</ul>
                  </>
                )}
                {d.questions_for_humans?.length > 0 && (
                  <>
                    <div className="prof-klabel">{t('disc.questionsH')}</div>
                    <ol className="imp-p">{d.questions_for_humans.map((x, i) => <li key={i}>{pick(x)}</li>)}</ol>
                  </>
                )}
              </section>
            )}
            {(data.calls || []).length > 0 && (
              <section>
                <div className="sec-label">{t('disc.callsH')}</div>
                <div className="mk-scroll">
                <table>
                  <thead><tr><th>{t('disc.callAgent')}</th><th>{t('disc.callStance')}</th>
                    <th>{t('disc.callHorizon')}</th><th>{t('disc.callInvalid')}</th></tr></thead>
                  <tbody>
                    {data.calls.map((c, i) => (
                      <tr key={i}>
                        <td>{agentName(agents, c.agent_id, lang)}</td>
                        <td>{t(`disc.stance.${c.stance}`)}</td>
                        <td className="num">{c.horizon_months} {t('disc.months')}</td>
                        <td>{(lang === 'en' && c.invalidation_en) ? c.invalidation_en : c.invalidation_condition}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
                <p className="subnote">{t('disc.callsNote')}</p>
              </section>
            )}
            <Comments discussionId={d.id} />
          </>
        )}
      </main>
      <SiteFooter />
    </div>
  )
}

/* ---------- M75: teaser prema AI Forumu na stranici dionice/fonda ---------- */
/* Prikazuje se SAMO ako za ticker postoji objavljena nit (index.json sadrži
   samo objavljene) — jedan fetch po sesiji, dijeljen između instanci. */
let _forumFeedPromise = null
function loadForumFeed() {
  if (!_forumFeedPromise) {
    _forumFeedPromise = fetch('/data/rasprave/index.json')
      .then((r) => { if (!r.ok) throw new Error('404'); return r.json() })
      .then((d) => d.rows || [])
      .catch(() => [])
  }
  return _forumFeedPromise
}

export function ForumTeaser({ ticker, variant = 'stock' }) {
  const { lang, t } = useLang()
  const [row, setRow] = useState(null)
  useEffect(() => {
    let on = true
    loadForumFeed().then((rows) => {
      if (on) setRow(rows.find((r) => r.ticker === String(ticker).toUpperCase()) || null)
    })
    return () => { on = false }
  }, [ticker])
  if (!row) return null
  const href = row.kind === 'topic'
    ? (lang === 'en' ? `/en/forum/${row.slug}` : `/forum/${row.slug}`)
    : (lang === 'en'
      ? `/en/stock/${String(ticker).toLowerCase()}/discussion`
      : `/dionica/${String(ticker).toLowerCase()}/rasprava`)
  const key = variant === 'etf' ? 'disc.teaserEtf'
    : variant === 'pension' ? 'disc.teaserPension' : 'disc.teaserStock'
  return (
    <div className="disc-teaser">
      <Link to={href}><b>AI Forum</b> · {t(key)} →</Link>
    </div>
  )
}

/* ---------- M72: forumska tema (ETF, mirovinski fondovi) ---------- */

export function TopicPage() {
  const { lang, t } = useLang()
  const { slug } = useParams()
  const [data, setData] = useState(undefined)
  useEffect(() => {
    setData(undefined)
    fetch(`/data/rasprave/topic-${String(slug).toLowerCase()}.json`)
      .then((r) => { if (!r.ok) throw new Error('404'); return r.json() })
      .then(setData).catch(() => setData(null))
  }, [slug])
  const d = data?.discussion
  const title = d ? ((lang === 'en' && d.title_en) ? d.title_en : d.title_hr) : String(slug)
  useEffect(() => { document.title = `${title} · AI Forum · Burzovni list` }, [title])
  const related = d && ((lang === 'en' && d.related_href_en) ? d.related_href_en : d.related_href)
  const relatedLabel = related && (related.includes('/etf/') || related.includes('/etf-')
    ? t('disc.linkEtf') : t('disc.related'))
  const pick = (o) => ((lang === 'en' && o?.en) ? o.en : (o?.hr ?? o))
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
        <h1 className="page-h1">{t('disc.topicH')} · {title}</h1>
        {related && <p className="imp-p"><Link to={related}>{relatedLabel}</Link></p>}
        <div className="disc-disclaimer">{t('disc.disclaimer')}</div>
        <div className="disc-invite">{t('disc.invite')}</div>
        {data === undefined && <div className="loading">{t('common.loading')}</div>}
        {data === null && (
          <p className="imp-p">{t('disc.topicNone')}{' '}
            <Link to={lang === 'en' ? '/en/discussions' : '/rasprave'}>{t('disc.feedH')}</Link></p>
        )}
        {d && (
          <>
            {(data.posts || []).map((p) => <AiPost key={p.id} post={p} agents={data.agents} />)}
            {d.questions_for_humans?.length > 0 && (
              <section>
                <div className="sec-label">{t('disc.questionsH')}</div>
                <ol className="imp-p">{d.questions_for_humans.map((x, i) => <li key={i}>{pick(x)}</li>)}</ol>
              </section>
            )}
            <Comments discussionId={d.id} />
          </>
        )}
      </main>
      <SiteFooter />
    </div>
  )
}

/* ---------- feed ---------- */

export function RaspraveIndex() {
  const { lang, t } = useLang()
  const [feed, setFeed] = useState(null)
  useEffect(() => {
    fetch('/data/rasprave/index.json').then((r) => r.json())
      .then((d) => setFeed(d.rows || [])).catch(() => setFeed([]))
    document.title = `${t('disc.feedH')} · Burzovni list`
  }, [t])
  const threadHref = (r) => {
    if (r.kind === 'topic') return lang === 'en' ? `/en/forum/${r.slug}` : `/forum/${r.slug}`
    const tk = r.ticker.toLowerCase()
    return lang === 'en' ? `/en/stock/${tk}/discussion` : `/dionica/${tk}/rasprava`
  }
  const relatedHref = (r) => {
    if (r.kind === 'topic') {
      return (lang === 'en' && r.related_href_en) ? r.related_href_en : r.related_href
    }
    const tk = r.ticker.toLowerCase()
    return lang === 'en' ? `/en/stock/${tk}` : `/dionica/${tk}`
  }
  const relatedLabel = (r) => {
    if (r.kind !== 'topic') return t('disc.linkStock')
    return (r.related_href || '').includes('/etf/') ? t('disc.linkEtf') : t('disc.related')
  }
  const pick = (o) => ((lang === 'en' && o?.en) ? o.en : (o?.hr ?? o))
  const rows = feed || []
  const groups = [
    { key: 'stocks', label: t('disc.groupStocks'), rows: rows.filter((r) => r.kind !== 'topic') },
    { key: 'etfs', label: t('disc.groupEtfs'), rows: rows.filter((r) => r.kind === 'topic' && (r.related_href || '').includes('/etf/')) },
    { key: 'topics', label: t('disc.groupTopics'), rows: rows.filter((r) => r.kind === 'topic' && !(r.related_href || '').includes('/etf/')) },
  ].filter((g) => g.rows.length)
  const card = (r) => (
    <div key={`${r.kind || 'r'}-${r.ticker}-${r.round_no}`} className="blog-card disc-card">
      <div className="blog-meta">{r.ticker} · {t('disc.roundMeta')} {r.round_no}
        {r.published_at ? ` · ${fmtDate(r.published_at.slice(0, 10))}` : ''}</div>
      <div className="blog-title">
        <Link to={threadHref(r)}>
          {r.kind === 'topic'
            ? pick({ hr: r.title_hr, en: r.title_en }) || r.ticker
            : `${t('disc.threadH')} · ${r.name || r.ticker}`}
        </Link>
      </div>
      {r.teaser && <div className="blog-sum">{t('disc.disagreeH')}: {pick(r.teaser)}</div>}
      <div className="disc-card-links">
        <Link to={threadHref(r)}>{t('disc.openThread')}</Link>
        {relatedHref(r) && <>{' · '}<Link to={relatedHref(r)}>{relatedLabel(r)}</Link></>}
      </div>
    </div>
  )
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
        <h1 className="page-h1">{t('disc.feedH')}</h1>
        <div className="disc-disclaimer">{t('disc.disclaimer')}</div>
        <p className="imp-p">{t('disc.feedLead')}</p>
        <div className="disc-invite">{t('disc.invite')}</div>
        <section>
          <div className="sec-label">{t('disc.agentsH')}</div>
          <ul className="imp-p">
            {['ai_value', 'ai_skeptic', 'ai_macro', 'ai_owner', 'ai_mod'].map((id) => (
              <li key={id}>
                <Link to={lang === 'en' ? `/en/agent/${id}` : `/agent/${id}`}
                  style={{ color: AGENT_COLOR[id], fontWeight: 600 }}>
                  {t(`disc.agent.${id}`)}
                </Link>{' — '}{t(`disc.agentBio.${id}`)}
              </li>
            ))}
          </ul>
        </section>
        {feed === null && <div className="loading">{t('common.loading')}</div>}
        {feed !== null && !rows.length && (
          <section>
            <div className="sec-label">{t('disc.latestH')}</div>
            <p className="imp-p">{t('disc.feedEmpty')}</p>
          </section>
        )}
        {groups.map((g) => (
          <section key={g.key}>
            <div className="sec-label">{g.label}</div>
            {g.rows.map(card)}
          </section>
        ))}
      </main>
      <SiteFooter />
    </div>
  )
}

/* ---------- profil agenta ---------- */

export function AgentPage() {
  const { lang, t } = useLang()
  const { id } = useParams()
  const [agents, setAgents] = useState(null)
  useEffect(() => {
    fetch('/data/agenti.json').then((r) => r.json())
      .then((d) => setAgents(d.rows || [])).catch(() => setAgents([]))
  }, [])
  const a = (agents || []).find((x) => x.id === id)
  useEffect(() => {
    if (a) document.title = `${lang === 'en' ? a.display_name_en : a.display_name_hr} · Burzovni list`
  }, [a, lang])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
        {agents === null && <div className="loading">{t('common.loading')}</div>}
        {agents !== null && !a && <p className="imp-p">{t('disc.agentNone')}</p>}
        {a && (
          <>
            <h1 className="page-h1" style={{ color: AGENT_COLOR[a.id] || '#262E33' }}>
              {lang === 'en' ? a.display_name_en : a.display_name_hr}
              {' '}<Badge type="ai" />
            </h1>
            <section>
              <div className="sec-label">{t('disc.agentAboutH')}</div>
              <p className="imp-p">{lang === 'en' ? a.bio_en : a.bio_hr}</p>
              <p className="subnote">{t('disc.agentModel')}: <code>{a.model}</code></p>
            </section>
            <section>
              <div className="sec-label">{t('disc.agentPromptH')}</div>
              <p className="imp-p fund-src">{a.role_prompt}</p>
            </section>
            <section>
              <div className="sec-label">{t('disc.trackH')}</div>
              <p className="imp-p">{t('disc.trackPlaceholder')}</p>
            </section>
            <div className="disc-disclaimer">{t('disc.disclaimer')}</div>
          </>
        )}
      </main>
      <SiteFooter />
    </div>
  )
}
