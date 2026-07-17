import React, { createContext, useContext, useEffect, useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import { setLocale } from '../format.js'
import { t as translate } from './strings.mjs'

/* M38: jezik se određuje ISKLJUČIVO iz rute (/en/... -> 'en'); nema IP
   auto-redirecta. Izbor se pamti u localStorage (bl_lang) samo kao
   preferencija za switcher/povratke — root ostaje HR. */

const LangCtx = createContext({ lang: 'hr', t: (k) => translate(k, 'hr') })

export function langFromPath(pathname) {
  return pathname === '/en' || String(pathname).startsWith('/en/') ? 'en' : 'hr'
}

export function LangProvider({ children }) {
  const { pathname } = useLocation()
  const lang = langFromPath(pathname)
  setLocale(lang) // formatteri (num/eur/pct/datum) prate jezik rute
  useEffect(() => {
    try { localStorage.setItem('bl_lang', lang) } catch { /* bez pohrane */ }
    document.documentElement.lang = lang
  }, [lang])
  const value = useMemo(() => ({ lang, t: (k) => translate(k, lang) }), [lang])
  return <LangCtx.Provider value={value}>{children}</LangCtx.Provider>
}

export function useLang() {
  return useContext(LangCtx)
}
