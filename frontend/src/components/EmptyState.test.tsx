import { render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
	it("renders error state and retry", async () => {
		const user = userEvent.setup();
		const onRetry = vi.fn();
		render(
			<EmptyState
				hasFilters={false}
				totalItems={0}
				onClearFilters={vi.fn()}
				onRetry={onRetry}
				error="boom"
			/>,
		);

		expect(screen.getByText("Failed to load")).toBeInTheDocument();
		await user.click(screen.getByRole("button", { name: "Retry" }));
		expect(onRetry).toHaveBeenCalledTimes(1);
	});

	it("renders no-results state and clear button", async () => {
		const user = userEvent.setup();
		const onClearFilters = vi.fn();
		render(
			<EmptyState
				hasFilters={true}
				totalItems={3}
				onClearFilters={onClearFilters}
				onRetry={vi.fn()}
			/>,
		);
		expect(screen.getByText("No results")).toBeInTheDocument();
		await user.click(screen.getByRole("button", { name: "Clear filters" }));
		expect(onClearFilters).toHaveBeenCalledTimes(1);
	});

	it("renders explicit repository unread empty message", () => {
		render(
			<EmptyState
				hasFilters={true}
				totalItems={0}
				onClearFilters={vi.fn()}
				onRetry={vi.fn()}
				filterContext={{
					unread: "unread",
					reason: "",
					repository: "org/repo-a",
				}}
			/>,
		);

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

	it("renders repository-scoped empty message", () => {
		render(
			<EmptyState
				hasFilters={true}
				totalItems={2}
				onClearFilters={vi.fn()}
				onRetry={vi.fn()}
				filterContext={{
					unread: "all",
					reason: "mention",
					repository: "org/repo-b",
				}}
			/>,
		);

		expect(
			screen.getByText("No notifications in org/repo-b"),
		).toBeInTheDocument();
		expect(
			screen.getByText(
				"No notifications in this repository match your filters.",
			),
		).toBeInTheDocument();
	});

	it("renders unread-only empty message without repository filter", () => {
		render(
			<EmptyState
				hasFilters={true}
				totalItems={2}
				onClearFilters={vi.fn()}
				onRetry={vi.fn()}
				filterContext={{
					unread: "unread",
					reason: "",
					repository: "",
				}}
			/>,
		);

		expect(screen.getByText("No unread notifications")).toBeInTheDocument();
		expect(
			screen.getByText("You're all caught up for the current filters."),
		).toBeInTheDocument();
	});

	it("renders fallback no-results when there are items but filters are empty", () => {
		render(
			<EmptyState
				hasFilters={false}
				totalItems={3}
				onClearFilters={vi.fn()}
				onRetry={vi.fn()}
			/>,
		);

		expect(screen.getByText("No results")).toBeInTheDocument();
		expect(
			screen.getByText("No notifications match the current filters."),
		).toBeInTheDocument();
	});
});
