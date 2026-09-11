import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // Bind IPv4 loopback explicitly: Node >=17 otherwise resolves `localhost`
  // to ::1 only, leaving 127.0.0.1:5173 (dev.py's health check) refused.
  server: { port: 5173, host: '127.0.0.1' },
});
