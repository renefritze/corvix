import { useEffect } from "preact/hooks";

interface KeyboardOptions {
	onRefresh: () => void;
	onFocusFilters: () => void;
	onDismissFocused: () => void;
}

export function useKeyboard({
	onRefresh,
	onFocusFilters,
	onDismissFocused,
}: KeyboardOptions) {
	useEffect(() => {
		function handleKeyDown(e: KeyboardEvent) {
			const target = e.target as HTMLElement;
			const inInput = ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName);

			if (e.key === "Escape") {
				(document.activeElement as HTMLElement | null)?.blur();
				return;
			}

			if (e.key === "/") {
				e.preventDefault();
				onFocusFilters();
				return;
			}

			if (inInput) return;

			if (e.key === "r" || e.key === "R") {
				onRefresh();
				return;
			}

			if (e.key === "d" || e.key === "D") {
				const focused = document.activeElement as HTMLElement | null;
				if (focused?.tagName === "TR") {
					onDismissFocused();
				}
				return;
			}

			if (e.key === "j" || e.key === "J") {
				const rows = Array.from(
					document.querySelectorAll<HTMLElement>("tr[tabindex='0']"),
				);
				const idx = rows.indexOf(document.activeElement as HTMLElement);
				rows[idx + 1]?.focus();
				return;
			}

			if (e.key === "k" || e.key === "K") {
				const rows = Array.from(
					document.querySelectorAll<HTMLElement>("tr[tabindex='0']"),
				);
				const idx = rows.indexOf(document.activeElement as HTMLElement);
				rows[idx - 1]?.focus();
				return;
			}

			if (e.key === "Enter") {
				const focused = document.activeElement as HTMLElement | null;
				if (focused?.tagName === "TR") {
					const link = focused.querySelector<HTMLAnchorElement>("a[href]");
					if (link) window.open(link.href, "_blank");
				}
			}
		}
		document.addEventListener("keydown", handleKeyDown);
		return () => document.removeEventListener("keydown", handleKeyDown);
	}, [onRefresh, onFocusFilters, onDismissFocused]);
}
