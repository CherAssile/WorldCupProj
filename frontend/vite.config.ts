/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  // Le vrai .env (VITE_API_URL, etc.) vit à la racine du repo, partagé avec
  // docker-compose et le backend — pas de duplication dans frontend/.
  envDir: path.resolve(import.meta.dirname, ".."),
  server: {
    host: true,
    port: 5173,
    watch: {
      usePolling: true,
    },
  },
  test: {
    environment: "jsdom",
  },
});
