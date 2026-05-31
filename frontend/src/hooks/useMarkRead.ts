import { useCallback, useState } from "preact/hooks";
import { markNotificationRead } from "../api";
import type { DashboardItem } from "../types";

/**
 * Handles marking notifications read: a single thread (opening its target) and
 * every visible unread item in a group, tracking which groups are in flight.
 */
export function useMarkRead(
	onRefresh: () => Promise<void>,
	onError: (msg: string) => void,
) {
	const [markingGroupNames, setMarkingGroupNames] = useState<Set<string>>(
		new Set(),
	);

	const openTarget = useCallback(
		(accountId: string, threadId: string) => {
			void markNotificationRead(accountId, threadId)
				.then(() => onRefresh())
				.catch((err: unknown) => {
					onError(err instanceof Error ? err.message : "Mark read failed");
				});
		},
		[onRefresh, onError],
	);

	const markGroupRead = useCallback(
		(groupName: string, items: DashboardItem[]) => {
			const unreadItems = items.filter((item) => item.unread);
			if (unreadItems.length === 0) return;
			setMarkingGroupNames((prev) => {
				const next = new Set(prev);
				next.add(groupName);
				return next;
			});
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
						onError(
							`Mark all read failed for ${failures} notification${failures > 1 ? "s" : ""}`,
						);
					}
				})
				.finally(() => {
					setMarkingGroupNames((prev) => {
						const next = new Set(prev);
						next.delete(groupName);
						return next;
					});
					return onRefresh();
				});
		},
		[onRefresh, onError],
	);

	return { markingGroupNames, openTarget, markGroupRead };
}
