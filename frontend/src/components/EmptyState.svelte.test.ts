import { render, screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { FilterState } from "../types";
import EmptyState from "./EmptyState.svelte";

type FilterContext = {
	unread: FilterState["unread"];
	reason: string[];
	repository: string;
};

function renderState(overrides: Record<string, unknown> = {}) {
	return render(EmptyState, {
		props: {
			hasFilters: false,
			totalItems: 0,
			onClearFilters: vi.fn(),
			onRetry: vi.fn(),
			...overrides,
		},
	});
}

describe("EmptyState", () => {
	it("renders the error state and the retry button fires onRetry", async () => {
		const onRetry = vi.fn();
		renderState({ error: "boom", onRetry });
		expect(screen.getByText("Failed to load")).toBeInTheDocument();
		expect(screen.getByText("boom")).toBeInTheDocument();
		expect(screen.getByTestId("empty-state")).toHaveClass("error");
		await userEvent.click(screen.getByRole("button", { name: "Retry" }));
		expect(onRetry).toHaveBeenCalledTimes(1);
	});

	it("renders the generic no-results filter state and clears filters", async () => {
		const onClearFilters = vi.fn();
		renderState({ hasFilters: true, totalItems: 3, onClearFilters });
		expect(screen.getByText("No results")).toBeInTheDocument();
		expect(
			screen.getByText("No notifications match the current filters."),
		).toBeInTheDocument();
		await userEvent.click(screen.getByRole("button", { name: "Clear filters" }));
		expect(onClearFilters).toHaveBeenCalledTimes(1);
	});

	it("renders the unread + repository scoped empty message", () => {
		const filterContext: FilterContext = {
			unread: "unread",
			reason: [],
			repository: "org/repo-a",
		};
		renderState({ hasFilters: true, totalItems: 0, filterContext });
		expect(
			screen.getByText("No unread notifications in org/repo-a"),
		).toBeInTheDocument();
		expect(
			screen.getByText("You're all caught up for this repository."),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "Clear filters" }),
		).toBeInTheDocument();
	});

	it("renders the repository-only scoped empty message", () => {
		const filterContext: FilterContext = {
			unread: "all",
			reason: ["mention"],
			repository: "org/repo-b",
		};
		renderState({ hasFilters: true, totalItems: 2, filterContext });
		expect(
			screen.getByText("No notifications in org/repo-b"),
		).toBeInTheDocument();
		expect(
			screen.getByText(
				"No notifications in this repository match your filters.",
			),
		).toBeInTheDocument();
	});

	it("renders the unread-only empty message without a repository filter", () => {
		const filterContext: FilterContext = {
			unread: "unread",
			reason: [],
			repository: "",
		};
		renderState({ hasFilters: true, totalItems: 2, filterContext });
		expect(screen.getByText("No unread notifications")).toBeInTheDocument();
		expect(
			screen.getByText("You're all caught up for the current filters."),
		).toBeInTheDocument();
	});

	it("renders the All clear state when there are no items and no filters", () => {
		renderState({ hasFilters: false, totalItems: 0 });
		expect(screen.getByText("All clear")).toBeInTheDocument();
		expect(
			screen.getByText("No notifications in this dashboard."),
		).toBeInTheDocument();
		expect(screen.queryByRole("button")).toBeNull();
	});

	it("renders the fallback no-results state with items but no filters", () => {
		renderState({ hasFilters: false, totalItems: 3 });
		expect(screen.getByText("No results")).toBeInTheDocument();
		expect(
			screen.getByText("No notifications match the current filters."),
		).toBeInTheDocument();
		expect(screen.queryByRole("button")).toBeNull();
	});
});
