import { screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ThemeStore } from "../lib/theme.svelte";
import { renderWithStores } from "../test/renderWithStores";
import { root } from "../test/runes.svelte";
import type { DashboardSummary } from "../types";
import Toolbar from "./Toolbar.svelte";

let dispose: (() => void) | undefined;

afterEach(() => {
	dispose?.();
	dispose = undefined;
});

function makeTheme() {
	const { value, dispose: d } = root(() => new ThemeStore());
	dispose = d;
	return value;
}

function renderToolbar(overrides: Record<string, unknown> = {}) {
	const props = {
		dashboardNames: ["overview"],
		currentDashboard: "overview",
		onDashboardChange: vi.fn(),
		onRefresh: vi.fn(),
		refreshing: false,
		summary: null as DashboardSummary | null,
		shortcutsOpen: false,
		onToggleShortcuts: vi.fn(),
		notifSupported: true,
		notifActive: false,
		notifPermission: "default" as const,
		onEnableNotifications: vi.fn(),
		onDisableNotifications: vi.fn(),
		onResetLayout: vi.fn(),
		searchQuery: "",
		onSearchChange: vi.fn(),
		onOpenCommandPalette: vi.fn(),
		...overrides,
	};
	renderWithStores(Toolbar, props, { theme: makeTheme() });
	return props;
}

describe("Toolbar", () => {
	it("renders the app name and summary stats", () => {
		renderToolbar({
			summary: {
				unread_items: 1,
				read_items: 2,
				group_count: 1,
				repository_count: 3,
				reason_count: 2,
			},
		});
		expect(screen.getByText("Corvix")).toBeInTheDocument();
		expect(
			screen.getByText(/3 notifications · 1 unread · 3 repos/),
		).toBeInTheDocument();
	});

	it("shows the dashboard selector only for multiple dashboards and fires change", async () => {
		const props = renderToolbar({ dashboardNames: ["overview", "triage"] });
		await userEvent.selectOptions(
			screen.getByLabelText("Select dashboard"),
			"triage",
		);
		expect(props.onDashboardChange).toHaveBeenCalledWith("triage");
	});

	it("hides the dashboard selector for a single dashboard", () => {
		renderToolbar({ dashboardNames: ["overview"] });
		expect(screen.queryByLabelText("Select dashboard")).toBeNull();
	});

	it("falls back to an empty value when there is no current dashboard", () => {
		renderToolbar({
			dashboardNames: ["overview", "triage"],
			currentDashboard: null,
		});
		const select = screen.getByLabelText("Select dashboard") as HTMLSelectElement;
		expect(select.value).toBe("");
		expect(screen.getByRole("option", { name: "overview" })).toBeInTheDocument();
	});

	it("calls onRefresh when the refresh button is clicked", async () => {
		const props = renderToolbar();
		await userEvent.click(screen.getByRole("button", { name: "Refresh" }));
		expect(props.onRefresh).toHaveBeenCalledTimes(1);
	});

	it("disables the refresh button while refreshing", () => {
		renderToolbar({ refreshing: true });
		const button = screen.getByRole("button", { name: "Refresh" });
		expect(button).toBeDisabled();
		expect(button).toHaveTextContent("Refreshing");
	});

	it("fires shortcuts, reset-layout, and command-palette callbacks", async () => {
		const props = renderToolbar();
		await userEvent.click(screen.getByRole("button", { name: "Keyboard shortcuts" }));
		expect(props.onToggleShortcuts).toHaveBeenCalledTimes(1);
		await userEvent.click(screen.getByRole("button", { name: "Reset column layout" }));
		expect(props.onResetLayout).toHaveBeenCalledTimes(1);
		await userEvent.click(screen.getByRole("button", { name: "Open command palette" }));
		expect(props.onOpenCommandPalette).toHaveBeenCalledTimes(1);
	});

	it("shows a blocked indicator when notifications are denied", () => {
		renderToolbar({ notifPermission: "denied" });
		expect(screen.getByText("Blocked")).toBeInTheDocument();
	});

	it("enables notifications from the default state", async () => {
		const props = renderToolbar({ notifActive: false, notifPermission: "default" });
		await userEvent.click(
			screen.getByRole("button", { name: "Enable browser notifications" }),
		);
		expect(props.onEnableNotifications).toHaveBeenCalledTimes(1);
	});

	it("enables notifications when granted but inactive", async () => {
		const props = renderToolbar({ notifActive: false, notifPermission: "granted" });
		await userEvent.click(
			screen.getByRole("button", { name: "Enable browser notifications" }),
		);
		expect(props.onEnableNotifications).toHaveBeenCalledTimes(1);
	});

	it("disables notifications when they are active", async () => {
		const props = renderToolbar({ notifActive: true, notifPermission: "granted" });
		await userEvent.click(
			screen.getByRole("button", { name: "Disable browser notifications" }),
		);
		expect(props.onDisableNotifications).toHaveBeenCalledTimes(1);
	});

	it("omits the notification control when unsupported", () => {
		renderToolbar({ notifSupported: false });
		expect(screen.queryByText("Blocked")).toBeNull();
		expect(
			screen.queryByRole("button", { name: "Enable browser notifications" }),
		).toBeNull();
	});

	it("forwards search input to onSearchChange", async () => {
		const props = renderToolbar();
		await userEvent.type(screen.getByLabelText("Search notifications"), "z");
		expect(props.onSearchChange).toHaveBeenCalledWith("z");
	});
});
