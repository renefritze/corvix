/**
 * useBrowserNotifications
 *
 * Manages browser Notification API permission, deduplication, cooldown,
 * and per-cycle burst capping.  Detects newly-arrived unread items by
 * comparing the current snapshot to the set of previously-seen thread IDs.
 *
 * Deduplication state is persisted in localStorage as an LRU-bounded map of
 * `id -> last-seen timestamp`, evicting entries past a TTL (and the oldest
 * entries beyond a maximum count) so it cannot grow unboundedly.  A
 * `BroadcastChannel` keeps the in-memory dedupe set synchronized across tabs,
 * so a notification fired in one tab is not re-fired in another.
 */
import { useCallback, useEffect, useRef, useState } from "preact/hooks";
import { notificationKey } from "../types";
import type { BrowserTabNotificationsConfig, DashboardItem } from "../types";

const STORAGE_KEY = "corvix.notifications.browser.seen";
const ENABLED_KEY = "corvix.notifications.browser.enabled";
const SYNC_CHANNEL = "corvix.notifications.browser.sync";

/** Maximum number of seen notification IDs retained (LRU upper bound). */
const SEEN_MAX_ENTRIES = 500;
/** Seen IDs untouched for longer than this are evicted (7 days, in ms). */
const SEEN_TTL_MS = 7 * 24 * 60 * 60 * 1000;
/**
 * Minimum age before a still-present item's seen timestamp is refreshed (1 day).
 * Avoids rewriting localStorage on every poll cycle while keeping live items
 * comfortably ahead of the TTL.
 */
const SEEN_TOUCH_INTERVAL_MS = 24 * 60 * 60 * 1000;

export type NotifPermission = "default" | "granted" | "denied" | "unsupported";

/** Map of notification id -> last-seen epoch milliseconds. */
type SeenMap = Map<string, number>;

interface SeenSyncMessage {
	type: "seen";
	entries: [string, number][];
}

interface UseBrowserNotificationsOptions {
	/** All current items from every group in the snapshot. */
	items: DashboardItem[];
	/** Server-side config for browser_tab target; null disables the feature. */
	config: BrowserTabNotificationsConfig | null;
}

interface UseBrowserNotificationsReturn {
	permission: NotifPermission;
	/** Whether the user has opted in *and* permission is granted. */
	active: boolean;
	/** Whether the browser supports the Notifications API. */
	supported: boolean;
	/** Request permission and enable notifications (must be called from a user gesture). */
	enable: () => Promise<void>;
	/** Disable browser notifications (does not revoke browser permission). */
	disable: () => void;
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
				// Legacy format: array of ids with no timestamp. Treat as seen now
				// so they survive at least one TTL window.
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

/**
 * Evict entries past the TTL and, if still over the maximum, drop the
 * least-recently-seen entries until within bounds. Mutates and returns `map`.
 */
function pruneSeen(map: SeenMap, now: number): SeenMap {
	for (const [id, ts] of map) {
		if (now - ts > SEEN_TTL_MS) map.delete(id);
	}
	if (map.size > SEEN_MAX_ENTRIES) {
		// Oldest first; delete the excess.
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

export function useBrowserNotifications({
	items,
	config,
}: UseBrowserNotificationsOptions): UseBrowserNotificationsReturn {
	const supported =
		globalThis.window !== undefined && "Notification" in globalThis.window;

	const getPermission = (): NotifPermission => {
		if (!supported) return "unsupported";
		return Notification.permission as NotifPermission;
	};

	const [permission, setPermission] = useState<NotifPermission>(getPermission);
	const [userEnabled, setUserEnabled] = useState<boolean>(loadUserEnabled);

	// Dedupe state: persisted across refreshes via localStorage and synchronized
	// across tabs via BroadcastChannel.
	const seenRef = useRef<SeenMap>(loadSeen());
	// Cooldown: timestamp (ms) after which the next burst is allowed.
	const cooldownUntilRef = useRef<number>(0);
	// Cross-tab sync channel (null when unsupported, e.g. older browsers/SSR).
	const channelRef = useRef<BroadcastChannel | null>(null);

	// Subscribe to dedupe updates broadcast by other tabs.
	useEffect(() => {
		if (globalThis.BroadcastChannel === undefined) return;
		const channel = new globalThis.BroadcastChannel(SYNC_CHANNEL);
		channelRef.current = channel;

		const onMessage = (event: MessageEvent) => {
			const data = event.data as Partial<SeenSyncMessage> | null;
			if (!data || data.type !== "seen" || !Array.isArray(data.entries)) {
				return;
			}
			const seen = seenRef.current;
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
			channelRef.current = null;
		};
	}, []);

	const featureEnabled = config?.enabled ?? false;

	const active =
		supported && userEnabled && permission === "granted" && featureEnabled;

	const enable = useCallback(async () => {
		if (!featureEnabled) return;
		if (!supported) return;
		const result = await Notification.requestPermission();
		const perm = result as NotifPermission;
		setPermission(perm);
		if (perm === "granted") {
			setUserEnabled(true);
			saveUserEnabled(true);
		}
	}, [featureEnabled, supported]);

	const disable = useCallback(() => {
		if (!featureEnabled) return;
		setUserEnabled(false);
		saveUserEnabled(false);
	}, [featureEnabled]);

	// Fire browser notifications for newly-seen unread items.
	useEffect(() => {
		if (!active || !config) return;

		const now = Date.now();
		const seen = seenRef.current;
		let changed = false;

		// Refresh the TTL of items still present so long-lived unread threads are
		// not re-notified once their original entry would have expired (LRU touch).
		// Only refresh entries that have aged noticeably; rewriting the timestamp
		// (and thus localStorage) on every poll cycle would be needless churn, and
		// the 1-day threshold keeps live items well clear of the 7-day TTL.
		for (const item of items) {
			const key = notificationKey(item);
			const prevTs = seen.get(key);
			if (prevTs !== undefined && now - prevTs > SEEN_TOUCH_INTERVAL_MS) {
				seen.set(key, now);
				changed = true;
			}
		}

		const inCooldown = now < cooldownUntilRef.current;

		const maxPerCycle = config.max_per_cycle ?? 5;
		const cooldownMs = (config.cooldown_seconds ?? 10) * 1000;

		const newItems = inCooldown
			? []
			: items.filter(
					(item) => item.unread && !seen.has(notificationKey(item)),
				);

		// Cap burst and only mark actually-notified items as seen.
		const toNotify = newItems.slice(0, maxPerCycle);

		if (toNotify.length > 0) {
			for (const item of toNotify) {
				seen.set(notificationKey(item), now);
			}
			// Apply cooldown for this notification burst.
			cooldownUntilRef.current = now + cooldownMs;
			changed = true;
		}

		if (changed) {
			pruneSeen(seen, now);
			saveSeen(seen);
		}

		if (toNotify.length > 0) {
			// Tell other tabs so they do not re-fire the same notifications.
			channelRef.current?.postMessage({
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
						globalThis.window.open(
							item.web_url,
							"_blank",
							"noopener,noreferrer",
						);
					}
					notif.close();
				});
			} catch {
				// Notification constructor can throw in some environments.
			}
		}
	}, [items, active, config]);

	return { permission, active, supported, enable, disable };
}
