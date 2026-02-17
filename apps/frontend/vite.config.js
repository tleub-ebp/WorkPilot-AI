import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { config as dotenvConfig } from 'dotenv';
import { resolve } from 'path';

dotenvConfig({ path: resolve(__dirname, '../../.env') });

const backendUrl = process.env.VITE_BACKEND_URL || 'http://localhost:9000';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/providers': backendUrl,
      '/providers/': backendUrl,
    },
  },
});