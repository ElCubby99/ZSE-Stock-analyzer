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
import { PolitikaKolacica, PolitikaPrivatnosti, UvjetiKoristenja } from './Legal.jsx'
import { ConsentProvider, pushEvent } from './consent.jsx'
import { SiteFooter, SiteHeader } from './Shell.jsx'
import AuthCallback from './AuthCallback.jsx'
import { initAuthEvents } from './authEvents.js'
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

const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      { path: '/', element: <Trziste /> },
      { path: '/screener', element: <Screener /> },
      { path: '/portfelj', element: <Portfelj /> },
      { path: '/dionica/:ticker', element: <StockPage /> },
      { path: '/blog', element: <BlogIndex /> },
      { path: '/blog/:slug', element: <BlogPost /> },
      { path: '/alati', element: <Alati /> },
      { path: '/metodologija', element: <Metodologija /> },
      { path: '/impressum', element: <Impressum /> },
      { path: '/dividende', element: <Dividende /> },
      { path: '/auth/callback', element: <AuthCallback /> },
      { path: '/politika-kolacica', element: <PolitikaKolacica /> },
      { path: '/uvjeti-koristenja', element: <UvjetiKoristenja /> },
      { path: '/politika-privatnosti', element: <PolitikaPrivatnosti /> },
      { path: '*', element: <NotFound /> },
    ],
  },
])

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConsentProvider>
      <RouterProvider router={router} />
    </ConsentProvider>
  </React.StrictMode>,
)
