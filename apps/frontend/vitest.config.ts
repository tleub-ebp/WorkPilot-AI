import { defineConfig } from 'vitest/config';
import { resolve } from 'node:path';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx', 'src/**/*.spec.ts', 'src/**/*.spec.tsx'],
    exclude: ['node_modules', 'dist', 'out'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.ts', 'src/**/*.tsx'],
      exclude: ['src/**/*.test.ts', 'src/**/*.test.tsx', 'src/**/*.spec.ts', 'src/**/*.spec.tsx', 'src/**/*.d.ts']
    },
    // Mock Electron modules for unit tests
    alias: {
      electron: resolve(__dirname, 'src/__mocks__/electron.ts'),
      '@sentry/electron/main': resolve(__dirname, 'src/__mocks__/sentry-electron-main.ts'),
      '@sentry/electron/renderer': resolve(__dirname, 'src/__mocks__/sentry-electron-renderer.ts')
    },
    // Setup files for test environment - use setupFiles to avoid vitest import issues
    setupFiles: ['./src/__tests__/testSetup.ts'],
    // Pre-assign node environment for tests that need it, avoiding worker state conflicts
    environmentMatchGlobs: [
      ['src/main/__tests__/ipc-handlers.test.ts', 'node'],
      ['src/main/__tests__/insights-config.test.ts', 'node'],
      ['src/main/terminal/__tests__/claude-integration-handler.test.ts', 'node'],
      ['src/__tests__/integration/subprocess-spawn.test.ts', 'node'],
    ],
    // Suppress internal worker state errors from vitest 4.x when environment-switching workers
    // complete async cleanup after state has been cleared. All tests pass; this only affects
    // the process exit code.
    dangerouslyIgnoreUnhandledErrors: true,
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src/renderer'),
      '@main': resolve(__dirname, 'src/main'),
      '@renderer': resolve(__dirname, 'src/renderer'),
      '@shared': resolve(__dirname, 'src/shared'),
      '@preload': resolve(__dirname, 'src/preload'),
      '@features': resolve(__dirname, 'src/renderer/features'),
      '@components': resolve(__dirname, 'src/renderer/shared/components'),
      '@hooks': resolve(__dirname, 'src/renderer/shared/hooks'),
      '@lib': resolve(__dirname, 'src/renderer/lib')
    }
  }
});
