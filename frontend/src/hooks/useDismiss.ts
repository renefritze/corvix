import { useCallback, useEffect, useRef, useState } from "preact/hooks";
import { dismissNotification } from "../api";

interface PendingDismissal {
	threadId: string;
	timerId: ReturnType<typeof setTimeout>;
}

export function useDismiss(
	onRefresh: () => void,
	onError: (msg: string) => void,
) {
	const [pending, setPending] = useState<Map<string, PendingDismissal>>(
		new Map(),
	);
	const pendingRef = useRef(pending);
	useEffect(() => {
		pendingRef.current = pending;
	}, [pending]);

	const dismiss = useCallback(
		(threadId: string) => {
			// Cancel any existing timer for this thread
			const existing = pendingRef.current.get(threadId);
			if (existing) clearTimeout(existing.timerId);

			const timerId = setTimeout(async () => {
				try {
					await dismissNotification(threadId);
					onRefresh();
				} catch (err) {
					onError(err instanceof Error ? err.message : "Dismiss failed");
				} finally {
					setPending((prev) => {
						const next = new Map(prev);
						next.delete(threadId);
						return next;
					});
				}
			}, 3000);

			setPending((prev) => {
				const next = new Map(prev);
				next.set(threadId, { threadId, timerId });
				return next;
			});
		},
		[onRefresh, onError],
	);

	const undo = useCallback((threadId: string) => {
		const item = pendingRef.current.get(threadId);
		if (!item) return;
		clearTimeout(item.timerId);
		setPending((prev) => {
			const next = new Map(prev);
			next.delete(threadId);
			return next;
		});
	}, []);

	const undoAll = useCallback(() => {
		pendingRef.current.forEach((item) => clearTimeout(item.timerId));
		setPending(new Map());
	}, []);

	return { pending, dismiss, undo, undoAll };
}
