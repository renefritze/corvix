import {
	useCallback,
	useEffect,
	useMemo,
	useRef,
	useState,
} from "preact/hooks";
import { dismissNotification } from "../api";

interface PendingDismissal {
	threadId: string;
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
		(threadId: string) => {
			if (committedRef.current.has(threadId)) return;
			// Cancel any existing timer for this thread
			const existing = pendingRef.current.get(threadId);
			if (existing) clearTimeout(existing.timerId);

			const timerId = setTimeout(async () => {
				try {
					setPending((prev) => {
						const next = new Map(prev);
						next.delete(threadId);
						return next;
					});
					await dismissNotification(threadId);
					setCommitted((prev) => {
						const next = new Set(prev);
						next.add(threadId);
						return next;
					});
					await onRefresh();
				} catch (err) {
					setCommitted((prev) => {
						if (!prev.has(threadId)) return prev;
						const next = new Set(prev);
						next.delete(threadId);
						return next;
					});
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
