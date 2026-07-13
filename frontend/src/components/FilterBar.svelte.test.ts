import { render, screen, within } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeItem } from "../test/fixtures";
import type { FilterState } from "../types";
import FilterBar from "./FilterBar.svelte";

function renderBar(overrides: Record<string, unknown> = {}) {
	const props = {
		filters: { unread: "all", reason: [], repository: "" } as FilterState,
		includeRead: true,
		items: [
			makeItem({ reason: "mention", repository: "org/a" }),
			makeItem({ thread_id: "2", reason: "subscribed", repository: "org/b" }),
		],
		onFilterChange: vi.fn(),
		onClearFilters: vi.fn(),
		generatedAt: "2026-04-09T10:00:00Z",
		...overrides,
	};
	render(FilterBar, { props });
	return props;
}

describe("FilterBar", () => {
	it("renders deduped reason options and fires reason/clear callbacks", async () => {
		const props = renderBar();
		await userEvent.click(screen.getByLabelText("Reason filter"));
		const menu = screen.getByRole("list", { name: "Reason options" });
		expect(within(menu).getByRole("button", { name: "mention" })).toBeInTheDocument();
		await userEvent.click(within(menu).getByRole("button", { name: "subscribed" }));
		expect(props.onFilterChange).toHaveBeenCalledWith("reason", ["subscribed"]);

		await userEvent.click(screen.getByRole("button", { name: "Clear" }));
		expect(props.onClearFilters).toHaveBeenCalledTimes(1);
		expect(screen.getByText(/snapshot:/i)).toBeInTheDocument();
	});

	it("appends to the selection when another reason is picked", async () => {
		const props = renderBar({
			filters: { unread: "all", reason: ["mention"], repository: "" },
			items: [
				makeItem({ reason: "mention", repository: "org/a" }),
				makeItem({ thread_id: "2", reason: "subscribed", repository: "org/b" }),
			],
			generatedAt: null,
		});
		await userEvent.click(screen.getByLabelText("Reason filter"));
		const menu = screen.getByRole("list", { name: "Reason options" });
		await userEvent.click(within(menu).getByRole("button", { name: "subscribed" }));
		expect(props.onFilterChange).toHaveBeenLastCalledWith("reason", [
			"mention",
			"subscribed",
		]);
	});

	it("toggles off an already-selected reason from the menu", async () => {
		const props = renderBar({
			filters: { unread: "all", reason: ["subscribed"], repository: "" },
			generatedAt: null,
		});
		await userEvent.click(screen.getByLabelText("Reason filter"));
		const menu = screen.getByRole("list", { name: "Reason options" });
		await userEvent.click(within(menu).getByRole("button", { name: "subscribed" }));
		expect(props.onFilterChange).toHaveBeenLastCalledWith("reason", []);
	});

	it("renders chips and removes a selected reason via its chip button", async () => {
		const props = renderBar({
			filters: { unread: "all", reason: ["mention"], repository: "" },
			items: [makeItem({ reason: "mention" })],
			generatedAt: null,
		});
		await userEvent.click(
			screen.getByRole("button", { name: "Remove mention reason filter" }),
		);
		expect(props.onFilterChange).toHaveBeenCalledWith("reason", []);
	});

	it("summarises the trigger label for many selected reasons", () => {
		renderBar({
			filters: {
				unread: "all",
				reason: ["a", "b", "c"],
				repository: "",
			},
		});
		expect(screen.getByText("3 reasons")).toBeInTheDocument();
	});

	it("disables read-state options when the dashboard excludes read items", () => {
		renderBar({
			filters: { unread: "unread", reason: [], repository: "" },
			includeRead: false,
			items: [makeItem()],
		});
		const unreadFilter = screen.getByLabelText("Unread state filter");
		expect(within(unreadFilter).getByRole("option", { name: /All/ })).toBeDisabled();
		expect(
			within(unreadFilter).getByRole("option", { name: /Read only/ }),
		).toBeDisabled();
		expect(
			within(unreadFilter).getByRole("option", { name: "Unread only" }),
		).not.toBeDisabled();
	});

	it("changes the unread filter via the select", async () => {
		const props = renderBar();
		await userEvent.selectOptions(
			screen.getByLabelText("Unread state filter"),
			"unread",
		);
		expect(props.onFilterChange).toHaveBeenCalledWith("unread", "unread");
	});

	it("lists repositories and changes the repository filter", async () => {
		const props = renderBar();
		const repoFilter = screen.getByLabelText("Repository filter");
		expect(within(repoFilter).getByRole("option", { name: "org/a" })).toBeInTheDocument();
		expect(within(repoFilter).getByRole("option", { name: "org/b" })).toBeInTheDocument();
		await userEvent.selectOptions(repoFilter, "org/b");
		expect(props.onFilterChange).toHaveBeenCalledWith("repository", "org/b");
	});

	it("keeps the selected repository visible when it no longer has matching items", () => {
		renderBar({
			filters: { unread: "unread", reason: [], repository: "org/a" },
			includeRead: false,
			items: [],
			generatedAt: null,
		});
		const repoFilter = screen.getByLabelText("Repository filter");
		expect(repoFilter).toHaveValue("org/a");
		expect(
			within(repoFilter).getByRole("option", {
				name: "org/a (no unread notifications)",
			}),
		).toBeInTheDocument();
	});

	it("keeps selected reasons visible when absent from the current items", async () => {
		renderBar({
			filters: { unread: "unread", reason: ["mention", "author"], repository: "" },
			includeRead: false,
			items: [makeItem({ reason: "review_requested" })],
			generatedAt: null,
		});
		await userEvent.click(screen.getByLabelText("Reason filter"));
		const menu = screen.getByRole("list", { name: "Reason options" });
		expect(
			within(menu).getByRole("button", { name: "mention (no unread notifications)" }),
		).toBeInTheDocument();
		expect(
			within(menu).getByRole("button", { name: "author (no unread notifications)" }),
		).toBeInTheDocument();
	});

	it("uses the read-inclusive missing label when read items are allowed", () => {
		renderBar({
			filters: { unread: "all", reason: [], repository: "org/gone" },
			includeRead: true,
			items: [makeItem({ repository: "org/a" })],
			generatedAt: null,
		});
		const repoFilter = screen.getByLabelText("Repository filter");
		expect(
			within(repoFilter).getByRole("option", {
				name: "org/gone (no matching notifications)",
			}),
		).toBeInTheDocument();
	});

	it("closes the reason menu on Escape", async () => {
		renderBar();
		await userEvent.click(screen.getByLabelText("Reason filter"));
		expect(screen.getByRole("list", { name: "Reason options" })).toBeInTheDocument();
		await userEvent.keyboard("{Escape}");
		expect(screen.queryByRole("list", { name: "Reason options" })).toBeNull();
	});

	it("closes the reason menu when clicking away", async () => {
		renderBar();
		await userEvent.click(screen.getByLabelText("Reason filter"));
		expect(screen.getByRole("list", { name: "Reason options" })).toBeInTheDocument();
		await userEvent.click(document.body);
		expect(screen.queryByRole("list", { name: "Reason options" })).toBeNull();
	});
});
