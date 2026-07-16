import React, { useEffect, useRef } from 'react'
import { createRoot } from 'react-dom/client'
import {
  createBrowserRouter, Link, Outlet, RouterProvider, useLocation,
} from 'react-router-dom'
import StockPage from './StockPage.jsx'
import Alati from './Alati.jsx'
import Trziste from './Trziste.jsx'
import Screener from './Screener.jsx'
import Portfelj from './Portfelj.jsx'
import { BlogIndex, BlogPost } from './Blog.jsx'
import Metodologija from './Metodologija.jsx'
import Impressum from './Impressum.jsx'
import Dividende from './Dividende.jsx'
import Usporedba from './Usporedba.jsx'
import { VijestDetail, VijestiIndex } from './Vijesti.jsx'
import { IndeksDetail, IndeksiIndex } from './Indeksi.jsx'
import { ObveznicaDetail, ObvezniceIndex } from './Obveznice.jsx'
import Admin from './Admin.jsx'
import { PolitikaKolacica, PolitikaPrivatnosti, UvjetiKoristenja } from './Legal.jsx'
import { ConsentProvider, pushEvent } from './consent.jsx'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import AuthCallback from './AuthCallback.jsx'
import { initAuthEvents } from './authEvents.js'
import { ROUTES } from './routes/registry.mjs'
import './styles.css'

initAuthEvents() // globalni sign_up/login eventi (method po provideru)

/* M25: SPA page_view — GA4 tag u GTM-u vidi samo prvi load; svaku promjenu
   rute pushamo kao 'spa_page_view' (GTM trigger + GA4 page_view tag je
   Borisov ručni korak, vidi README). Prvi load se NE puša (broji ga GTM). */
function RootLayout() {
  const loc = useLocation()
  const first = useRef(true)
  useEffect(() => {
    if (first.current) { first.current = false; return }
    pushEvent('spa_page_view', {
      page_path: loc.pathname,
      page_title: document.title,
    })
  }, [loc.pathname])
  return <Outlet />
}

/* SEO higijena: vlastita 404 s linkom na popis dionica (bez redirecta na /) */
function NotFound() {
  useEffect(() => { document.title = 'Stranica nije pronađena · Burzovni list' }, [])
  return (
    <div className="shellpg">
      <SiteHeader />
      <main className="wrap">
        <h1 className="page-h1">404 — stranica nije pronađena</h1>
        <section>
          <p className="imp-p">Tražena stranica ne postoji ili je premještena.
          Možda tražite <Link to="/">popis svih dionica</Link>,{' '}
          <Link to="/dividende">kalendar dividendi</Link> ili{' '}
          <Link to="/screener">screener</Link>?</p>
        </section>
      </main>
      <SiteFooter />
    </div>
  )
}

/* Rute se grade ISKLJUČIVO iz src/routes/registry.mjs (jedan izvor istine za
   router, prerender i sitemap). Nova stranica: unos u registry + komponenta
   ovdje u COMPONENTS mapi — nikad hardkodiran path u ovom fajlu. */
const COMPONENTS = {
  Trziste: <Trziste />,
  Screener: <Screener />,
  Portfelj: <Portfelj />,
  StockPage: <StockPage />,
  BlogIndex: <BlogIndex />,
  BlogPost: <BlogPost />,
  Alati: <Alati />,
  Metodologija: <Metodologija />,
  Impressum: <Impressum />,
  Dividende: <Dividende />,
  Usporedba: <Usporedba />,
  VijestiIndex: <VijestiIndex />,
  IndeksiIndex: <IndeksiIndex />,
  IndeksDetail: <IndeksDetail />,
  ObvezniceIndex: <ObvezniceIndex />,
  ObveznicaDetail: <ObveznicaDetail />,
  VijestDetail: <VijestDetail />,
  AuthCallback: <AuthCallback />,
  Admin: <Admin />,
  PolitikaKolacica: <PolitikaKolacica />,
  UvjetiKoristenja: <UvjetiKoristenja />,
  PolitikaPrivatnosti: <PolitikaPrivatnosti />,
}

const routeChildren = ROUTES.map((r) => {
  if (!COMPONENTS[r.component]) {
    throw new Error(`ruta ${r.path}: komponenta '${r.component}' nije u COMPONENTS mapi (main.jsx)`)
  }
  return { path: r.path, element: COMPONENTS[r.component] }
})

const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [...routeChildren, { path: '*', element: <NotFound /> }],
  },
])

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConsentProvider>
      <RouterProvider router={router} />
    </ConsentProvider>
  </React.StrictMode>,
)
