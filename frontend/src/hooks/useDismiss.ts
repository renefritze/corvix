import {
	useCallback,
	useEffect,
	useMemo,
	useRef,
	useState,
} from "preact/hooks";
import { dismissNotification } from "../api";
import { notificationKey } from "../types";

interface PendingDismissal {
	accountId: string;
	threadId: string;
	key: string;
	timerId: ReturnType<typeof setTimeout>;
}

export function useDismiss(
	onRefresh: () => Promise<void>,
	onError: (msg: string) => void,
	currentThreadIds: Set<string>,
) {
	const [pending, setPending] = useState<Map<string, PendingDismissal>>(
		new Map(),
	);
	const [committed, setCommitted] = useState<Set<string>>(new Set());
	const pendingRef = useRef(pending);
	const committedRef = useRef(committed);
	useEffect(() => {
		pendingRef.current = pending;
	}, [pending]);
	useEffect(() => {
		committedRef.current = committed;
	}, [committed]);

	useEffect(() => {
		setCommitted((prev) => {
			const next = new Set(prev);
			for (const threadId of prev) {
				if (!currentThreadIds.has(threadId)) {
					next.delete(threadId);
				}
			}
			return next;
		});
	}, [currentThreadIds]);

	const dismiss = useCallback(
		(accountId: string, threadId: string) => {
			const key = notificationKey({
				account_id: accountId,
				thread_id: threadId,
			});
			if (committedRef.current.has(key)) return;
			// Cancel any existing timer for this thread
			const existing = pendingRef.current.get(key);
			if (existing) clearTimeout(existing.timerId);

			const timerId = setTimeout(async () => {
				try {
					setPending((prev) => {
						const next = new Map(prev);
						next.delete(key);
						return next;
					});
					await dismissNotification(accountId, threadId);
					setCommitted((prev) => {
						const next = new Set(prev);
						next.add(key);
						return next;
					});
					await onRefresh();
				} catch (err) {
					setCommitted((prev) => {
						if (!prev.has(key)) return prev;
						const next = new Set(prev);
						next.delete(key);
						return next;
					});
					onError(err instanceof Error ? err.message : "Dismiss failed");
				} finally {
					setPending((prev) => {
						const next = new Map(prev);
						next.delete(key);
						return next;
					});
				}
			}, 3000);

			setPending((prev) => {
				const next = new Map(prev);
				next.set(key, { key, accountId, threadId, timerId });
				return next;
			});
		},
		[onRefresh, onError],
	);

	const undo = useCallback((accountId: string, threadId: string) => {
		const key = notificationKey({ account_id: accountId, thread_id: threadId });
		const item = pendingRef.current.get(key);
		if (!item) return;
		clearTimeout(item.timerId);
		setPending((prev) => {
			const next = new Map(prev);
			next.delete(key);
			return next;
		});
	}, []);

	const undoAll = useCallback(() => {
		for (const item of pendingRef.current.values()) {
			clearTimeout(item.timerId);
		}
		setPending(new Map());
	}, []);

	const hiddenThreadIds = useMemo(
		() => new Set([...pending.keys(), ...committed.keys()]),
		[pending, committed],
	);

	return { pending, dismiss, undo, undoAll, hiddenThreadIds };
}
