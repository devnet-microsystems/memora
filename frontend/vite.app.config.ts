import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  configFile: false,
  root: __dirname,
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
