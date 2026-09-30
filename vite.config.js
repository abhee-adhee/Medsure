import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/scan': 'http://localhost:8000',
      '/scans': 'http://localhost:8000',
      '/demo': 'http://localhost:8000',
      '/alerts': 'http://localhost:8000',
      '/stats': 'http://localhost:8000',
      '/receiving': 'http://localhost:8000',
      '/batch-report': 'http://localhost:8000'
    }
  }
})
