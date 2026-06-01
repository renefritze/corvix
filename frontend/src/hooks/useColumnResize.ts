import { useCallback, useEffect, useRef, useState } from "preact/hooks";
import type { ColumnWidths, ResizableSortColumn } from "../types";

/**
 * Bump this whenever the column set or the persisted width schema changes in a
 * way that makes older stored values invalid (columns renamed, removed, or the
 * value shape altered). Old keys are purged on startup so a schema change never
 * resurrects widths for columns that no longer exist.
 */
const STORAGE_VERSION = 2;
const STORAGE_KEY_PREFIX = "corvix.table.columnWidths";
const STORAGE_KEY = `${STORAGE_KEY_PREFIX}.v${STORAGE_VERSION}`;

/**
 * Returns true for any persisted key this hook owns: the unversioned legacy key
 * (equal to the prefix) and every `${prefix}.vN` key. Used to distinguish our
 * keys from unrelated localStorage entries during cleanup.
 */
function isManagedColumnWidthKey(key: string): boolean {
	return key === STORAGE_KEY_PREFIX || key.startsWith(`${STORAGE_KEY_PREFIX}.v`);
}

/**
 * Removes every column-width key except the current version's. This sweeps away
 * the unversioned legacy key and any superseded `.vN` entries so they cannot be
 * loaded after a schema bump and cannot accumulate as orphaned storage.
 */
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

/**
 * Reads the persisted widths for the current schema version, falling back to a
 * one-time migration from the unversioned legacy key so users keep their layout
 * across this upgrade. `parseSavedWidths` validates and clamps the result, so a
 * migrated value can only ever contain known, in-range columns.
 */
function readInitialWidths(storage: Storage): ColumnWidths {
	const current = storage.getItem(STORAGE_KEY);
	if (current !== null) return parseSavedWidths(current);
	return parseSavedWidths(storage.getItem(STORAGE_KEY_PREFIX));
}

export function useColumnResize() {
	const [widths, setWidths] = useState<ColumnWidths>(() => {
		if (typeof globalThis.window === "undefined") return DEFAULT_COLUMN_WIDTHS;
		return readInitialWidths(globalThis.window.localStorage);
	});
	const dragRef = useRef<DragState | null>(null);

	// Purge legacy/older-version keys once on mount. Reading the initial widths
	// above already migrated any legacy value, so this only deletes orphans.
	useEffect(() => {
		if (typeof globalThis.window === "undefined") return;
		try {
			cleanupStaleColumnWidthKeys(globalThis.window.localStorage);
		} catch {
			/* ignore storage access errors */
		}
	}, []);

	const onMouseMove = useCallback((event: MouseEvent) => {
		const dragState = dragRef.current;
		if (!dragState) return;
		const delta = event.clientX - dragState.startX;
		const nextWidth = Math.max(
			MIN_COLUMN_WIDTHS[dragState.column],
			dragState.startWidth + delta,
		);
		setWidths((prev) => {
			if (prev[dragState.column] === nextWidth) return prev;
			return { ...prev, [dragState.column]: nextWidth };
		});
	}, []);

	const stopResize = useCallback(() => {
		dragRef.current = null;
		document.body.classList.remove("col-resizing");
		if (typeof globalThis.window !== "undefined") {
			globalThis.window.removeEventListener("mousemove", onMouseMove);
			globalThis.window.removeEventListener("mouseup", stopResize);
		}
	}, [onMouseMove]);

	const startResize = useCallback(
		(column: ResizableSortColumn, startX: number) => {
			stopResize();
			dragRef.current = {
				column,
				startX,
				startWidth: widths[column],
			};
			document.body.classList.add("col-resizing");
			if (typeof globalThis.window !== "undefined") {
				globalThis.window.addEventListener("mousemove", onMouseMove);
				globalThis.window.addEventListener("mouseup", stopResize);
			}
		},
		[onMouseMove, stopResize, widths],
	);

	const resetColumnWidth = useCallback((column: ResizableSortColumn) => {
		setWidths((prev) => ({
			...prev,
			[column]: DEFAULT_COLUMN_WIDTHS[column],
		}));
	}, []);

	const resetLayout = useCallback(() => {
		setWidths(DEFAULT_COLUMN_WIDTHS);
	}, []);

	useEffect(
		() => () => {
			stopResize();
		},
		[stopResize],
	);

	useEffect(() => {
		if (typeof globalThis.window === "undefined") return;
		try {
			globalThis.window.localStorage.setItem(
				STORAGE_KEY,
				JSON.stringify(widths),
			);
		} catch {
			/* ignore storage write errors */
		}
	}, [widths]);

	return {
		widths,
		startResize,
		resetColumnWidth,
		resetLayout,
	};
}
