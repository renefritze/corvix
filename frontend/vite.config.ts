import { defineConfig } from "vitest/config";
import preact from "@preact/preset-vite";

export default defineConfig(({ mode }) => ({
  plugins: mode === "test" ? [] : [preact()],
  build: {
    outDir: "../src/corvix/web/static/assets",
    emptyOutDir: true,
    cssCodeSplit: false,
    lib: {
      entry: "src/main.tsx",
      formats: ["es"],
      fileName: () => "app.js",
      cssFileName: "index",
    },
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/main.tsx", "src/test/**"],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
}));
