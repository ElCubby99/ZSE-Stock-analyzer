import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import { supabase } from './supabase.js'

/* M26 1.1: /auth/callback — povratak s OAuth providera. Code exchange radi
   supabase-js sam (detectSessionInUrl); ovdje čekamo sesiju pa vraćamo
   korisnika na stranicu s koje je login krenuo (bl_return_to). */
export default function AuthCallback() {
  const navigate = useNavigate()
  const [err, setErr] = useState(null)

  useEffect(() => {
    document.title = 'Prijava… · Burzovni list'
    const params = new URLSearchParams(window.location.search)
    if (params.get('error')) {
      setErr(params.get('error_description') || params.get('error'))
      return undefined
    }
    let done = false
    const go = () => {
      if (done) return
      done = true
      let to = '/portfelj'
      try {
        to = sessionStorage.getItem('bl_return_to') || '/portfelj'
        sessionStorage.removeItem('bl_return_to')
      } catch { /* noop */ }
      navigate(to.startsWith('/') ? to : '/portfelj', { replace: true })
    }
    supabase?.auth.getSession().then(({ data }) => { if (data.session) go() })
    const { data: sub } = supabase?.auth.onAuthStateChange((event) => {
      if (event === 'SIGNED_IN') go()
    }) || { data: null }
    const t = setTimeout(() => {
      if (!done) setErr('Prijava nije dovršena — pokušaj ponovno.')
    }, 12000)
    return () => { sub?.subscription?.unsubscribe(); clearTimeout(t) }
  }, [navigate])

  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
        {err ? (
          <section>
            <div className="sec-label">Prijava nije uspjela</div>
            <p className="imp-p">{err}</p>
            <p className="imp-p"><a href="/portfelj">Natrag na prijavu</a></p>
          </section>
        ) : (
          <div className="loading">dovršavam prijavu…</div>
        )}
      </main>
      <SiteFooter />
    </div>
  )
}
