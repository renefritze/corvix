/**
 * Per-column drag-resize with widths persisted in localStorage, ported verbatim
 * from `useColumnResize.ts` including STORAGE_VERSION = 2 and the one-time
 * migration from the unversioned legacy key so user layouts survive the upgrade.
 */
import type { ColumnWidths, ResizableSortColumn } from "../types";

const STORAGE_VERSION = 2;
const STORAGE_KEY_PREFIX = "corvix.table.columnWidths";
const STORAGE_KEY = `${STORAGE_KEY_PREFIX}.v${STORAGE_VERSION}`;

function isManagedColumnWidthKey(key: string): boolean {
	return key === STORAGE_KEY_PREFIX || key.startsWith(`${STORAGE_KEY_PREFIX}.v`);
}

function cleanupStaleColumnWidthKeys(storage: Storage): void {
	const staleKeys: string[] = [];
	for (let i = 0; i < storage.length; i++) {
		const key = storage.key(i);
		if (key && key !== STORAGE_KEY && isManagedColumnWidthKey(key)) {
			staleKeys.push(key);
		}
	}
	for (const key of staleKeys) {
		storage.removeItem(key);
	}
}

const DEFAULT_COLUMN_WIDTHS: ColumnWidths = {
	repository: 185,
	subject_type: 110,
	reason: 150,
	score: 75,
	updated_at: 110,
};

const MIN_COLUMN_WIDTHS: ColumnWidths = {
	repository: 120,
	subject_type: 90,
	reason: 120,
	score: 64,
	updated_at: 96,
};

interface DragState {
	column: ResizableSortColumn;
	startX: number;
	startWidth: number;
}

function normalizeStoredWidth(
	column: ResizableSortColumn,
	value: unknown,
): number {
	const numericValue = Number(value);
	if (!Number.isFinite(numericValue)) {
		return DEFAULT_COLUMN_WIDTHS[column];
	}
	return Math.max(MIN_COLUMN_WIDTHS[column], numericValue);
}

function parseSavedWidths(raw: string | null): ColumnWidths {
	if (!raw) return DEFAULT_COLUMN_WIDTHS;
	try {
		const parsed = JSON.parse(raw) as Partial<ColumnWidths>;
		return {
			repository: normalizeStoredWidth("repository", parsed.repository),
			subject_type: normalizeStoredWidth("subject_type", parsed.subject_type),
			reason: normalizeStoredWidth("reason", parsed.reason),
			score: normalizeStoredWidth("score", parsed.score),
			updated_at: normalizeStoredWidth("updated_at", parsed.updated_at),
		};
	} catch {
		return DEFAULT_COLUMN_WIDTHS;
	}
}

function readInitialWidths(storage: Storage): ColumnWidths {
	const current = storage.getItem(STORAGE_KEY);
	if (current !== null) return parseSavedWidths(current);
	return parseSavedWidths(storage.getItem(STORAGE_KEY_PREFIX));
}

export class ColumnResizeStore {
	widths = $state<ColumnWidths>(DEFAULT_COLUMN_WIDTHS);
	#drag: DragState | null = null;

	constructor() {
		if (globalThis.window !== undefined) {
			try {
				this.widths = readInitialWidths(globalThis.window.localStorage);
			} catch {
				// localStorage can throw (SecurityError); keep defaults.
			}
		}
	}

	#onMouseMove = (event: MouseEvent): void => {
		const drag = this.#drag;
		if (!drag) return;
		const delta = event.clientX - drag.startX;
		const nextWidth = Math.max(MIN_COLUMN_WIDTHS[drag.column], drag.startWidth + delta);
		if (this.widths[drag.column] !== nextWidth) {
			this.widths = { ...this.widths, [drag.column]: nextWidth };
		}
	};

	stopResize = (): void => {
		this.#drag = null;
		if (globalThis.document !== undefined) {
			globalThis.document.body.classList.remove("col-resizing");
		}
		if (globalThis.window !== undefined) {
			globalThis.window.removeEventListener("mousemove", this.#onMouseMove);
			globalThis.window.removeEventListener("mouseup", this.stopResize);
		}
	};

	startResize = (column: ResizableSortColumn, startX: number): void => {
		this.stopResize();
		this.#drag = { column, startX, startWidth: this.widths[column] };
		if (globalThis.document !== undefined) {
			globalThis.document.body.classList.add("col-resizing");
		}
		if (globalThis.window !== undefined) {
			globalThis.window.addEventListener("mousemove", this.#onMouseMove);
			globalThis.window.addEventListener("mouseup", this.stopResize);
		}
	};

	resetColumnWidth = (column: ResizableSortColumn): void => {
		this.widths = { ...this.widths, [column]: DEFAULT_COLUMN_WIDTHS[column] };
	};

	resetLayout = (): void => {
		this.widths = DEFAULT_COLUMN_WIDTHS;
	};

	bind(): void {
		// Purge legacy/older-version keys once; also stop any drag on teardown.
		$effect(() => {
			if (globalThis.window !== undefined) {
				try {
					cleanupStaleColumnWidthKeys(globalThis.window.localStorage);
				} catch {
					/* ignore storage access errors */
				}
			}
			return () => this.stopResize();
		});

		// Persist widths on change.
		$effect(() => {
			const widths = this.widths;
			if (globalThis.window === undefined) return;
			try {
				globalThis.window.localStorage.setItem(STORAGE_KEY, JSON.stringify(widths));
			} catch {
				/* ignore storage write errors */
			}
		});
	}
}
