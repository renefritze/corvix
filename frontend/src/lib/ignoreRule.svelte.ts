/**
 * "Create ignore rule" flow, ported from `useIgnoreRuleDialog.ts`: the row
 * context menu, the dialog item, and the lazily fetched rule snippets with
 * their loading/error state and request cancellation.
 */
import { fetchRuleSnippets } from "../api";
import type { DashboardItem, RuleSnippetsPayload } from "../types";

export interface IgnoreMenuState {
	item: DashboardItem;
	x: number;
	y: number;
}

export class IgnoreRuleStore {
	menu = $state<IgnoreMenuState | null>(null);
	dialogItem = $state<DashboardItem | null>(null);
	snippets = $state<RuleSnippetsPayload | null>(null);
	loading = $state(false);
	error = $state<string | null>(null);
	#getDashboard: () => string | null;

	constructor(getDashboard: () => string | null) {
		this.#getDashboard = getDashboard;
	}

	requestRule = (
		item: DashboardItem,
		position: { x: number; y: number },
	): void => {
		this.menu = { item, x: position.x, y: position.y };
	};

	openDialog = (item: DashboardItem): void => {
		this.dialogItem = item;
		this.menu = null;
	};

	closeDialog = (): void => {
		this.dialogItem = null;
		this.snippets = null;
		this.error = null;
		this.loading = false;
	};

	bind(): void {
		// Dismiss the context menu on outside click / Escape.
		$effect(() => {
			if (!this.menu) return;
			const handleClickAway = () => {
				this.menu = null;
			};
			const handleEscape = (event: KeyboardEvent) => {
				if (event.key === "Escape") this.menu = null;
			};
			globalThis.addEventListener("click", handleClickAway);
			globalThis.addEventListener("keydown", handleEscape);
			return () => {
				globalThis.removeEventListener("click", handleClickAway);
				globalThis.removeEventListener("keydown", handleEscape);
			};
		});

		// Lazily fetch snippets whenever the dialog opens, cancelling stale loads.
		$effect(() => {
			const item = this.dialogItem;
			if (!item) return;
			const dashboard = this.#getDashboard();
			let cancelled = false;
			this.loading = true;
			this.error = null;
			this.snippets = null;
			void fetchRuleSnippets(
				item.account_id,
				item.thread_id,
				dashboard ?? undefined,
			)
				.then((payload) => {
					if (!cancelled) this.snippets = payload;
				})
				.catch((err: unknown) => {
					if (!cancelled) {
						this.error =
							err instanceof Error ? err.message : "Failed to load rule snippets";
					}
				})
				.finally(() => {
					if (!cancelled) this.loading = false;
				});
			return () => {
				cancelled = true;
			};
		});
	}
}
