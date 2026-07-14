import React from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import StockPage from './StockPage.jsx'
import Alati from './Alati.jsx'
import Trziste from './Trziste.jsx'
import Screener from './Screener.jsx'
import Portfelj from './Portfelj.jsx'
import { BlogIndex, BlogPost } from './Blog.jsx'
import Metodologija from './Metodologija.jsx'
import Impressum from './Impressum.jsx'
import './styles.css'

const router = createBrowserRouter([
  { path: '/', element: <Trziste /> },
  { path: '/screener', element: <Screener /> },
  { path: '/portfelj', element: <Portfelj /> },
  { path: '/dionica/:ticker', element: <StockPage /> },
  { path: '/blog', element: <BlogIndex /> },
  { path: '/blog/:slug', element: <BlogPost /> },
  { path: '/alati', element: <Alati /> },
  { path: '/metodologija', element: <Metodologija /> },
  { path: '/impressum', element: <Impressum /> },
  { path: '*', element: <Navigate to="/" replace /> },
])

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
)
