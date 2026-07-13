/**
 * Marks notifications read: a single thread (opening its target) and every
 * visible unread item in a group, tracking in-flight groups. Ported from
 * `useMarkRead.ts`.
 */
import { markNotificationRead } from "../api";
import type { DashboardItem } from "../types";

export class MarkReadStore {
	markingGroupNames = $state<Set<string>>(new Set());
	readonly #onRefresh: () => Promise<void>;
	readonly #onError: (msg: string) => void;

	constructor(
		onRefresh: () => Promise<void>,
		onError: (msg: string) => void,
	) {
		this.#onRefresh = onRefresh;
		this.#onError = onError;
	}

	openTarget = (accountId: string, threadId: string): void => {
		void markNotificationRead(accountId, threadId)
			.then(() => this.#onRefresh())
			.catch((err: unknown) => {
				this.#onError(err instanceof Error ? err.message : "Mark read failed");
			});
	};

	markGroupRead = (groupName: string, items: DashboardItem[]): void => {
		const unreadItems = items.filter((item) => item.unread);
		if (unreadItems.length === 0) return;
		const marking = new Set(this.markingGroupNames);
		marking.add(groupName);
		this.markingGroupNames = marking;
		void Promise.allSettled(
			unreadItems.map((item) =>
				markNotificationRead(item.account_id, item.thread_id),
			),
		)
			.then((results) => {
				const failures = results.filter(
					(result) => result.status === "rejected",
				).length;
				if (failures > 0) {
					this.#onError(
						`Mark all read failed for ${failures} notification${failures > 1 ? "s" : ""}`,
					);
				}
			})
			.finally(() => {
				const next = new Set(this.markingGroupNames);
				next.delete(groupName);
				this.markingGroupNames = next;
				return this.#onRefresh();
			});
	};
}
