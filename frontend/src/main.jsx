import React from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import StockPage from './StockPage.jsx'
import Alati from './Alati.jsx'
import { BlogIndex, BlogPost } from './Blog.jsx'
import './styles.css'

const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/dionica/ADRS" replace /> },
  { path: '/dionica/:ticker', element: <StockPage /> },
  { path: '/blog', element: <BlogIndex /> },
  { path: '/blog/:slug', element: <BlogPost /> },
  { path: '/alati', element: <Alati /> },
  { path: '*', element: <Navigate to="/dionica/ADRS" replace /> },
])

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
)
