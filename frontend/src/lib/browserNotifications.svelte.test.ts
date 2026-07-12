import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { makeItem } from "../test/fixtures";
import { flushSync, root } from "../test/runes.svelte";
import type { BrowserTabNotificationsConfig, DashboardItem } from "../types";
import { BrowserNotificationsStore } from "./browserNotifications.svelte";

const ENABLED_KEY = "corvix.notifications.browser.enabled";
const SEEN_KEY = "corvix.notifications.browser.seen";

// --- Notification mock --------------------------------------------------

class NotificationMock {
	static permission: NotificationPermission = "default";
	static requestPermission = vi.fn(async () => NotificationMock.permission);
	static instances: NotificationMock[] = [];

	title: string;
	options?: NotificationOptions;
	close = vi.fn();
	#clickHandler: (() => void) | null = null;

	constructor(title: string, options?: NotificationOptions) {
		this.title = title;
		this.options = options;
		NotificationMock.instances.push(this);
	}

	addEventListener(type: string, listener: () => void): void {
		if (type === "click") this.#clickHandler = listener;
	}

	triggerClick(): void {
		this.#clickHandler?.();
	}
}

// --- BroadcastChannel mock ---------------------------------------------

class BroadcastChannelMock {
	static channels: BroadcastChannelMock[] = [];
	name: string;
	closed = false;
	#listeners: ((event: MessageEvent) => void)[] = [];

	constructor(name: string) {
		this.name = name;
		BroadcastChannelMock.channels.push(this);
	}

	addEventListener(type: string, listener: (event: MessageEvent) => void): void {
		if (type === "message") this.#listeners.push(listener);
	}

	removeEventListener(
		type: string,
		listener: (event: MessageEvent) => void,
	): void {
		if (type === "message") {
			this.#listeners = this.#listeners.filter((l) => l !== listener);
		}
	}

	postMessage(data: unknown): void {
		for (const channel of BroadcastChannelMock.channels) {
			if (channel === this || channel.name !== this.name || channel.closed) {
				continue;
			}
			for (const listener of channel.#listeners) {
				listener({ data } as MessageEvent);
			}
		}
	}

	close(): void {
		this.closed = true;
		BroadcastChannelMock.channels = BroadcastChannelMock.channels.filter(
			(c) => c !== this,
		);
	}
}

// --- helpers ------------------------------------------------------------

const originalNotification = Object.getOwnPropertyDescriptor(
	globalThis,
	"Notification",
);
const originalBroadcastChannel = Object.getOwnPropertyDescriptor(
	globalThis,
	"BroadcastChannel",
);

function installNotification(permission: NotificationPermission = "default"): void {
	NotificationMock.permission = permission;
	NotificationMock.instances = [];
	NotificationMock.requestPermission = vi.fn(async () => {
		NotificationMock.permission = "granted";
		return "granted";
	});
	Object.defineProperty(globalThis, "Notification", {
		value: NotificationMock,
		writable: true,
		configurable: true,
	});
	if (globalThis.window !== undefined) {
		Object.defineProperty(globalThis.window, "Notification", {
			value: NotificationMock,
			writable: true,
			configurable: true,
		});
	}
}

function installBroadcastChannel(): void {
	BroadcastChannelMock.channels = [];
	Object.defineProperty(globalThis, "BroadcastChannel", {
		value: BroadcastChannelMock,
		writable: true,
		configurable: true,
	});
}

function removeNotification(): void {
	Reflect.deleteProperty(globalThis, "Notification");
	if (globalThis.window !== undefined) {
		Reflect.deleteProperty(globalThis.window, "Notification");
	}
}

const activeConfig: BrowserTabNotificationsConfig = {
	enabled: true,
	max_per_cycle: 5,
	cooldown_seconds: 10,
};

/**
 * Constructs a store whose item list is a reactive `$state`, binds it inside an
 * `$effect.root`, and exposes a `setItems` to drive the effect. Because the fire
 * effect reads `getItems()`, reassigning the reactive array (then flushing)
 * re-runs it exactly as a live snapshot update would.
 */
function mountStore(
	initialItems: DashboardItem[],
	config: BrowserTabNotificationsConfig | null,
) {
	const { value, dispose } = root(() => {
		let items = $state(initialItems);
		const store = new BrowserNotificationsStore(
			() => items,
			() => config,
		);
		store.bind();
		return {
			store,
			setItems: (next: DashboardItem[]) => {
				items = next;
			},
		};
	});
	return { ...value, dispose };
}

// --- tests --------------------------------------------------------------

describe("BrowserNotificationsStore", () => {
	beforeEach(() => {
		installNotification("default");
		installBroadcastChannel();
	});

	afterEach(() => {
		if (originalNotification) {
			Object.defineProperty(globalThis, "Notification", originalNotification);
		} else {
			removeNotification();
		}
		if (originalBroadcastChannel) {
			Object.defineProperty(
				globalThis,
				"BroadcastChannel",
				originalBroadcastChannel,
			);
		} else {
			Reflect.deleteProperty(globalThis, "BroadcastChannel");
		}
	});

	it("reports unsupported when Notification is absent", () => {
		removeNotification();
		const store = new BrowserNotificationsStore(
			() => [makeItem()],
			() => activeConfig,
		);
		expect(store.supported).toBe(false);
		expect(store.permission).toBe("unsupported");
		expect(store.active).toBe(false);
	});

	it("reflects the current Notification permission", () => {
		installNotification("granted");
		const granted = new BrowserNotificationsStore(
			() => [],
			() => activeConfig,
		);
		expect(granted.supported).toBe(true);
		expect(granted.permission).toBe("granted");

		installNotification("denied");
		const denied = new BrowserNotificationsStore(
			() => [],
			() => activeConfig,
		);
		expect(denied.permission).toBe("denied");
	});

	it("enable() requests permission and persists the enabled flag", async () => {
		installNotification("default");
		const store = new BrowserNotificationsStore(
			() => [],
			() => activeConfig,
		);

		await store.enable();

		expect(NotificationMock.requestPermission).toHaveBeenCalledTimes(1);
		expect(store.permission).toBe("granted");
		expect(localStorage.getItem(ENABLED_KEY)).toBe("true");
	});

	it("enable() does nothing when the feature is disabled in config", async () => {
		installNotification("default");
		const store = new BrowserNotificationsStore(
			() => [],
			() => ({ enabled: false, max_per_cycle: 5, cooldown_seconds: 10 }),
		);

		await store.enable();

		expect(NotificationMock.requestPermission).not.toHaveBeenCalled();
		expect(localStorage.getItem(ENABLED_KEY)).toBeNull();
	});

	it("enable() does not persist when permission is not granted", async () => {
		installNotification("default");
		NotificationMock.requestPermission = vi.fn(async () => {
			NotificationMock.permission = "denied";
			return "denied";
		});
		const store = new BrowserNotificationsStore(
			() => [],
			() => activeConfig,
		);

		await store.enable();

		expect(store.permission).toBe("denied");
		expect(localStorage.getItem(ENABLED_KEY)).toBeNull();
	});

	it("disable() clears the enabled flag", () => {
		installNotification("granted");
		localStorage.setItem(ENABLED_KEY, "true");
		const store = new BrowserNotificationsStore(
			() => [],
			() => activeConfig,
		);

		store.disable();

		expect(localStorage.getItem(ENABLED_KEY)).toBe("false");
		expect(store.active).toBe(false);
	});

	it("is active only when supported, enabled, granted and config-enabled", () => {
		installNotification("granted");
		localStorage.setItem(ENABLED_KEY, "true");
		const store = new BrowserNotificationsStore(
			() => [],
			() => activeConfig,
		);
		expect(store.active).toBe(true);

		installNotification("default");
		localStorage.setItem(ENABLED_KEY, "true");
		const notGranted = new BrowserNotificationsStore(
			() => [],
			() => activeConfig,
		);
		expect(notGranted.active).toBe(false);

		installNotification("granted");
		localStorage.removeItem(ENABLED_KEY);
		const notEnabled = new BrowserNotificationsStore(
			() => [],
			() => activeConfig,
		);
		expect(notEnabled.active).toBe(false);

		installNotification("granted");
		localStorage.setItem(ENABLED_KEY, "true");
		const configOff = new BrowserNotificationsStore(
			() => [],
			() => ({ enabled: false, max_per_cycle: 5, cooldown_seconds: 10 }),
		);
		expect(configOff.active).toBe(false);
	});

	it("fires a notification for a new unread item when active", () => {
		installNotification("granted");
		localStorage.setItem(ENABLED_KEY, "true");
		const { dispose } = mountStore(
			[makeItem({ thread_id: "1", subject_title: "One" })],
			activeConfig,
		);

		expect(NotificationMock.instances).toHaveLength(1);
		expect(NotificationMock.instances[0]?.title).toBe("One");
		expect(NotificationMock.instances[0]?.options?.tag).toBe("primary:1");
		dispose();
	});

	it("does not fire when the store is not active", () => {
		installNotification("granted");
		// userEnabled flag never set -> inactive.
		const { dispose } = mountStore([makeItem()], activeConfig);
		expect(NotificationMock.instances).toHaveLength(0);
		dispose();
	});

	it("respects the max_per_cycle burst cap", () => {
		installNotification("granted");
		localStorage.setItem(ENABLED_KEY, "true");
		const { dispose } = mountStore(
			[
				makeItem({ thread_id: "1", subject_title: "One" }),
				makeItem({ thread_id: "2", subject_title: "Two" }),
			],
			{ enabled: true, max_per_cycle: 1, cooldown_seconds: 10 },
		);

		expect(NotificationMock.instances).toHaveLength(1);
		expect(NotificationMock.instances[0]?.title).toBe("One");
		dispose();
	});

	it("only notifies unread items", () => {
		installNotification("granted");
		localStorage.setItem(ENABLED_KEY, "true");
		const { dispose } = mountStore(
			[
				makeItem({ thread_id: "1", subject_title: "Read", unread: false }),
				makeItem({ thread_id: "2", subject_title: "Unread" }),
			],
			activeConfig,
		);

		expect(NotificationMock.instances).toHaveLength(1);
		expect(NotificationMock.instances[0]?.title).toBe("Unread");
		dispose();
	});

	it("dedupes against persisted seen ids", () => {
		installNotification("granted");
		localStorage.setItem(ENABLED_KEY, "true");
		localStorage.setItem(SEEN_KEY, JSON.stringify(["primary:1"]));

		const { dispose } = mountStore(
			[
				makeItem({ thread_id: "1", subject_title: "Seen" }),
				makeItem({ thread_id: "2", subject_title: "New" }),
			],
			activeConfig,
		);

		expect(NotificationMock.instances).toHaveLength(1);
		expect(NotificationMock.instances[0]?.title).toBe("New");
		dispose();
	});

	it("re-notifies items whose seen entry expired (TTL prune)", () => {
		installNotification("granted");
		localStorage.setItem(ENABLED_KEY, "true");
		const stale = Date.now() - 8 * 24 * 60 * 60 * 1000; // 8 days > 7-day TTL
		localStorage.setItem(SEEN_KEY, JSON.stringify([["primary:1", stale]]));

		const { dispose } = mountStore(
			[makeItem({ thread_id: "1", subject_title: "Stale" })],
			activeConfig,
		);

		expect(NotificationMock.instances).toHaveLength(1);
		expect(NotificationMock.instances[0]?.title).toBe("Stale");
		dispose();
	});

	it("does not re-notify a still-fresh seen item", () => {
		installNotification("granted");
		localStorage.setItem(ENABLED_KEY, "true");
		localStorage.setItem(SEEN_KEY, JSON.stringify([["primary:1", Date.now()]]));

		const { dispose } = mountStore(
			[makeItem({ thread_id: "1", subject_title: "Fresh" })],
			activeConfig,
		);

		expect(NotificationMock.instances).toHaveLength(0);
		dispose();
	});

	it("bounds the seen set to prevent unbounded growth (LRU prune)", () => {
		installNotification("granted");
		localStorage.setItem(ENABLED_KEY, "true");
		const now = Date.now();
		const seeded = Array.from(
			{ length: 500 },
			(_, i) => [`old:${i}`, now - 1000 - i] as [string, number],
		);
		localStorage.setItem(SEEN_KEY, JSON.stringify(seeded));

		const { dispose } = mountStore(
			[makeItem({ thread_id: "new", subject_title: "New" })],
			activeConfig,
		);

		expect(NotificationMock.instances).toHaveLength(1);

		const saved = JSON.parse(localStorage.getItem(SEEN_KEY) ?? "[]") as [
			string,
			number,
		][];
		expect(saved).toHaveLength(500);
		const ids = new Set(saved.map((entry) => entry[0]));
		expect(ids.has("primary:new")).toBe(true);
		expect(ids.has("old:499")).toBe(false);
		dispose();
	});

	it("refreshes only sufficiently-aged seen timestamps", () => {
		installNotification("granted");
		localStorage.setItem(ENABLED_KEY, "true");
		const now = Date.now();
		const fresh = now - 60 * 1000; // below the 24h touch interval
		const aged = now - 2 * 24 * 60 * 60 * 1000; // above the touch interval
		localStorage.setItem(
			SEEN_KEY,
			JSON.stringify([
				["primary:fresh", fresh],
				["primary:aged", aged],
			]),
		);

		const { dispose } = mountStore(
			[
				makeItem({ thread_id: "fresh", subject_title: "Fresh" }),
				makeItem({ thread_id: "aged", subject_title: "Aged" }),
			],
			activeConfig,
		);

		// Both already seen -> nothing fired.
		expect(NotificationMock.instances).toHaveLength(0);

		const saved = new Map<string, number>(
			JSON.parse(localStorage.getItem(SEEN_KEY) ?? "[]") as [string, number][],
		);
		expect(saved.get("primary:aged")).toBeGreaterThan(aged);
		expect(saved.get("primary:fresh")).toBe(fresh);
		dispose();
	});

	it("suppresses new bursts until the cooldown expires", () => {
		vi.useFakeTimers();
		try {
			installNotification("granted");
			localStorage.setItem(ENABLED_KEY, "true");
			const config: BrowserTabNotificationsConfig = {
				enabled: true,
				max_per_cycle: 5,
				cooldown_seconds: 1,
			};
			const { setItems, dispose } = mountStore(
				[makeItem({ thread_id: "1", subject_title: "One" })],
				config,
			);
			expect(NotificationMock.instances).toHaveLength(1);

			// Still within cooldown: the second item must not fire.
			setItems([
				makeItem({ thread_id: "1", subject_title: "One" }),
				makeItem({ thread_id: "2", subject_title: "Two" }),
			]);
			flushSync();
			expect(NotificationMock.instances).toHaveLength(1);

			vi.advanceTimersByTime(1100);
			setItems([
				makeItem({ thread_id: "1", subject_title: "One" }),
				makeItem({ thread_id: "2", subject_title: "Two" }),
			]);
			flushSync();

			expect(NotificationMock.instances).toHaveLength(2);
			expect(NotificationMock.instances[1]?.title).toBe("Two");
			dispose();
		} finally {
			vi.useRealTimers();
		}
	});

	it("opens web_url in a new tab when a notification is clicked", () => {
		installNotification("granted");
		localStorage.setItem(ENABLED_KEY, "true");
		const { dispose } = mountStore(
			[makeItem({ thread_id: "c", web_url: "https://example.com/pr/1" })],
			activeConfig,
		);

		expect(NotificationMock.instances).toHaveLength(1);
		NotificationMock.instances[0]?.triggerClick();
		expect(globalThis.window.open).toHaveBeenCalledWith(
			"https://example.com/pr/1",
			"_blank",
			"noopener,noreferrer",
		);
		dispose();
	});

	it("syncs deduplication across tabs via BroadcastChannel", () => {
		installNotification("granted");
		localStorage.setItem(ENABLED_KEY, "true");
		const item = makeItem({ thread_id: "shared", subject_title: "Shared" });

		// Tab B subscribes first with no items.
		const tabB = mountStore([], activeConfig);
		// Tab A fires the notification and broadcasts the seen id.
		const tabA = mountStore([item], activeConfig);
		expect(NotificationMock.instances).toHaveLength(1);

		// Tab B now receives the same unread item; the broadcast must dedupe it.
		tabB.setItems([item]);
		flushSync();
		expect(NotificationMock.instances).toHaveLength(1);

		tabA.dispose();
		tabB.dispose();
	});

	it("skips channel setup when BroadcastChannel is unavailable", () => {
		installNotification("granted");
		Reflect.deleteProperty(globalThis, "BroadcastChannel");
		localStorage.setItem(ENABLED_KEY, "true");

		const { dispose } = mountStore(
			[makeItem({ thread_id: "1", subject_title: "One" })],
			activeConfig,
		);

		// Still notifies even without cross-tab sync.
		expect(NotificationMock.instances).toHaveLength(1);
		dispose();
	});
});
