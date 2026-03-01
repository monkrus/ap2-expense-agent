import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTarget = process.env.VITE_PROXY_TARGET || env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [react()],
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['src/test/setup.js'],
      include: ['src/**/*.{test,spec}.{js,jsx}'],
      exclude: ['node_modules', 'dist', 'tests/**', 'e2e/**'],
    },
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
          secure: false
        }
      }
    },
    build: {
      chunkSizeWarningLimit: 600,
      rollupOptions: {
        output: {
          manualChunks: {
            // Heavy export libs loaded only when export dialog opens
            'vendor-excel': ['exceljs'],
            'vendor-pdf': ['jspdf', 'jspdf-autotable'],
            // Charting library
            'vendor-charts': ['recharts', 'react-is'],
            // React core — cached long-term by browsers
            'vendor-react': ['react', 'react-dom'],
            // Icon library
            'vendor-icons': ['lucide-react'],
          }
        }
      }
    }
  }
})
