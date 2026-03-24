import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { config as dotenvConfig } from 'dotenv';
import { resolve } from 'node:path';

dotenvConfig({ path: resolve(__dirname, '../../.env-files/.env') });

const backendUrl = process.env.VITE_BACKEND_URL || 'http://localhost:9000';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src/renderer'),
      '@shared': resolve(__dirname, 'src/shared'),
      '@preload': resolve(__dirname, 'src/preload'),
      '@features': resolve(__dirname, 'src/renderer/features'),
      '@components': resolve(__dirname, 'src/renderer/shared/components'),
      '@hooks': resolve(__dirname, 'src/renderer/shared/hooks'),
      '@lib': resolve(__dirname, 'src/renderer/lib'),
    },
  },
  server: {
    proxy: {
      '/providers': {
        target: backendUrl,
        changeOrigin: true,
      },
      '/providers/': {
        target: backendUrl,
        changeOrigin: true,
      },
      '/api': backendUrl,
      '/api/': backendUrl,
      '/projects': backendUrl,
      '/projects/': backendUrl,
      '/tasks': backendUrl,
      '/tasks/': backendUrl,
      '/analytics': {
        target: backendUrl,
        changeOrigin: true,
      },
      // Ajoutez ici d'autres routes API nécessaires
    },
  },
});