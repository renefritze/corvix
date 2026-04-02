/**
 * useBrowserNotifications
 *
 * Manages browser Notification API permission, deduplication, cooldown,
 * and per-cycle burst capping.  Detects newly-arrived unread items by
 * comparing the current snapshot to the set of previously-seen thread IDs
 * stored in localStorage.
 */
import { useCallback, useEffect, useRef, useState } from "preact/hooks";
import type { BrowserTabNotificationsConfig, DashboardItem } from "../types";

const STORAGE_KEY = "corvix.notifications.browser.seen";
const ENABLED_KEY = "corvix.notifications.browser.enabled";

export type NotifPermission = "default" | "granted" | "denied" | "unsupported";

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

function loadSeen(): Set<string> {
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (!raw) return new Set();
		const parsed: unknown = JSON.parse(raw);
		if (Array.isArray(parsed)) return new Set(parsed as string[]);
	} catch {
		// ignore parse errors
	}
	return new Set();
}

function saveSeen(seen: Set<string>): void {
	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify([...seen]));
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
	const supported = typeof window !== "undefined" && "Notification" in window;

	const getPermission = (): NotifPermission => {
		if (!supported) return "unsupported";
		return Notification.permission as NotifPermission;
	};

	const [permission, setPermission] = useState<NotifPermission>(getPermission);
	const [userEnabled, setUserEnabled] = useState<boolean>(loadUserEnabled);

	// Dedupe state: persisted across page refreshes via localStorage.
	const seenRef = useRef<Set<string>>(loadSeen());
	// Cooldown: timestamp (ms) after which the next burst is allowed.
	const cooldownUntilRef = useRef<number>(0);

	const active =
		supported &&
		userEnabled &&
		permission === "granted" &&
		(config?.enabled ?? true);

	const enable = useCallback(async () => {
		if (!supported) return;
		const result = await Notification.requestPermission();
		const perm = result as NotifPermission;
		setPermission(perm);
		if (perm === "granted") {
			setUserEnabled(true);
			saveUserEnabled(true);
		}
	}, [supported]);

	const disable = useCallback(() => {
		setUserEnabled(false);
		saveUserEnabled(false);
	}, []);

	// Fire browser notifications for newly-seen unread items.
	useEffect(() => {
		if (!active || !config) return;

		const now = Date.now();
		if (now < cooldownUntilRef.current) return;

		const maxPerCycle = config.max_per_cycle ?? 5;
		const cooldownMs = (config.cooldown_seconds ?? 10) * 1000;

		const newItems = items.filter(
			(item) => item.unread && !seenRef.current.has(item.thread_id),
		);

		// Cap burst and only mark actually-notified items as seen.
		const toNotify = newItems.slice(0, maxPerCycle);
		if (toNotify.length === 0) return;

		const updatedSeen = new Set(seenRef.current);
		for (const item of toNotify) {
			updatedSeen.add(item.thread_id);
		}
		seenRef.current = updatedSeen;
		saveSeen(updatedSeen);

		// Apply cooldown for this notification burst.
		cooldownUntilRef.current = now + cooldownMs;

		for (const item of toNotify) {
			try {
				const notif = new Notification(item.subject_title, {
					body: `${item.repository} · ${item.reason}`,
					tag: item.thread_id,
					icon: "/assets/favicon.svg",
				});
				notif.addEventListener("click", () => {
					if (item.web_url) {
						window.open(item.web_url, "_blank", "noopener,noreferrer");
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
