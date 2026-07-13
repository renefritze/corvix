/// <reference types="vitest/config" />
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { svelteTesting } from "@testing-library/svelte/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vitest/config";

export default defineConfig(({ mode }) => ({
  plugins: [
    svelte(),
    tailwindcss(),
    ...(mode === "test" ? [svelteTesting()] : []),
  ],
  build: {
    outDir: "../src/corvix/web/static/assets",
    emptyOutDir: true,
    cssCodeSplit: false,
    minify: "terser",
    terserOptions: {
      compress: {
        module: true,
        toplevel: true,
        passes: 2,
      },
      mangle: {
        module: true,
        toplevel: true,
      },
      format: {
        comments: false,
      },
    },
    lib: {
      entry: "src/main.ts",
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
    include: ["src/**/*.test.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      include: ["src/**/*.{ts,svelte}"],
      exclude: ["src/main.ts", "src/test/**", "src/api-types.gen.ts"],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
}));
