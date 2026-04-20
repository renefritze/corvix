import { render, screen, waitFor } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { makeItem } from "../test/fixtures";
import type { BrowserTabNotificationsConfig, DashboardItem } from "../types";
import { useBrowserNotifications } from "./useBrowserNotifications";

class NotificationMock {
	static permission: NotificationPermission = "default";
	static readonly requestPermission = vi.fn(async () => "granted");
	static readonly instances: NotificationMock[] = [];

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
		NotificationMock.permission = "default";
		NotificationMock.requestPermission.mockImplementation(async () => {
			NotificationMock.permission = "granted";
			return "granted";
		});
		Object.defineProperty(globalThis, "Notification", {
			value: NotificationMock,
			writable: true,
		});
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
		expect(globalThis.open).toHaveBeenCalledWith(
			"https://example.com/pr/1",
			"_blank",
			"noopener,noreferrer",
		);
	});
});
