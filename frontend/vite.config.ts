import path from "node:path"
import { defineConfig } from "vitest/config"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    globals: true,
  },
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "./src") } },
  server: {
    port: 5173,
    // The API is same-origin in production behind nginx; mirror that in dev so
    // no base URL ever has to be configured in the client. Target 127.0.0.1
    // rather than localhost: Node resolves localhost to ::1 first, which lands
    // on a different service when one is already bound to the IPv6 port.
    proxy: {
      "/api": {
        target: process.env.DOCUSCOPE_API_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
})
