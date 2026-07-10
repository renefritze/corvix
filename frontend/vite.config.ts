import { defineConfig } from "vitest/config";
import preact from "@preact/preset-vite";

export default defineConfig(({ mode }) => ({
  plugins: mode === "test" ? [] : [preact()],
  // Pin the JSX runtime to Preact for Vite's built-in (oxc) transform. In test
  // mode the preact preset is not loaded, and the *.test.tsx files are excluded
  // from tsconfig.json, so the transform would otherwise default to React and
  // emit an unresolvable `react/jsx-dev-runtime` import (regressed by Vite 8.1's
  // oxc JSX handling honouring tsconfig include/exclude).
  oxc: {
    jsx: {
      runtime: "automatic",
      importSource: "preact",
    },
  },
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
    // Inline preact-router so it is transformed by Vite and shares the same
    // (ESM) preact instance as the components under test; otherwise its CJS
    // build pulls a separate preact copy and <Router> renders nothing.
    server: {
      deps: {
        inline: ["preact-router"],
      },
    },
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
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
