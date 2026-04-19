import { useCallback, useEffect, useRef, useState } from "preact/hooks";
import { fetchSnapshot } from "../api";
import type { SnapshotPayload } from "../types";

const REFRESH_INTERVAL_MS = 15_000;
type LoadMode = "initial" | "manual" | "auto";

function modeRank(mode: LoadMode): number {
	if (mode === "initial") return 3;
	if (mode === "manual") return 2;
	return 1;
}

export function useSnapshot(dashboard: string | undefined) {
	const [snapshot, setSnapshot] = useState<SnapshotPayload | null>(null);
	const [loading, setLoading] = useState(true);
	const [manualRefreshing, setManualRefreshing] = useState(false);
	const [autoRefreshing, setAutoRefreshing] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const inFlight = useRef(false);
	const needsReload = useRef(false);
	const queuedMode = useRef<LoadMode | null>(null);

	const load = useCallback(
		async (mode: LoadMode = "manual") => {
			if (inFlight.current) {
				needsReload.current = true;
				if (
					queuedMode.current === null ||
					modeRank(mode) > modeRank(queuedMode.current)
				) {
					queuedMode.current = mode;
				}
				return;
			}
			inFlight.current = true;
			if (mode === "manual") setManualRefreshing(true);
			if (mode === "auto") setAutoRefreshing(true);
			try {
				const data = await fetchSnapshot(dashboard);
				setSnapshot(data);
				setError(null);
			} catch (err) {
				setError(err instanceof Error ? err.message : "Unknown error");
			} finally {
				inFlight.current = false;
				if (mode === "manual") setManualRefreshing(false);
				if (mode === "auto") setAutoRefreshing(false);
				if (mode === "initial") setLoading(false);
				if (needsReload.current) {
					const nextMode = queuedMode.current ?? "auto";
					needsReload.current = false;
					queuedMode.current = null;
					void load(nextMode);
				}
			}
		},
		[dashboard],
	);

	useEffect(() => {
		setLoading(true);
		void load("initial");
		const id = setInterval(() => void load("auto"), REFRESH_INTERVAL_MS);
		return () => clearInterval(id);
	}, [load]);

	const refresh = useCallback(() => load("manual"), [load]);
	const refreshing = manualRefreshing || autoRefreshing;

	return {
		snapshot,
		loading,
		refreshing,
		manualRefreshing,
		autoRefreshing,
		error,
		refresh,
	};
}
