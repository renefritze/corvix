import { render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { Toolbar } from "./Toolbar";

describe("Toolbar", () => {
	it("handles dashboard selection and refresh", async () => {
		const user = userEvent.setup();
		const onDashboardChange = vi.fn();
		const onRefresh = vi.fn();
		const onToggleShortcuts = vi.fn();

		render(
			<Toolbar
				dashboardNames={["overview", "triage"]}
				currentDashboard="overview"
				onDashboardChange={onDashboardChange}
				onRefresh={onRefresh}
				refreshing={false}
				summary={{
					unread_items: 1,
					read_items: 2,
					group_count: 1,
					repository_count: 2,
					reason_count: 2,
				}}
				shortcutsOpen={false}
				onToggleShortcuts={onToggleShortcuts}
				notifSupported={true}
				notifActive={false}
				notifPermission="default"
				onEnableNotifications={vi.fn()}
				onDisableNotifications={vi.fn()}
			/>,
		);

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
		render(
			<Toolbar
				dashboardNames={["overview"]}
				currentDashboard="overview"
				onDashboardChange={vi.fn()}
				onRefresh={vi.fn()}
				refreshing={true}
				summary={null}
				shortcutsOpen={true}
				onToggleShortcuts={vi.fn()}
				notifSupported={true}
				notifActive={false}
				notifPermission="denied"
				onEnableNotifications={vi.fn()}
				onDisableNotifications={vi.fn()}
			/>,
		);

		expect(screen.getByText("Notifs blocked")).toBeInTheDocument();
		expect(screen.queryByLabelText("Select dashboard")).not.toBeInTheDocument();
		expect(screen.getByRole("button", { name: "Refresh" })).toBeDisabled();
	});

	it("renders active notifications toggle and disables them", async () => {
		const user = userEvent.setup();
		const onDisableNotifications = vi.fn();

		render(
			<Toolbar
				dashboardNames={["overview"]}
				currentDashboard="overview"
				onDashboardChange={vi.fn()}
				onRefresh={vi.fn()}
				refreshing={false}
				summary={null}
				shortcutsOpen={false}
				onToggleShortcuts={vi.fn()}
				notifSupported={true}
				notifActive={true}
				notifPermission="granted"
				onEnableNotifications={vi.fn()}
				onDisableNotifications={onDisableNotifications}
			/>,
		);

		await user.click(
			screen.getByRole("button", { name: "Disable browser notifications" }),
		);
		expect(onDisableNotifications).toHaveBeenCalledTimes(1);
	});

	it("handles null current dashboard value", () => {
		render(
			<Toolbar
				dashboardNames={["overview", "triage"]}
				currentDashboard={null}
				onDashboardChange={vi.fn()}
				onRefresh={vi.fn()}
				refreshing={false}
				summary={null}
				shortcutsOpen={false}
				onToggleShortcuts={vi.fn()}
				notifSupported={false}
				notifActive={false}
				notifPermission="default"
				onEnableNotifications={vi.fn()}
				onDisableNotifications={vi.fn()}
			/>,
		);

		expect(screen.getByLabelText("Select dashboard")).toBeInTheDocument();
		expect(
			screen.getByRole("option", { name: "overview" }),
		).toBeInTheDocument();
	});
});
