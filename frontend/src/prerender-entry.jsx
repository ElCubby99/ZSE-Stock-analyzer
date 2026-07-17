/* M33: SSR ulaz za prerender — renderira ISTE React content komponente
   pravnih stranica u statički HTML (jedan izvor teksta, bez dupliranja).
   Builda se kao vite SSR bundle (vidi package.json "build") i uvozi iz
   scripts/prerender.mjs. Bez hookova/window pristupa u content komponentama. */
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { StaticRouter } from 'react-router-dom/server'
import { ImpressumContent } from './Impressum.jsx'
import {
  EnCookiesContent, EnPrivacyContent, EnTermsContent,
  PolitikaKolacicaContent, PolitikaPrivatnostiContent, UvjetiKoristenjaContent,
} from './Legal.jsx'

const CONTENT = {
  '/impressum': ImpressumContent,
  '/uvjeti-koristenja': UvjetiKoristenjaContent,
  '/politika-privatnosti': PolitikaPrivatnostiContent,
  '/politika-kolacica': PolitikaKolacicaContent,
  // M38: engleske pravne stranice (pun prijevod + prevails klauzula)
  '/en/terms': EnTermsContent,
  '/en/privacy': EnPrivacyContent,
  '/en/cookies': EnCookiesContent,
}

export function renderStatic(route) {
  const C = CONTENT[route]
  if (!C) return null
  return renderToStaticMarkup(
    <StaticRouter location={route}>
      <C />
    </StaticRouter>,
  )
}
