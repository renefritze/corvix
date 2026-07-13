/**
 * Snapshot data source, ported from `useSnapshot.ts`.
 *
 * Opens an SSE `EventSource` on `/api/v1/events` and applies pushed snapshots;
 * falls back to 15s polling only once the connection is definitively CLOSED (or
 * when EventSource is unavailable, e.g. jsdom). In-flight loads coalesce, with
 * the queued reload keeping the highest-ranked LoadMode. `bind()` wires the
 * (re)subscription to a reactive dashboard key via `$effect`, tearing the
 * previous stream down before opening the next.
 */
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

export class SnapshotStore {
	snapshot = $state<SnapshotPayload | null>(null);
	loading = $state(true);
	manualRefreshing = $state(false);
	autoRefreshing = $state(false);
	error = $state<string | null>(null);

	#dashboard: string | undefined = undefined;
	#inFlight = false;
	#needsReload = false;
	#queuedMode: LoadMode | null = null;

	get refreshing(): boolean {
		return this.manualRefreshing || this.autoRefreshing;
	}

	readonly #load = async (mode: LoadMode = "manual"): Promise<void> => {
		if (this.#inFlight) {
			this.#needsReload = true;
			if (
				this.#queuedMode === null ||
				modeRank(mode) > modeRank(this.#queuedMode)
			) {
				this.#queuedMode = mode;
			}
			return;
		}
		this.#inFlight = true;
		if (mode === "manual") this.manualRefreshing = true;
		if (mode === "auto") this.autoRefreshing = true;
		try {
			const data = await fetchSnapshot(this.#dashboard);
			this.snapshot = data;
			this.error = null;
		} catch (err) {
			this.error = err instanceof Error ? err.message : "Unknown error";
		} finally {
			this.#inFlight = false;
			if (mode === "manual") this.manualRefreshing = false;
			if (mode === "auto") this.autoRefreshing = false;
			if (mode === "initial") this.loading = false;
			if (this.#needsReload) {
				const nextMode = this.#queuedMode ?? "auto";
				this.#needsReload = false;
				this.#queuedMode = null;
				void this.#load(nextMode);
			}
		}
	};

	refresh = (): Promise<void> => {
		return this.#load("manual");
	};

	#start(dashboard: string | undefined): () => void {
		this.#dashboard = dashboard;
		this.loading = true;
		void this.#load("initial");

		// Without EventSource (older browsers, jsdom) keep fixed-interval polling.
		if (typeof EventSource === "undefined") {
			const id = setInterval(() => void this.#load("auto"), REFRESH_INTERVAL_MS);
			return () => clearInterval(id);
		}

		// `active` guards against late events firing after teardown (e.g. an
		// `onerror` dispatched during/after `source.close()`).
		let active = true;
		let pollId: ReturnType<typeof setInterval> | null = null;
		const startPollingFallback = () => {
			if (active && pollId === null) {
				pollId = setInterval(() => {
					if (active) void this.#load("auto");
				}, REFRESH_INTERVAL_MS);
			}
		};

		const source = new EventSource(snapshotEventsUrl(dashboard));
		source.addEventListener("snapshot", (event) => {
			if (!active) return;
			try {
				const data = JSON.parse((event as MessageEvent).data) as SnapshotPayload;
				this.snapshot = data;
				this.error = null;
				this.loading = false;
			} catch {
				// Ignore malformed frames; the next valid push recovers.
			}
		});
		source.addEventListener("snapshot-error", (event) => {
			if (!active) return;
			this.error = parseErrorDetail((event as MessageEvent).data);
		});
		source.onerror = () => {
			if (active && source.readyState === EventSource.CLOSED) {
				startPollingFallback();
			}
		};

		return () => {
			active = false;
			source.close();
			if (pollId !== null) clearInterval(pollId);
		};
	}

	/** (Re)subscribe whenever the reactive dashboard key changes. */
	bind(getDashboard: () => string | undefined): void {
		$effect(() => {
			const dashboard = getDashboard();
			return this.#start(dashboard);
		});
	}
}
