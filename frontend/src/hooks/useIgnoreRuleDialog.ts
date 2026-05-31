import { useCallback, useEffect, useState } from "preact/hooks";
import { fetchRuleSnippets } from "../api";
import type { DashboardItem, RuleSnippetsPayload } from "../types";

interface IgnoreMenuState {
	item: DashboardItem;
	x: number;
	y: number;
}

/**
 * Owns the "create ignore rule" flow: the row context menu, the dialog item,
 * and the lazily fetched rule snippets (with their loading and error state).
 */
export function useIgnoreRuleDialog(currentDashboard: string | null) {
	const [menu, setMenu] = useState<IgnoreMenuState | null>(null);
	const [dialogItem, setDialogItem] = useState<DashboardItem | null>(null);
	const [snippets, setSnippets] = useState<RuleSnippetsPayload | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const requestRule = useCallback(
		(item: DashboardItem, position: { x: number; y: number }) => {
			setMenu({ item, x: position.x, y: position.y });
		},
		[],
	);

	const openDialog = useCallback((item: DashboardItem) => {
		setDialogItem(item);
		setMenu(null);
	}, []);

	const closeDialog = useCallback(() => {
		setDialogItem(null);
		setSnippets(null);
		setError(null);
		setLoading(false);
	}, []);

	useEffect(() => {
		if (!menu) return;
		const handleClickAway = () => setMenu(null);
		const handleEscape = (event: KeyboardEvent) => {
			if (event.key === "Escape") {
				setMenu(null);
			}
		};
		globalThis.addEventListener("click", handleClickAway);
		globalThis.addEventListener("keydown", handleEscape);
		return () => {
			globalThis.removeEventListener("click", handleClickAway);
			globalThis.removeEventListener("keydown", handleEscape);
		};
	}, [menu]);

	useEffect(() => {
		if (!dialogItem) {
			return;
		}
		let cancelled = false;
		setLoading(true);
		setError(null);
		setSnippets(null);
		void fetchRuleSnippets(
			dialogItem.account_id,
			dialogItem.thread_id,
			currentDashboard ?? undefined,
		)
			.then((payload) => {
				if (cancelled) return;
				setSnippets(payload);
			})
			.catch((err: unknown) => {
				if (cancelled) return;
				setError(
					err instanceof Error ? err.message : "Failed to load rule snippets",
				);
			})
			.finally(() => {
				if (cancelled) return;
				setLoading(false);
			});
		return () => {
			cancelled = true;
		};
	}, [dialogItem, currentDashboard]);

	return {
		menu,
		dialogItem,
		snippets,
		loading,
		error,
		requestRule,
		openDialog,
		closeDialog,
	};
}
