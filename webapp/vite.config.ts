import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  base: "/app/",
  build: { target: "es2022" },
  plugins: [react()],
  server: { proxy: { "/api": { target: "http://localhost:8080", ws: true } } },
});
