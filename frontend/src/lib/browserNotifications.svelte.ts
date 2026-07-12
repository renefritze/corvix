/**
 * Browser Notification permission, deduplication, cooldown and per-cycle burst
 * capping, ported from `useBrowserNotifications.ts`. Dedupe state is an
 * LRU-bounded `id -> last-seen` map persisted to localStorage and synced across
 * tabs via BroadcastChannel. Storage keys are kept verbatim.
 */
import { notificationKey } from "../types";
import type { BrowserTabNotificationsConfig, DashboardItem } from "../types";

const STORAGE_KEY = "corvix.notifications.browser.seen";
const ENABLED_KEY = "corvix.notifications.browser.enabled";
const SYNC_CHANNEL = "corvix.notifications.browser.sync";

const SEEN_MAX_ENTRIES = 500;
const SEEN_TTL_MS = 7 * 24 * 60 * 60 * 1000;
const SEEN_TOUCH_INTERVAL_MS = 24 * 60 * 60 * 1000;

export type NotifPermission = "default" | "granted" | "denied" | "unsupported";

type SeenMap = Map<string, number>;

interface SeenSyncMessage {
	type: "seen";
	entries: [string, number][];
}

function parseSeen(raw: string | null): SeenMap {
	const map: SeenMap = new Map();
	if (!raw) return map;
	try {
		const parsed: unknown = JSON.parse(raw);
		if (!Array.isArray(parsed)) return map;
		const now = Date.now();
		for (const entry of parsed) {
			if (typeof entry === "string") {
				map.set(entry, now);
			} else if (
				Array.isArray(entry) &&
				typeof entry[0] === "string" &&
				typeof entry[1] === "number"
			) {
				map.set(entry[0], entry[1]);
			}
		}
	} catch {
		// ignore parse errors
	}
	return map;
}

function pruneSeen(map: SeenMap, now: number): SeenMap {
	for (const [id, ts] of map) {
		if (now - ts > SEEN_TTL_MS) map.delete(id);
	}
	if (map.size > SEEN_MAX_ENTRIES) {
		const sorted = [...map.entries()].sort((a, b) => a[1] - b[1]);
		const excess = map.size - SEEN_MAX_ENTRIES;
		for (let i = 0; i < excess; i++) {
			map.delete(sorted[i][0]);
		}
	}
	return map;
}

function loadSeen(): SeenMap {
	try {
		return pruneSeen(parseSeen(localStorage.getItem(STORAGE_KEY)), Date.now());
	} catch {
		return new Map();
	}
}

function saveSeen(map: SeenMap): void {
	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify([...map.entries()]));
	} catch {
		// ignore storage errors
	}
}

function loadUserEnabled(): boolean {
	try {
		return localStorage.getItem(ENABLED_KEY) === "true";
	} catch {
		return false;
	}
}

function saveUserEnabled(value: boolean): void {
	try {
		localStorage.setItem(ENABLED_KEY, String(value));
	} catch {
		// ignore
	}
}

export class BrowserNotificationsStore {
	permission = $state<NotifPermission>("unsupported");
	#userEnabled = $state(false);
	#getItems: () => DashboardItem[];
	#getConfig: () => BrowserTabNotificationsConfig | null;

	#seen: SeenMap = loadSeen();
	#cooldownUntil = 0;
	#channel: BroadcastChannel | null = null;

	readonly supported =
		globalThis.window !== undefined && "Notification" in globalThis.window;

	constructor(
		getItems: () => DashboardItem[],
		getConfig: () => BrowserTabNotificationsConfig | null,
	) {
		this.#getItems = getItems;
		this.#getConfig = getConfig;
		this.permission = this.supported
			? (Notification.permission as NotifPermission)
			: "unsupported";
		this.#userEnabled = loadUserEnabled();
	}

	get #featureEnabled(): boolean {
		return this.#getConfig()?.enabled ?? false;
	}

	get active(): boolean {
		return (
			this.supported &&
			this.#userEnabled &&
			this.permission === "granted" &&
			this.#featureEnabled
		);
	}

	enable = async (): Promise<void> => {
		if (!this.#featureEnabled) return;
		if (!this.supported) return;
		const result = await Notification.requestPermission();
		this.permission = result as NotifPermission;
		if (this.permission === "granted") {
			this.#userEnabled = true;
			saveUserEnabled(true);
		}
	};

	disable = (): void => {
		if (!this.#featureEnabled) return;
		this.#userEnabled = false;
		saveUserEnabled(false);
	};

	bind(): void {
		// Subscribe to dedupe updates broadcast by other tabs.
		$effect(() => {
			if (globalThis.BroadcastChannel === undefined) return;
			const channel = new globalThis.BroadcastChannel(SYNC_CHANNEL);
			this.#channel = channel;
			const onMessage = (event: MessageEvent) => {
				const data = event.data as Partial<SeenSyncMessage> | null;
				if (data?.type !== "seen" || !Array.isArray(data.entries)) return;
				const seen = this.#seen;
				for (const entry of data.entries) {
					if (
						Array.isArray(entry) &&
						typeof entry[0] === "string" &&
						typeof entry[1] === "number"
					) {
						const prev = seen.get(entry[0]);
						if (prev === undefined || entry[1] > prev) seen.set(entry[0], entry[1]);
					}
				}
				pruneSeen(seen, Date.now());
			};
			channel.addEventListener("message", onMessage);
			return () => {
				channel.removeEventListener("message", onMessage);
				channel.close();
				this.#channel = null;
			};
		});

		// Fire browser notifications for newly-seen unread items.
		$effect(() => {
			const items = this.#getItems();
			const config = this.#getConfig();
			if (!this.active || !config) return;

			const now = Date.now();
			const seen = this.#seen;
			let changed = false;

			for (const item of items) {
				const key = notificationKey(item);
				const prevTs = seen.get(key);
				if (prevTs !== undefined && now - prevTs > SEEN_TOUCH_INTERVAL_MS) {
					seen.set(key, now);
					changed = true;
				}
			}

			const inCooldown = now < this.#cooldownUntil;
			const maxPerCycle = config.max_per_cycle ?? 5;
			const cooldownMs = (config.cooldown_seconds ?? 10) * 1000;

			const newItems = inCooldown
				? []
				: items.filter(
						(item) => item.unread && !seen.has(notificationKey(item)),
					);

			const toNotify = newItems.slice(0, maxPerCycle);

			if (toNotify.length > 0) {
				for (const item of toNotify) {
					seen.set(notificationKey(item), now);
				}
				this.#cooldownUntil = now + cooldownMs;
				changed = true;
			}

			if (changed) {
				pruneSeen(seen, now);
				saveSeen(seen);
			}

			if (toNotify.length > 0) {
				this.#channel?.postMessage({
					type: "seen",
					entries: toNotify.map(
						(item) => [notificationKey(item), now] as [string, number],
					),
				} satisfies SeenSyncMessage);
			}

			for (const item of toNotify) {
				try {
					const notif = new Notification(item.subject_title, {
						body: `${item.repository} · ${item.reason}`,
						tag: notificationKey(item),
						icon: "/assets/favicon.svg",
					});
					notif.addEventListener("click", () => {
						if (item.web_url) {
							globalThis.window.open(item.web_url, "_blank", "noopener,noreferrer");
						}
						notif.close();
					});
				} catch {
					// Notification constructor can throw in some environments.
				}
			}
		});
	}
}
