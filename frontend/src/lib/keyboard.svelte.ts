/**
 * Global keyboard shortcuts, ported from `useKeyboard.ts` and extended with
 * Cmd/Ctrl+K (command palette) and `/` (focus search). Suppressed while typing;
 * Escape blurs; `?` toggles the shortcuts panel.
 */

export interface KeyboardOptions {
	onRefresh: () => void;
	onFocusFilters: () => void;
	onDismissFocused: () => void;
	onToggleShortcuts: () => void;
	onCommandPalette: () => void;
	onFocusSearch: () => void;
}

function isTypingTarget(target: EventTarget | null): boolean {
	if (!(target instanceof HTMLElement)) return false;
	return (
		["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName) ||
		target.isContentEditable
	);
}

function focusRelativeRow(delta: number): void {
	const rows = Array.from(
		document.querySelectorAll<HTMLTableRowElement>("tr[data-thread-id]"),
	);
	if (rows.length === 0) return;

	const active = document.activeElement;
	const current = active?.closest(
		"tr[data-thread-id]",
	) as HTMLTableRowElement | null;
	const idx = current ? rows.indexOf(current) : -1;

	let nextIndex: number;
	if (idx === -1) {
		nextIndex = delta > 0 ? 0 : rows.length - 1;
	} else {
		nextIndex = Math.min(rows.length - 1, Math.max(0, idx + delta));
	}
	rows[nextIndex]?.focus();
}

function openFocusedRow(): void {
	const active = document.activeElement;
	const row = active?.closest(
		"tr[data-thread-id]",
	) as HTMLTableRowElement | null;
	if (!row) return;
	const link = row.querySelector<HTMLAnchorElement>("td[data-label='Title'] a");
	if (link) link.click();
}

export class KeyboardStore {
	readonly #options: KeyboardOptions;

	constructor(options: KeyboardOptions) {
		this.#options = options;
	}

	readonly #handleKeyDown = (event: KeyboardEvent): void => {
		const typingTarget = isTypingTarget(event.target);
		const hasModifiers = event.altKey || event.ctrlKey || event.metaKey;

		// Command palette works even from an input (Cmd/Ctrl+K).
		if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
			event.preventDefault();
			this.#options.onCommandPalette();
			return;
		}

		if (event.key === "Escape") {
			(document.activeElement as HTMLElement | null)?.blur();
			return;
		}

		if (!typingTarget && !hasModifiers && event.key === "?") {
			event.preventDefault();
			this.#options.onToggleShortcuts();
			return;
		}

		if (typingTarget || hasModifiers) return;

		if (event.key === "/") {
			event.preventDefault();
			this.#options.onFocusSearch();
			return;
		}

		const key = event.key.toLowerCase();

		if (key === "r") {
			event.preventDefault();
			this.#options.onRefresh();
			return;
		}
		if (key === "f") {
			event.preventDefault();
			this.#options.onFocusFilters();
			return;
		}
		if (key === "j") {
			event.preventDefault();
			focusRelativeRow(1);
			return;
		}
		if (key === "k") {
			event.preventDefault();
			focusRelativeRow(-1);
			return;
		}
		if (key === "d") {
			event.preventDefault();
			this.#options.onDismissFocused();
		}
		if (event.key === "Enter") {
			openFocusedRow();
		}
	};

	bind(): void {
		$effect(() => {
			document.addEventListener("keydown", this.#handleKeyDown);
			return () => document.removeEventListener("keydown", this.#handleKeyDown);
		});
	}
}
