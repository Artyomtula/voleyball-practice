import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Запросы /api проксируются на FastAPI, поэтому фронтенду не нужен CORS
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": process.env.API_URL || "http://localhost:8000",
    },
  },
});
