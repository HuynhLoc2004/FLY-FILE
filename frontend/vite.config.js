import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    // Ensure pdfjs-dist (used by react-pdf) worker is bundled correctly by Vite
    include: ['pdfjs-dist/build/pdf.worker.min.mjs'],
  },
})
