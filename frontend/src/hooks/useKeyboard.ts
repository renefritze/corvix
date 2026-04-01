import { useEffect } from "preact/hooks";

interface KeyboardOptions {
	onRefresh: () => void;
	onFocusFilters: () => void;
	onDismissFocused: () => void;
	onToggleShortcuts: () => void;
}

function isTypingTarget(target: EventTarget | null): boolean {
	if (!(target instanceof HTMLElement)) return false;
	return (
		["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName) ||
		target.isContentEditable
	);
}

function focusRelativeRow(delta: number) {
	const rows = Array.from(
		document.querySelectorAll<HTMLTableRowElement>("tr.notification-row"),
	);
	if (rows.length === 0) return;

	const active = document.activeElement as HTMLElement | null;
	const current = active?.closest(
		"tr.notification-row",
	) as HTMLTableRowElement | null;
	const idx = current ? rows.indexOf(current) : -1;

	const nextIndex =
		idx === -1
			? delta > 0
				? 0
				: rows.length - 1
			: Math.min(rows.length - 1, Math.max(0, idx + delta));

	rows[nextIndex]?.focus();
}

export function useKeyboard({
	onRefresh,
	onFocusFilters,
	onDismissFocused,
	onToggleShortcuts,
}: KeyboardOptions) {
	useEffect(() => {
		function handleKeyDown(e: KeyboardEvent) {
			const typingTarget = isTypingTarget(e.target);
			const hasModifiers = e.altKey || e.ctrlKey || e.metaKey;

			if (e.key === "Escape") {
				(document.activeElement as HTMLElement | null)?.blur();
				return;
			}

			if (
				!typingTarget &&
				!e.altKey &&
				!e.ctrlKey &&
				!e.metaKey &&
				e.key === "?"
			) {
				e.preventDefault();
				onToggleShortcuts();
				return;
			}

			if (typingTarget || hasModifiers) return;

			const key = e.key.toLowerCase();

			if (key === "r") {
				e.preventDefault();
				onRefresh();
				return;
			}

			if (key === "f") {
				e.preventDefault();
				onFocusFilters();
				return;
			}

			if (key === "j") {
				e.preventDefault();
				focusRelativeRow(1);
				return;
			}

			if (key === "k") {
				e.preventDefault();
				focusRelativeRow(-1);
				return;
			}

			if (key === "d") {
				e.preventDefault();
				onDismissFocused();
			}
		}
		document.addEventListener("keydown", handleKeyDown);
		return () => document.removeEventListener("keydown", handleKeyDown);
	}, [onRefresh, onFocusFilters, onDismissFocused, onToggleShortcuts]);
}
