/**
 * Dismiss with a 3-second undo grace period, ported from `useDismiss.ts`.
 * Pending dismissals live in a Map keyed by notificationKey with per-thread
 * timers; committing hits the API and refreshes; the committed set is pruned
 * whenever a thread leaves the current snapshot.
 */
import { dismissNotification } from "../api";
import { notificationKey } from "../types";

interface PendingDismissal {
	accountId: string;
	threadId: string;
	key: string;
	timerId: ReturnType<typeof setTimeout>;
}

export class DismissStore {
	pending = $state<Map<string, PendingDismissal>>(new Map());
	#committed = $state<Set<string>>(new Set());
	#onRefresh: () => Promise<void>;
	#onError: (msg: string) => void;
	#getCurrentThreadIds: () => Set<string>;

	constructor(
		onRefresh: () => Promise<void>,
		onError: (msg: string) => void,
		getCurrentThreadIds: () => Set<string>,
	) {
		this.#onRefresh = onRefresh;
		this.#onError = onError;
		this.#getCurrentThreadIds = getCurrentThreadIds;
	}

	get count(): number {
		return this.pending.size;
	}

	get hiddenThreadIds(): Set<string> {
		return new Set([...this.pending.keys(), ...this.#committed]);
	}

	dismiss = (accountId: string, threadId: string): void => {
		const key = notificationKey({ account_id: accountId, thread_id: threadId });
		if (this.#committed.has(key)) return;
		const existing = this.pending.get(key);
		if (existing) clearTimeout(existing.timerId);

		const timerId = setTimeout(async () => {
			try {
				await dismissNotification(accountId, threadId);
				const committed = new Set(this.#committed);
				committed.add(key);
				this.#committed = committed;
				await this.#onRefresh();
			} catch (err) {
				if (this.#committed.has(key)) {
					const committed = new Set(this.#committed);
					committed.delete(key);
					this.#committed = committed;
				}
				this.#onError(err instanceof Error ? err.message : "Dismiss failed");
			} finally {
				const next = new Map(this.pending);
				next.delete(key);
				this.pending = next;
			}
		}, 3000);

		const next = new Map(this.pending);
		next.set(key, { key, accountId, threadId, timerId });
		this.pending = next;
	};

	undo = (accountId: string, threadId: string): void => {
		const key = notificationKey({ account_id: accountId, thread_id: threadId });
		const item = this.pending.get(key);
		if (!item) return;
		clearTimeout(item.timerId);
		const next = new Map(this.pending);
		next.delete(key);
		this.pending = next;
	};

	undoAll = (): void => {
		for (const item of this.pending.values()) {
			clearTimeout(item.timerId);
		}
		this.pending = new Map();
	};

	bind(): void {
		// Drop committed threads once they leave the current snapshot.
		$effect(() => {
			const current = this.#getCurrentThreadIds();
			let changed = false;
			const next = new Set(this.#committed);
			for (const key of this.#committed) {
				if (!current.has(key)) {
					next.delete(key);
					changed = true;
				}
			}
			if (changed) this.#committed = next;
		});
	}
}
