import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // VITE_* values live in the repo-root .env, next to the rest of the project config.
  envDir: '../..',
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
})
