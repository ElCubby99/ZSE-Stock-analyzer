import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// /api ide na python -m src.webapi (port 8001) u razvoju;
// u produkciji webapi servira i ovaj build (frontend/dist).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://127.0.0.1:8001' },
  },
})
