import { useCallback, useEffect, useRef, useState } from "preact/hooks";
import { fetchSnapshot } from "../api";
import type { SnapshotPayload } from "../types";

const REFRESH_INTERVAL_MS = 15_000;

export function useSnapshot(dashboard: string | undefined) {
	const [snapshot, setSnapshot] = useState<SnapshotPayload | null>(null);
	const [loading, setLoading] = useState(true);
	const [refreshing, setRefreshing] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const inFlight = useRef(false);
	const needsReload = useRef(false);
	const queuedBackground = useRef(false);

	const load = useCallback(
		async (isBackground = false) => {
			if (inFlight.current) {
				needsReload.current = true;
				queuedBackground.current = queuedBackground.current || isBackground;
				return;
			}
			inFlight.current = true;
			if (isBackground) setRefreshing(true);
			try {
				const data = await fetchSnapshot(dashboard);
				setSnapshot(data);
				setError(null);
			} catch (err) {
				setError(err instanceof Error ? err.message : "Unknown error");
			} finally {
				inFlight.current = false;
				if (isBackground) setRefreshing(false);
				else setLoading(false);
				if (needsReload.current) {
					const nextIsBackground = queuedBackground.current;
					needsReload.current = false;
					queuedBackground.current = false;
					void load(nextIsBackground);
				}
			}
		},
		[dashboard],
	);

	useEffect(() => {
		setLoading(true);
		load(false);
		const id = setInterval(() => load(true), REFRESH_INTERVAL_MS);
		return () => clearInterval(id);
	}, [load]);

	const refresh = useCallback(() => load(true), [load]);

	return { snapshot, loading, refreshing, error, refresh };
}
