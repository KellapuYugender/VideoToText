import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const backend = 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // The browser talks only to Vite; API calls and the WebSocket go through to Django.
    proxy: {
      '/api': backend,
      '/ws': { target: backend, ws: true },
    },
  },
})
