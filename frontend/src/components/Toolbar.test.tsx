import { render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "preact";
import { Toolbar } from "./Toolbar";

type ToolbarProps = ComponentProps<typeof Toolbar>;

function renderToolbar(overrides: Partial<ToolbarProps> = {}) {
	const props: ToolbarProps = {
		dashboardNames: ["overview"],
		currentDashboard: "overview",
		onDashboardChange: vi.fn(),
		onRefresh: vi.fn(),
		refreshing: false,
		summary: null,
		shortcutsOpen: false,
		onToggleShortcuts: vi.fn(),
		notifSupported: true,
		notifActive: false,
		notifPermission: "default",
		onEnableNotifications: vi.fn(),
		onDisableNotifications: vi.fn(),
		onResetLayout: vi.fn(),
		...overrides,
	};
	return render(<Toolbar {...props} />);
}

describe("Toolbar", () => {
	it("handles dashboard selection and refresh", async () => {
		const user = userEvent.setup();
		const onDashboardChange = vi.fn();
		const onRefresh = vi.fn();
		const onToggleShortcuts = vi.fn();

		renderToolbar({
			dashboardNames: ["overview", "triage"],
			summary: {
				unread_items: 1,
				read_items: 2,
				group_count: 1,
				repository_count: 2,
				reason_count: 2,
			},
			onDashboardChange,
			onRefresh,
			onToggleShortcuts,
		});

		await user.selectOptions(
			screen.getByLabelText("Select dashboard"),
			"triage",
		);
		expect(onDashboardChange).toHaveBeenCalledWith("triage");

		await user.click(screen.getByRole("button", { name: "Refresh" }));
		expect(onRefresh).toHaveBeenCalledTimes(1);

		await user.click(screen.getByRole("button", { name: /shortcuts/i }));
		expect(onToggleShortcuts).toHaveBeenCalledTimes(1);
	});

	it("renders denied notification state and hides selector for single dashboard", () => {
		renderToolbar({
			refreshing: true,
			shortcutsOpen: true,
			notifPermission: "denied",
		});

		expect(screen.getByText("Notifs blocked")).toBeInTheDocument();
		expect(screen.queryByLabelText("Select dashboard")).not.toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Refresh" })).toBeDisabled();
	});

	it("renders active notifications toggle and disables them", async () => {
		const user = userEvent.setup();
		const onDisableNotifications = vi.fn();

		renderToolbar({
			notifActive: true,
			notifPermission: "granted",
			onDisableNotifications,
		});

		await user.click(
			screen.getByRole("button", { name: "Disable browser notifications" }),
		);
		expect(onDisableNotifications).toHaveBeenCalledTimes(1);
	});

	it("invokes the reset-layout callback", async () => {
		const user = userEvent.setup();
		const onResetLayout = vi.fn();

		renderToolbar({ notifSupported: false, onResetLayout });

		await user.click(
			screen.getByRole("button", { name: "Reset column layout" }),
		);
		expect(onResetLayout).toHaveBeenCalledTimes(1);
	});

	it("handles null current dashboard value", () => {
		renderToolbar({
			dashboardNames: ["overview", "triage"],
			currentDashboard: null,
			notifSupported: false,
		});

		expect(screen.getByLabelText("Select dashboard")).toBeInTheDocument();
		expect(
			screen.getByRole("option", { name: "overview" }),
		).toBeInTheDocument();
	});
});
