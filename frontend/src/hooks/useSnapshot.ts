import { useCallback, useEffect, useRef, useState } from "preact/hooks";
import { fetchSnapshot, snapshotEventsUrl } from "../api";
import type { SnapshotPayload } from "../types";

const REFRESH_INTERVAL_MS = 15_000;
type LoadMode = "initial" | "manual" | "auto";

function modeRank(mode: LoadMode): number {
	if (mode === "initial") return 3;
	if (mode === "manual") return 2;
	return 1;
}

/** Extract a human-readable message from a server-sent `snapshot-error` frame. */
function parseErrorDetail(raw: unknown): string {
	if (typeof raw !== "string") return "Snapshot stream error";
	try {
		const payload = JSON.parse(raw) as { detail?: unknown };
		if (typeof payload.detail === "string" && payload.detail) {
			return payload.detail;
		}
	} catch {
		// Non-JSON payload; fall through to the generic message.
	}
	return "Snapshot stream error";
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
					load(nextMode);
				}
			}
		},
		[dashboard],
	);

	useEffect(() => {
		setLoading(true);
		load("initial");

		// Without EventSource (e.g. older browsers, jsdom) keep the legacy
		// fixed-interval polling behavior.
		if (typeof EventSource === "undefined") {
			const id = setInterval(() => load("auto"), REFRESH_INTERVAL_MS);
			return () => clearInterval(id);
		}

		// SSE path: the server pushes a snapshot only when the data changes, so
		// no interval is needed. We poll only as a fallback once the connection
		// is permanently closed (e.g. the endpoint is unavailable).
		let pollId: ReturnType<typeof setInterval> | null = null;
		const startPollingFallback = () => {
			if (pollId === null) {
				pollId = setInterval(() => load("auto"), REFRESH_INTERVAL_MS);
			}
		};

		const source = new EventSource(snapshotEventsUrl(dashboard));
		source.addEventListener("snapshot", (event) => {
			try {
				const data = JSON.parse(
					(event as MessageEvent).data,
				) as SnapshotPayload;
				setSnapshot(data);
				setError(null);
				setLoading(false);
			} catch {
				// Ignore malformed frames; the next valid push will recover.
			}
		});
		source.addEventListener("snapshot-error", (event) => {
			const detail = parseErrorDetail((event as MessageEvent).data);
			setError(detail);
		});
		source.onerror = () => {
			// EventSource auto-reconnects on transient errors; only fall back to
			// polling once the connection is definitively closed.
			if (source.readyState === EventSource.CLOSED) {
				startPollingFallback();
			}
		};

		return () => {
			source.close();
			if (pollId !== null) clearInterval(pollId);
		};
	}, [load, dashboard]);

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
