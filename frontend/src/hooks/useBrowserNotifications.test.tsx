import { render, screen, waitFor } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { makeItem } from "../test/fixtures";
import type { BrowserTabNotificationsConfig, DashboardItem } from "../types";
import { useBrowserNotifications } from "./useBrowserNotifications";

class NotificationMock {
	private static permissionState: NotificationPermission = "default";
	static readonly requestPermission = vi.fn(async () => "granted");
	static readonly instances: NotificationMock[] = [];

	static get permission(): NotificationPermission {
		return NotificationMock.permissionState;
	}

	static setPermission(value: NotificationPermission): void {
		NotificationMock.permissionState = value;
	}

	readonly title: string;
	readonly options?: NotificationOptions;
	readonly close = vi.fn();
	private clickHandler: (() => void) | null = null;

	constructor(title: string, options?: NotificationOptions) {
		this.title = title;
		this.options = options;
		NotificationMock.instances.push(this);
	}

	addEventListener(type: string, listener: () => void) {
		if (type === "click") this.clickHandler = listener;
	}

	triggerClick() {
		this.clickHandler?.();
	}
}

function Harness({
	items,
	config,
}: Readonly<{
	items: DashboardItem[];
	config: BrowserTabNotificationsConfig | null;
}>) {
	const { active, permission, enable, disable, supported } =
		useBrowserNotifications({
			items,
			config,
		});

	return (
		<div>
			<div data-testid="active">{String(active)}</div>
			<div data-testid="permission">{permission}</div>
			<div data-testid="supported">{String(supported)}</div>
			<button type="button" onClick={() => void enable()}>
				enable
			</button>
			<button type="button" onClick={disable}>
				disable
			</button>
		</div>
	);
}

describe("useBrowserNotifications", () => {
	beforeEach(() => {
		NotificationMock.instances.length = 0;
		NotificationMock.setPermission("default");
		NotificationMock.requestPermission.mockImplementation(async () => {
			NotificationMock.setPermission("granted");
			return "granted";
		});
		Object.defineProperty(globalThis.window, "Notification", {
			value: NotificationMock,
			writable: true,
			configurable: true,
		});
	});

	it("does not activate when permission is denied", async () => {
		const user = userEvent.setup();
		NotificationMock.requestPermission.mockImplementation(async () => {
			NotificationMock.setPermission("denied");
			return "denied";
		});

		render(
			<Harness
				items={[makeItem()]}
				config={{ enabled: true, max_per_cycle: 3, cooldown_seconds: 2 }}
			/>,
		);

		await user.click(screen.getByRole("button", { name: "enable" }));

		await waitFor(() => {
			expect(screen.getByTestId("permission")).toHaveTextContent("denied");
		});
		expect(screen.getByTestId("active")).toHaveTextContent("false");
		expect(NotificationMock.instances).toHaveLength(0);
	});

	it("reports unsupported when Notification API is unavailable", () => {
		Reflect.deleteProperty(globalThis.window, "Notification");

		render(
			<Harness
				items={[makeItem()]}
				config={{ enabled: true, max_per_cycle: 3, cooldown_seconds: 2 }}
			/>,
		);

		expect(screen.getByTestId("supported")).toHaveTextContent("false");
		expect(screen.getByTestId("permission")).toHaveTextContent("unsupported");
		expect(screen.getByTestId("active")).toHaveTextContent("false");
	});

	it("enables notifications and respects max_per_cycle", async () => {
		const user = userEvent.setup();
		const config: BrowserTabNotificationsConfig = {
			enabled: true,
			max_per_cycle: 1,
			cooldown_seconds: 10,
		};
		const items = [
			makeItem({ thread_id: "1", subject_title: "One" }),
			makeItem({ thread_id: "2", subject_title: "Two" }),
		];

		render(<Harness items={items} config={config} />);
		await user.click(screen.getByRole("button", { name: "enable" }));

		await waitFor(() => {
			expect(screen.getByTestId("active")).toHaveTextContent("true");
		});
		await waitFor(() => {
			expect(NotificationMock.instances).toHaveLength(1);
		});
		expect(NotificationMock.instances[0]?.title).toBe("One");
	});

	it("disables active notifications", async () => {
		const user = userEvent.setup();
		const config: BrowserTabNotificationsConfig = {
			enabled: true,
			max_per_cycle: 5,
			cooldown_seconds: 1,
		};

		render(<Harness items={[makeItem()]} config={config} />);
		await user.click(screen.getByRole("button", { name: "enable" }));
		await waitFor(() => {
			expect(screen.getByTestId("active")).toHaveTextContent("true");
		});

		await user.click(screen.getByRole("button", { name: "disable" }));
		expect(screen.getByTestId("active")).toHaveTextContent("false");
	});

	it("does nothing when feature is disabled in config", async () => {
		const user = userEvent.setup();
		render(
			<Harness
				items={[makeItem()]}
				config={{ enabled: false, max_per_cycle: 3, cooldown_seconds: 2 }}
			/>,
		);

		await user.click(screen.getByRole("button", { name: "enable" }));
		expect(screen.getByTestId("active")).toHaveTextContent("false");
		expect(NotificationMock.requestPermission).not.toHaveBeenCalled();
		expect(NotificationMock.instances).toHaveLength(0);
	});

	it("opens web_url when notification is clicked", async () => {
		const user = userEvent.setup();
		render(
			<Harness
				items={[
					makeItem({ thread_id: "x-1", web_url: "https://example.com/pr/1" }),
				]}
				config={{ enabled: true, max_per_cycle: 5, cooldown_seconds: 2 }}
			/>,
		);

		await user.click(screen.getByRole("button", { name: "enable" }));
		await waitFor(() => {
			expect(NotificationMock.instances).toHaveLength(1);
		});
		NotificationMock.instances[0]?.triggerClick();
		expect(globalThis.window.open).toHaveBeenCalledWith(
			"https://example.com/pr/1",
			"_blank",
			"noopener,noreferrer",
		);
	});

	it("dedupes notifications using persisted seen ids", async () => {
		NotificationMock.setPermission("granted");
		localStorage.setItem("corvix.notifications.browser.enabled", "true");
		localStorage.setItem(
			"corvix.notifications.browser.seen",
			JSON.stringify(["primary:1"]),
		);

		const items = [
			makeItem({ thread_id: "1", subject_title: "Seen" }),
			makeItem({ thread_id: "2", subject_title: "New" }),
		];

		const { rerender } = render(
			<Harness
				items={items}
				config={{ enabled: true, max_per_cycle: 5, cooldown_seconds: 2 }}
			/>,
		);

		await waitFor(() => {
			expect(NotificationMock.instances).toHaveLength(1);
		});
		expect(NotificationMock.instances[0]?.title).toBe("New");

		rerender(
			<Harness
				items={[...items]}
				config={{ enabled: true, max_per_cycle: 5, cooldown_seconds: 2 }}
			/>,
		);
		expect(NotificationMock.instances).toHaveLength(1);
	});

	it("re-notifies unread items whose seen entry has expired (TTL)", async () => {
		NotificationMock.setPermission("granted");
		localStorage.setItem("corvix.notifications.browser.enabled", "true");
		const stale = Date.now() - 8 * 24 * 60 * 60 * 1000; // 8 days > 7-day TTL
		localStorage.setItem(
			"corvix.notifications.browser.seen",
			JSON.stringify([["primary:1", stale]]),
		);

		render(
			<Harness
				items={[makeItem({ thread_id: "1", subject_title: "Stale" })]}
				config={{ enabled: true, max_per_cycle: 5, cooldown_seconds: 2 }}
			/>,
		);

		await waitFor(() => {
			expect(NotificationMock.instances).toHaveLength(1);
		});
		expect(NotificationMock.instances[0]?.title).toBe("Stale");
	});

	it("does not re-notify unread items whose seen entry is still fresh", async () => {
		NotificationMock.setPermission("granted");
		localStorage.setItem("corvix.notifications.browser.enabled", "true");
		localStorage.setItem(
			"corvix.notifications.browser.seen",
			JSON.stringify([["primary:1", Date.now()]]),
		);

		render(
			<Harness
				items={[makeItem({ thread_id: "1", subject_title: "Fresh" })]}
				config={{ enabled: true, max_per_cycle: 5, cooldown_seconds: 2 }}
			/>,
		);

		await new Promise((resolve) => setTimeout(resolve, 50));
		expect(NotificationMock.instances).toHaveLength(0);
	});

	it("refreshes only sufficiently-aged seen timestamps to limit writes", async () => {
		NotificationMock.setPermission("granted");
		localStorage.setItem("corvix.notifications.browser.enabled", "true");
		const now = Date.now();
		const fresh = now - 60 * 1000; // 1 minute ago: below the touch interval
		const aged = now - 2 * 24 * 60 * 60 * 1000; // 2 days ago: above the interval
		localStorage.setItem(
			"corvix.notifications.browser.seen",
			JSON.stringify([
				["primary:fresh", fresh],
				["primary:aged", aged],
			]),
		);

		render(
			<Harness
				items={[
					makeItem({ thread_id: "fresh", subject_title: "Fresh" }),
					makeItem({ thread_id: "aged", subject_title: "Aged" }),
				]}
				config={{ enabled: true, max_per_cycle: 5, cooldown_seconds: 2 }}
			/>,
		);

		// Both items are already seen, so nothing is notified.
		await new Promise((resolve) => setTimeout(resolve, 50));
		expect(NotificationMock.instances).toHaveLength(0);

		const saved = new Map<string, number>(
			JSON.parse(
				localStorage.getItem("corvix.notifications.browser.seen") ?? "[]",
			) as [string, number][],
		);
		// The aged entry was refreshed; the fresh one was left untouched.
		expect(saved.get("primary:aged")).toBeGreaterThan(aged);
		expect(saved.get("primary:fresh")).toBe(fresh);
	});

	it("bounds the seen set to prevent unbounded growth", async () => {
		NotificationMock.setPermission("granted");
		localStorage.setItem("corvix.notifications.browser.enabled", "true");
		const now = Date.now();
		// Seed exactly the maximum number of (fresh) entries.
		const seeded = Array.from(
			{ length: 500 },
			(_, i) => [`old:${i}`, now - 1_000 - i] as [string, number],
		);
		localStorage.setItem(
			"corvix.notifications.browser.seen",
			JSON.stringify(seeded),
		);

		render(
			<Harness
				items={[makeItem({ thread_id: "new", subject_title: "New" })]}
				config={{ enabled: true, max_per_cycle: 5, cooldown_seconds: 2 }}
			/>,
		);

		await waitFor(() => {
			expect(NotificationMock.instances).toHaveLength(1);
		});

		const raw = localStorage.getItem("corvix.notifications.browser.seen");
		const saved = JSON.parse(raw ?? "[]") as [string, number][];
		// Adding the new id pushed the set to 501; it is pruned back to the bound.
		expect(saved).toHaveLength(500);
		const ids = new Set(saved.map((entry) => entry[0]));
		// The freshly-seen id is retained; the least-recently-seen one is evicted.
		expect(ids.has("primary:new")).toBe(true);
		expect(ids.has("old:499")).toBe(false);
	});

	it("syncs deduplication across tabs via BroadcastChannel", async () => {
		NotificationMock.setPermission("granted");
		localStorage.setItem("corvix.notifications.browser.enabled", "true");
		const config: BrowserTabNotificationsConfig = {
			enabled: true,
			max_per_cycle: 5,
			cooldown_seconds: 2,
		};
		const item = makeItem({ thread_id: "shared", subject_title: "Shared" });

		// "Tab B" mounts first with no items, so it is subscribed to the channel
		// before "Tab A" broadcasts.
		const tabB = render(<Harness items={[]} config={config} />);

		// "Tab A" mounts, notifies the shared item, and broadcasts the seen id.
		render(<Harness items={[item]} config={config} />);
		await waitFor(() => {
			expect(NotificationMock.instances).toHaveLength(1);
		});

		// Allow the broadcast to propagate to tab B.
		await new Promise((resolve) => setTimeout(resolve, 50));

		// Tab B now sees the same unread item; it must not fire a duplicate.
		tabB.rerender(<Harness items={[item]} config={config} />);
		await new Promise((resolve) => setTimeout(resolve, 50));
		expect(NotificationMock.instances).toHaveLength(1);
	});

	it("suppresses new bursts until cooldown expires", async () => {
		vi.useFakeTimers();
		NotificationMock.setPermission("granted");
		localStorage.setItem("corvix.notifications.browser.enabled", "true");

		const config: BrowserTabNotificationsConfig = {
			enabled: true,
			max_per_cycle: 5,
			cooldown_seconds: 1,
		};
		const { rerender } = render(
			<Harness
				items={[makeItem({ thread_id: "1", subject_title: "One" })]}
				config={config}
			/>,
		);

		await waitFor(() => {
			expect(NotificationMock.instances).toHaveLength(1);
		});

		rerender(
			<Harness
				items={[
					makeItem({ thread_id: "1", subject_title: "One" }),
					makeItem({ thread_id: "2", subject_title: "Two" }),
				]}
				config={config}
			/>,
		);
		expect(NotificationMock.instances).toHaveLength(1);

		await vi.advanceTimersByTimeAsync(1_100);
		rerender(
			<Harness
				items={[
					makeItem({ thread_id: "1", subject_title: "One" }),
					makeItem({ thread_id: "2", subject_title: "Two" }),
				]}
				config={{ ...config }}
			/>,
		);

		await waitFor(() => {
			expect(NotificationMock.instances).toHaveLength(2);
		});
		expect(NotificationMock.instances[1]?.title).toBe("Two");
	});
});
