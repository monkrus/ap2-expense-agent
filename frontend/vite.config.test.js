import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vitest configuration for unit tests
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    css: true,
    // Only include test files in src/ directory
    include: ['src/**/*.{test,spec}.{js,jsx}'],
    // Exclude Playwright E2E tests
    exclude: ['node_modules', 'dist', 'tests/**/*.spec.js', 'e2e/**/*.spec.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.test.{js,jsx}',
        '**/*.spec.{js,jsx}',
        '**/dist/',
      ],
    },
  },
});
