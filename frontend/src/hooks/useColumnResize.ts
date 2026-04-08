import { useCallback, useEffect, useRef, useState } from "preact/hooks";
import type { ColumnWidths, ResizableSortColumn } from "../types";

const STORAGE_KEY = "corvix.table.columnWidths";

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

function parseSavedWidths(raw: string | null): ColumnWidths {
	if (!raw) return DEFAULT_COLUMN_WIDTHS;
	try {
		const parsed = JSON.parse(raw) as Partial<ColumnWidths>;
		return {
			repository: Number(parsed.repository) || DEFAULT_COLUMN_WIDTHS.repository,
			subject_type:
				Number(parsed.subject_type) || DEFAULT_COLUMN_WIDTHS.subject_type,
			reason: Number(parsed.reason) || DEFAULT_COLUMN_WIDTHS.reason,
			score: Number(parsed.score) || DEFAULT_COLUMN_WIDTHS.score,
			updated_at: Number(parsed.updated_at) || DEFAULT_COLUMN_WIDTHS.updated_at,
		};
	} catch {
		return DEFAULT_COLUMN_WIDTHS;
	}
}

export function useColumnResize() {
	const [widths, setWidths] = useState<ColumnWidths>(() => {
		if (typeof window === "undefined") return DEFAULT_COLUMN_WIDTHS;
		return parseSavedWidths(window.localStorage.getItem(STORAGE_KEY));
	});
	const dragRef = useRef<DragState | null>(null);

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
		window.removeEventListener("mousemove", onMouseMove);
		window.removeEventListener("mouseup", stopResize);
	}, [onMouseMove]);

	const startResize = useCallback(
		(column: ResizableSortColumn, startX: number) => {
			dragRef.current = {
				column,
				startX,
				startWidth: widths[column],
			};
			document.body.classList.add("col-resizing");
			window.addEventListener("mousemove", onMouseMove);
			window.addEventListener("mouseup", stopResize);
		},
		[onMouseMove, stopResize, widths],
	);

	const resetColumnWidth = useCallback((column: ResizableSortColumn) => {
		setWidths((prev) => ({
			...prev,
			[column]: DEFAULT_COLUMN_WIDTHS[column],
		}));
	}, []);

	useEffect(
		() => () => {
			stopResize();
		},
		[stopResize],
	);

	useEffect(() => {
		if (typeof window === "undefined") return;
		try {
			window.localStorage.setItem(STORAGE_KEY, JSON.stringify(widths));
		} catch {
			/* ignore storage write errors */
		}
	}, [widths]);

	return {
		widths,
		startResize,
		resetColumnWidth,
	};
}
