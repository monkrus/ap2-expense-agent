import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Core React libraries
          'vendor-react': ['react', 'react-dom'],

          // Payment/Stripe libraries
          'vendor-stripe': ['@stripe/react-stripe-js', '@stripe/stripe-js'],

          // HTTP client and utilities
          'vendor-utils': ['axios'],

          // UI libraries
          'vendor-ui': ['lucide-react']
        }
      }
    },
    // Set chunk size warning to 1000kb (1MB)
    // Note: ExcelJS is ~940kb but lazy-loaded only when user exports to Excel
    chunkSizeWarningLimit: 1000
  }
})
