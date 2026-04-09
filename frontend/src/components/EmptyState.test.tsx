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
});
