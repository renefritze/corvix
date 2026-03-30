# Preact SPA Frontend Rewrite Plan

## 1. Project Setup (Vite + Preact + TypeScript)

Create a `frontend/` directory at the project root:

```bash
mkdir frontend && cd frontend
npm init -y
npm install preact
npm install -D vite @preact/preset-vite typescript
```

**`frontend/vite.config.ts`** — output built assets to `../src/corvix/web/static/`:

```ts
import { defineConfig } from "vite";
import preact from "@preact/preset-vite";

export default defineConfig({
  plugins: [preact()],
  build: {
    outDir: "../src/corvix/web/static",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: "assets/app.js",
        assetFileNames: "assets/[name][extname]",
      },
    },
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
```

**`frontend/tsconfig.json`** — standard Preact TypeScript config:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "jsxImportSource": "preact",
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true,
    "paths": {
      "react": ["./node_modules/preact/compat/"],
      "react-dom": ["./node_modules/preact/compat/"]
    }
  },
  "include": ["src"]
}
```

The Vite dev server proxy at `/api` allows running `npm run dev` in `frontend/` while the Litestar backend runs on port 8000.

---

## 2. Frontend Directory Structure

```
frontend/
  package.json
  tsconfig.json
  vite.config.ts
  index.html                  # Vite entry HTML
  src/
    main.tsx                  # Preact render entry point
    app.tsx                   # Root <App /> component
    api.ts                    # fetch wrappers
    types.ts                  # Shared type definitions
    hooks/
      useSnapshot.ts          # Data fetching + auto-refresh
      useDismiss.ts           # Dismiss-with-undo logic
      useKeyboard.ts          # Global keyboard shortcuts
      useFilters.ts           # Filter state management
      useSort.ts              # Column sort state
    components/
      Toolbar.tsx             # App name + dashboard select + refresh + inline stats
      FilterBar.tsx           # Inline filter controls
      NotificationTable.tsx   # Main data table
      TableHeader.tsx         # Sortable column headers
      TableRow.tsx            # Single notification row
      UndoToast.tsx           # Fixed-position undo notification
      EmptyState.tsx          # Zero-results / error panels
      LoadingSkeleton.tsx     # Table skeleton placeholder
    styles/
      app.css                 # Single global stylesheet
```

---

## 3. Component Architecture

### `<App />`

Root component. Owns top-level state:

```ts
interface AppState {
  dashboard: string | null;
  dashboardNames: string[];
  snapshot: SnapshotPayload | null;
  loading: boolean;       // true only for initial load
  refreshing: boolean;    // true during background refreshes
  error: string | null;
}
```

Renders `<Toolbar>`, `<FilterBar>`, `<NotificationTable>` (or `<EmptyState>` / `<LoadingSkeleton>`), and `<UndoToast>`.

### `<Toolbar />`

Props: `dashboardNames`, `currentDashboard`, `onDashboardChange`, `onRefresh`, `refreshing`, `summary`.

Single compact row (~44px): app name on the left, inline stats strip in the middle (`142 notifications, 89 unread, 23 repos` as plain text separated by dots), dashboard `<select>` + refresh button on the right.

### `<FilterBar />`

Props: `filters`, `filterOptions`, `onFilterChange`, `onClearFilters`.

Slim row (~40px): three `<select>` elements (unread state, reason, repository) + clear button + snapshot timestamp on the right.

### `<NotificationTable />`

Props: `groups`, `sortColumn`, `sortDirection`, `onSort`, `onDismiss`, `pendingDismissals`.

Renders a `<table>` with `<TableHeader>` and maps over groups — a group-name sub-header row (full `colspan`) followed by `<TableRow>` for each item.

### `<TableHeader />`

Props: `sortColumn`, `sortDirection`, `onSort`.

Renders `<thead>` with clickable column headers and sort arrow indicators.

### `<TableRow />`

Props: `item`, `onDismiss`, `isPendingDismissal`.

Renders a `<tr>` with: unread dot, truncated linked title, repository, subject type, reason, right-aligned mono score, relative time, dismiss icon button. Row has `tabindex="0"`. Unread rows get a subtle left-border highlight.

### `<UndoToast />`

Props: `pendingDismissals`, `onUndo`.

Fixed bottom-right toast. Shows when there are pending dismissals.

### `<EmptyState />`

Props: `hasFilters`, `totalItems`, `onClearFilters`, `onRetry`.

Contextual empty/error messaging.

### `<LoadingSkeleton />`

Renders a fake table with 8-10 shimmer rows matching the real column layout.

---

## 4. Data Fetching Layer

### `types.ts`

```ts
export interface DashboardItem {
  thread_id: string;
  repository: string;
  reason: string;
  subject_type: string;
  subject_title: string;
  unread: boolean;
  updated_at: string;
  score: number;
  web_url: string | null;
  matched_rules: string[];
  actions_taken: string[];
}

export interface DashboardGroup {
  name: string;
  items: DashboardItem[];
}

export interface DashboardSummary {
  unread_items: number;
  read_items: number;
  group_count: number;
  repository_count: number;
  reason_count: number;
}

export interface SnapshotPayload {
  name: string;
  generated_at: string | null;
  groups: DashboardGroup[];
  total_items: number;
  summary: DashboardSummary;
  dashboard_names: string[];
}

export type SortColumn = "subject_title" | "repository" | "subject_type" | "reason" | "score" | "updated_at";
export type SortDirection = "asc" | "desc";

export interface FilterState {
  unread: "all" | "unread" | "read";
  reason: string;
  repository: string;
}
```

### `api.ts`

Two functions, no changes to backend endpoints:

- `fetchSnapshot(dashboard?: string): Promise<SnapshotPayload>` — `GET /api/snapshot`
- `dismissNotification(threadId: string): Promise<void>` — `POST /api/notifications/{thread_id}/dismiss`

---

## 5. Table Component Design

### Columns

| # | Column | Width | Content | Sortable |
|---|--------|-------|---------|----------|
| 1 | Status | 28px fixed | 6px dot: green=unread, dim gray=read | No |
| 2 | Title | flex-grow (min 200px) | `subject_title` linked to `web_url`, truncated with ellipsis | Yes |
| 3 | Repository | ~180px | `owner/repo`, truncate if needed | Yes |
| 4 | Type | ~90px | `subject_type` | Yes |
| 5 | Reason | ~100px | `reason` | Yes |
| 6 | Score | ~70px right-aligned | `score` to 1 decimal, mono font | Yes |
| 7 | Updated | ~110px | Relative time, title attr with full timestamp | Yes |
| 8 | Actions | 36px fixed | Dismiss icon button (X or trash SVG) | No |

### Behavior

- Click column header to sort ascending; click again to reverse. Active column gets arrow indicator.
- Default sort: score descending.
- Sorting is purely client-side.
- Group sub-headers: full-width `<tr>` spanning all columns with group name + count, slightly different background.
- Row height target: 36-40px (`padding: 6px 12px`, `font-size: 0.875rem`, `line-height: 1.25`).
- Rows are focusable (`tabindex="0"`), hoverable with subtle highlight.

---

## 6. Filter/Toolbar Design

Two slim rows replacing the massive current header:

**Row 1 (Toolbar, ~44px)**: `Corvix` label (small) | inline stats | dashboard `<select>` | refresh button.

**Row 2 (Filters, ~40px)**: Three `<select>` elements | clear button | snapshot timestamp text.

Both rows share a dark surface background, visually grouped. Stats are plain text, not cards.

Filter options derived from current snapshot items. When a filter value disappears from new data, reset to "all".

---

## 7. Styling Approach

Single `frontend/src/styles/app.css`. No CSS modules, no Tailwind.

Key decisions:
- Preserve existing CSS custom properties (color scheme from `:root`).
- Strip decorative elements: no radial gradients, no backdrop-filter blur, no large border-radius.
- Flat surfaces with 1px borders.
- `border-collapse: collapse`, alternating row backgrounds, sticky `<thead>`.
- Dark body background (`--bg`) without gradient overlays and grid pattern.
- Border radius: 4-6px for containers, 2px for table cells.
- Shimmer animation for skeleton states applied to table rows.
- `prefers-reduced-motion` media query preserved.

**Mobile breakpoint (<768px)**: Hide Type and Reason columns. Below 480px, switch to stacked card-per-row layout via CSS (`<td>` becomes block with `data-label` shown via `::before`).

---

## 8. Keyboard Shortcuts

Implemented in `useKeyboard` hook with a single `document` `keydown` listener.

| Key | Action | Condition |
|-----|--------|-----------|
| `R` | Trigger refresh | Not in input/select/textarea |
| `/` | Focus first filter `<select>` | Always (preventDefault) |
| `D` | Dismiss focused table row | A `<tr>` must have focus |
| `J` | Move focus to next row | Optional enhancement |
| `K` | Move focus to previous row | Optional enhancement |
| `Enter` | Open focused row's GitHub link | A `<tr>` must have focus |
| `Escape` | Blur current element | Always |

---

## 9. Dismiss with Undo Flow

Implemented in `useDismiss` hook:

```ts
interface PendingDismissal {
  threadId: string;
  timerId: number;
  hideTimerId: number;
}
```

Flow (matches current behavior):
1. User clicks dismiss or presses `D` — row gets `opacity: 0` + `pointer-events: none`, then `display: none` after 180ms.
2. `<UndoToast>` appears with 3-second window.
3. Undo within 3s: clear timers, restore row, remove toast, re-focus row.
4. After 3s: call `POST /api/notifications/{thread_id}/dismiss`, then refresh.
5. On API failure: restore row, show error in toolbar area.

Table checks `pending.has(item.thread_id)` to apply dismissal CSS class.

---

## 10. Auto-Refresh Mechanism

Implemented in `useSnapshot` hook:

- 15-second `setInterval`.
- Deduplication of concurrent refreshes via a ref.
- First load: skeleton (`loading=true`).
- Subsequent refreshes: thin 2px animated accent-colored bar at top of page.
- Refresh button gets a spinner icon during refresh (text stays "Refresh").

---

## 11. Backend Changes

Vite build output lands in `src/corvix/web/static/`:

```
src/corvix/web/static/
  index.html
  assets/
    app.js
    app.css
```

### Changes to `app.py`

**Option A (minimal)**: Keep current routes as-is. Vite config produces files at the same paths the backend already serves. No code changes needed.

**Option B (cleaner)**: Replace `app_css` and `app_js` route handlers with Litestar's `StaticFilesConfig`:

```python
from litestar.static_files import StaticFilesConfig

app = Litestar(
    route_handlers=[index, health, api_themes, dashboards, snapshot, dismiss_notification],
    static_files_config=[
        StaticFilesConfig(directories=["corvix/web/static/assets"], path="/assets"),
    ],
)
```

Keep the `index` handler for `/`.

### Other changes

- `tests/test_web.py`: Remove tests checking specific HTML element IDs (Preact renders at runtime). Keep HTML media type test, keep API tests unchanged.
- `MANIFEST.in`: Already covers new output (`recursive-include src/corvix/web/static *`).
- `Dockerfile`: Add multi-stage frontend build:

```dockerfile
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
# ... existing setup ...
COPY --from=frontend /frontend/../src/corvix/web/static /app/src/corvix/web/static
```

---

## 12. Build Integration

### Local development

```bash
# Terminal 1: Litestar backend
CORVIX_CONFIG=corvix.yaml uv run corvix-web

# Terminal 2: Vite dev server with proxy
cd frontend && npm run dev
# Opens localhost:5173, API proxied to localhost:8000
```

### Production build

```bash
cd frontend && npm run build
# Output → src/corvix/web/static/
```

### `package.json` scripts

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview"
  }
}
```

### CI

Add to workflow before Python test step:

```yaml
- uses: actions/setup-node@v4
  with:
    node-version: 22
    cache: npm
    cache-dependency-path: frontend/package-lock.json
- run: cd frontend && npm ci && npm run build
```

### `.gitignore` additions

```
frontend/node_modules/
frontend/dist/
```

Do not commit built files. CI builds them fresh. Include a placeholder `index.html` that says "Run `npm run build` in frontend/" to avoid breaking Python imports.

---

## 13. Migration Steps

### Phase 1: Scaffold (no behavior change)

1. Create `frontend/` with `package.json`, `tsconfig.json`, `vite.config.ts`.
2. Create `frontend/index.html` (minimal: `<div id="app">` + `<script type="module" src="/src/main.tsx">`).
3. Create `frontend/src/main.tsx` rendering placeholder `<App />`.
4. Create `frontend/src/styles/app.css` — copy color variables, write new table-focused styles.
5. Verify `npm run dev` starts and shows placeholder.

### Phase 2: Data layer

6. Create `types.ts` with all TypeScript interfaces.
7. Create `api.ts` with `fetchSnapshot` and `dismissNotification`.
8. Create `hooks/useSnapshot.ts` with auto-refresh.
9. Wire `<App />` to fetch and dump data as JSON to verify API proxy works.

### Phase 3: Table UI

10. Create `<NotificationTable>`, `<TableHeader>`, `<TableRow>`.
11. Create `hooks/useSort.ts`.
12. Create `hooks/useFilters.ts`.
13. Create `<FilterBar>` and `<Toolbar>`.
14. Verify sorting and filtering work.

### Phase 4: Interactions

15. Create `hooks/useDismiss.ts` and `<UndoToast>`.
16. Create `hooks/useKeyboard.ts`.
17. Create `<EmptyState>` and `<LoadingSkeleton>`.
18. Test all keyboard shortcuts.

### Phase 5: Styling polish

19. Finalize `app.css` — responsive breakpoints, row heights, color refinements.
20. Test on mobile viewport sizes.
21. Verify `prefers-reduced-motion` support.

### Phase 6: Backend integration

22. Run `npm run build` and verify output in `src/corvix/web/static/`.
23. Update `app.py` to serve new static files.
24. Delete old static files (replaced by Vite build output).
25. Update `tests/test_web.py`.
26. Update Dockerfile with multi-stage frontend build.
27. Update CI workflow with Node.js build step.
28. Update `.gitignore`.

### Phase 7: Cleanup

29. Remove references to old card-based UI in docs.
30. Document the frontend build process.
31. Test full Docker Compose stack end-to-end.
