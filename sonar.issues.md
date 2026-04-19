# Sonar Issues Plan

Based on `sonar.issues.json`.

## Summary

- Total issues: `121`
- Severity: `2 blocker`, `21 critical`, `36 major`, `62 minor`
- Language split: `76 TypeScript`, `44 Python`, `1 Docker`

## Fix Order

1. Blockers and critical correctness issues
2. Mechanical cleanup with low regression risk
3. Frontend accessibility and readability fixes
4. Backend complexity refactors
5. Final validation and Sonar rerun

## Phase 1: Blockers And Critical Issues

### `tests/e2e/test_dashboard_ui.py`

- `python:S930` at line `159`
- Keep the test logic unchanged.
- Update `tests/e2e/playwright_types.py` so `RouteLike.fulfill()` matches Playwright's actual API.
- Add support for `response=` and for explicit `status` / `content_type` / `body` arguments.

### `frontend/src/hooks/useSnapshot.ts`

- `typescript:S3735` at lines `54`, `63`, `64`
- Remove `void` from `load(...)` calls.
- Keep `load()` error handling and in-flight behavior unchanged.

### `frontend/src/test/setup.ts`

- `typescript:S1186` at lines `6`, `7`, `8`
- Replace empty `ResizeObserverMock` methods with non-empty spy-backed methods or minimal implementations.

### `src/corvix/config.py`

- `python:S1192` at line `118`
- Extract `"https://api.github.com"` into a module constant and reuse it in defaults and parsing.

### `src/corvix/domain.py`

- `python:S3776` at line `127`
- Reduce complexity in `Notification.from_api_payload()` by extracting small validation helpers.
- Preserve current exceptions and behavior.

- `python:S1192` at line `236`
- Extract `"stored record"` into a constant reused by `NotificationRecord.from_dict()`.

### `src/corvix/services.py`

- `python:S3776` at line `71`
- Split `run_poll_cycle()` into small orchestration helpers.
- Keep fetch, enrichment, rule evaluation, persistence, and dispatch behavior unchanged.

### `src/corvix/storage.py`

- `python:S3776` at line `412`
- Refactor `_coerce_context()` by extracting shared string-key dict normalization.

- `python:S1172` at lines `158`, `171`, `188`, `193`
- Keep `user_id` in signatures because it is part of the storage backend contract.
- Mark it intentionally unused inside the JSON-backed methods.

### `src/corvix/ingestion.py`

- `python:S1192` at line `248`
- Extract `"request failed"` into a constant.

### `src/corvix/db.py`

- `python:S1192` at line `45`
- Extract `"users.id"` into a local constant used by all foreign keys.

### `src/corvix/migrations/versions/838399841a57_initial_schema.py`

- `python:S1192` at line `37`
- Add the same `"users.id"` constant locally inside the migration file.

### `tests/e2e/conftest.py`

- `python:S1192` at line `94`
- Extract `"2024-01-01T00:00:00Z"` into a test constant.

### `tests/integration/test_cli.py`

- `python:S1186` at lines `105`, `134`
- Add short comments explaining intentionally empty stub methods, or replace them with minimal non-empty stubs.

## Phase 2: Low-Risk Mechanical Cleanup

### Backend

#### `src/corvix/actions.py`

- `python:S108` at line `12`
- Remove the empty `if TYPE_CHECKING: pass` block.

#### `src/corvix/config.py` (phase 2)

- `python:S7500` at line `338`
- Replace the list comprehension with `list(value)`.

#### `src/corvix/services.py` (phase 2)

- `python:S7500` at line `111`
- Replace the dict comprehension with `dict(clients_by_account)`.

#### `tests/e2e/conftest.py` (phase 2)

- `python:S4144` at line `36`
- Extract the duplicated `do_PATCH()` and `do_DELETE()` handler logic into one helper.

#### `tests/integration/test_web_api.py`

- `python:S7500` at lines `339`, `414`
- Replace generator-throw lambda helpers with a tiny explicit raising function.

#### `docs/conf.py`

- `python:S125` at line `173`
- Remove the commented-out code.

#### `docker/lighthouse.Dockerfile`

- `docker:S7031` at line `6`
- Merge consecutive `RUN` instructions into one.

### Float Comparisons In Tests

#### `tests/unit/test_config.py`

- `python:S1244` at lines `128`, `129`, `166`, `167`, `184`, `186`, `211`, `213`
- Replace direct float equality with `pytest.approx(...)`.

#### `tests/unit/test_dashboarding.py`

- `python:S1244` at line `330`
- Replace direct float equality with `pytest.approx(...)`.

#### `tests/unit/test_scoring.py`

- `python:S1244` at lines `58`, `63`, `72`, `81`, `90`, `99`, `108`, `117`, `126`, `144`
- Replace direct float equality with `pytest.approx(...)`.

- `python:S125` at line `164`
- Remove the commented-out code-like note.

## Phase 3: Frontend Mechanical Fixes

### `frontend/src/app.test.tsx`

- `typescript:S4323` at line `61`
- Replace the repeated union type with a type alias.

- `typescript:S6551` at line `65`
- Stop using generic stringification for fetch input.
- Derive the URL explicitly from `string`, `URL`, or `Request`.

- `typescript:S7764` at lines `8`, `97`, `101`, `116`, `141`, `168`, `207`, `220`, `225`, `278`
- Replace bare `window` access with `globalThis` or `globalThis.window`.

### `frontend/src/app.tsx`

- `typescript:S7764` at lines `55`, `58`, `171`, `175`, `186`, `187`, `191`, `203`, `207`, `210`
- Replace `window` references with `globalThis` / `globalThis.window`.

- `typescript:S3358` at lines `270`, `278`
- Replace nested ternary rendering with an explicit branch variable or helper.

- `typescript:S6819` at line `232`
- Replace `role="dialog"` markup with a native `<dialog open>`.

- `typescript:S6772` at lines `240`, `241`
- Make whitespace around `<kbd>` elements explicit with `{" "}`.

### Readonly Props

Mark component props readonly in these files:

- `frontend/src/components/EmptyState.tsx` (`typescript:S6759`)
- `frontend/src/components/FilterBar.tsx` (`typescript:S6759`)
- `frontend/src/components/NotificationTable.tsx` (`typescript:S6759`)
- `frontend/src/components/TableHeader.tsx` (`typescript:S6759`)
- `frontend/src/components/TableRow.tsx` (`typescript:S6759`)
- `frontend/src/components/Toolbar.tsx` (`typescript:S6759`)
- `frontend/src/components/UndoToast.tsx` (`typescript:S6759`)
- `frontend/src/hooks/useBrowserNotifications.test.tsx` (`typescript:S6759`)
- `frontend/src/hooks/useDismiss.test.tsx` (`typescript:S6759`)
- `frontend/src/hooks/useKeyboard.test.tsx` (`typescript:S6759`)
- `frontend/src/hooks/useSnapshot.test.tsx` (`typescript:S6759`)
- `frontend/src/hooks/useSort.test.tsx` (`typescript:S6759`)

### `frontend/src/components/FilterBar.tsx`

- `typescript:S2871` at lines `25`, `28`
- Replace `.sort()` with `localeCompare` sorting.

### `frontend/src/components/NotificationTable.tsx`

- `typescript:S4325` at lines `18`, `19`
- Remove unnecessary type assertions in `sortItems()`.

### `frontend/src/hooks/useBrowserNotifications.test.tsx`

- `typescript:S1444` at lines `8`, `9`, `10`
- Make static members readonly where possible.

- `typescript:S1186` at line `26`
- Replace empty `close()` with a non-empty spy-backed method.

- `typescript:S7764` at line `66`
- Replace `window` with `globalThis`.

### `frontend/src/hooks/useBrowserNotifications.ts`

- `typescript:S7764` at line `77`
- Replace `window` usage with `globalThis.window` or `globalThis`.

### `frontend/src/hooks/useColumnResize.test.tsx`

- `typescript:S7764` at lines `32`, `37`, `48`
- Replace `window` event dispatches with `globalThis`.

### `frontend/src/hooks/useColumnResize.ts`

- `typescript:S7764` at lines `58`, `59`, `80`, `81`, `93`, `94`, `114`, `116`
- Replace all bare `window` references with `globalThis` / `globalThis.window`.

## Phase 4: Frontend Accessibility And Readability

### `frontend/src/components/TableHeader.tsx`

- `typescript:S3358` at line `87`
- Compute `aria-sort` outside JSX instead of using nested ternaries.

### `frontend/src/components/TableRow.tsx`

- `typescript:S6825` at line `56`
- Remove `aria-hidden="true"` from the focusable status cell.
- Keep the unread dot decorative and expose unread/read state accessibly.

### `frontend/src/hooks/useKeyboard.test.tsx`

- `typescript:S5256` at line `34`
- Add a valid table header row or column to the test fixture.

### `frontend/src/hooks/useKeyboard.ts`

- `typescript:S3358` at line `32`
- Replace the nested ternary computing `nextIndex` with explicit branching.

### `frontend/src/hooks/useSnapshot.test.tsx`

- `typescript:S3735` at line `21`
- Remove `void` from the refresh button handler.

## Full File Checklist

- `docker/lighthouse.Dockerfile`: merge consecutive `RUN`
- `docs/conf.py`: remove commented-out code
- `frontend/src/app.test.tsx`: type alias, explicit input stringification, `globalThis`
- `frontend/src/app.tsx`: `globalThis`, nested ternary removal, native dialog, explicit spacing
- `frontend/src/components/EmptyState.tsx`: readonly props
- `frontend/src/components/FilterBar.tsx`: readonly props, `localeCompare`
- `frontend/src/components/NotificationTable.tsx`: readonly props, remove unnecessary assertions
- `frontend/src/components/TableHeader.tsx`: readonly props, simplify `aria-sort`
- `frontend/src/components/TableRow.tsx`: readonly props, accessible unread state
- `frontend/src/components/Toolbar.tsx`: readonly props
- `frontend/src/components/UndoToast.tsx`: readonly props
- `frontend/src/hooks/useBrowserNotifications.test.tsx`: readonly props, readonly statics, non-empty `close`, `globalThis`
- `frontend/src/hooks/useBrowserNotifications.ts`: `globalThis`
- `frontend/src/hooks/useColumnResize.test.tsx`: `globalThis`
- `frontend/src/hooks/useColumnResize.ts`: `globalThis`
- `frontend/src/hooks/useDismiss.test.tsx`: readonly props
- `frontend/src/hooks/useKeyboard.test.tsx`: readonly props, valid table header
- `frontend/src/hooks/useKeyboard.ts`: simplify ternary
- `frontend/src/hooks/useSnapshot.test.tsx`: readonly props, remove `void`
- `frontend/src/hooks/useSnapshot.ts`: remove `void`
- `frontend/src/hooks/useSort.test.tsx`: readonly props
- `frontend/src/test/setup.ts`: non-empty mock methods, `globalThis`
- `src/corvix/actions.py`: remove empty code block
- `src/corvix/config.py`: constants, `list(value)`
- `src/corvix/db.py`: `users.id` constant
- `src/corvix/domain.py`: complexity reduction, `stored record` constant
- `src/corvix/ingestion.py`: `request failed` constant
- `src/corvix/migrations/versions/838399841a57_initial_schema.py`: `users.id` constant
- `src/corvix/services.py`: complexity reduction, `dict(clients_by_account)`
- `src/corvix/storage.py`: keep signatures stable, mark `user_id` unused, refactor `_coerce_context()`
- `tests/e2e/conftest.py`: deduplicate handlers, timestamp constant
- `tests/e2e/test_dashboard_ui.py`: satisfied by Playwright protocol update
- `tests/integration/test_cli.py`: explain empty stubs
- `tests/integration/test_web_api.py`: replace generator-throw helpers
- `tests/unit/test_config.py`: `pytest.approx(...)`
- `tests/unit/test_dashboarding.py`: `pytest.approx(...)`
- `tests/unit/test_scoring.py`: `pytest.approx(...)`, remove commented code

## Validation

Run after implementation:

- `uv run ruff check .`
- `uv run ty check src/corvix/`
- `uv run pytest tests/unit/test_config.py tests/unit/test_dashboarding.py tests/unit/test_scoring.py`
- `uv run pytest tests/integration/test_cli.py tests/integration/test_web_api.py`
- `npm --prefix frontend run test -- --run`
- `make frontend-build`
- `uv run pytest tests/e2e/test_dashboard_ui.py`
- `docker compose up --build`

## Highest-Risk Changes

- `tests/e2e/playwright_types.py` protocol update
- `frontend/src/app.tsx` switch to native `<dialog>`
- `src/corvix/domain.py` complexity refactor
- `src/corvix/services.py` complexity refactor
- `src/corvix/storage.py` `_coerce_context()` refactor
