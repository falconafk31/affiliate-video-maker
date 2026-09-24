import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: true, // bind 0.0.0.0 agar bisa diakses dari luar container/preview
    allowedHosts: true, // izinkan semua host (preview proxy / LAN lokal)
    proxy: {
      // Dev: semua panggilan "/api/..." diteruskan ke backend lokal
      // (frontend memakai URL relatif — tanpa hardcode host/port backend)
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:9000',
        changeOrigin: true,
        // SSE (EventSource /api/jobs/{id}/stream) butuh streaming tanpa buffering
        ws: false,
        compress: false,
      },
    },
  },
})
