import { render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { useFilters } from "./useFilters";

function Harness() {
	const { filters, setFilter, clearFilters } = useFilters();
	return (
		<div>
			<div data-testid="state">{JSON.stringify(filters)}</div>
			<button type="button" onClick={() => setFilter("reason", "subscribed")}>
				set-reason
			</button>
			<button type="button" onClick={() => setFilter("unread", "read")}>
				set-unread
			</button>
			<button type="button" onClick={clearFilters}>
				clear
			</button>
		</div>
	);
}

describe("useFilters", () => {
	it("updates and clears filters", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		expect(screen.getByTestId("state")).toHaveTextContent(
			'{"unread":"all","reason":"","repository":""}',
		);

		await user.click(screen.getByRole("button", { name: "set-reason" }));
		expect(screen.getByTestId("state")).toHaveTextContent(
			'"reason":"subscribed"',
		);

		await user.click(screen.getByRole("button", { name: "set-unread" }));
		expect(screen.getByTestId("state")).toHaveTextContent('"unread":"read"');

		await user.click(screen.getByRole("button", { name: "clear" }));
		expect(screen.getByTestId("state")).toHaveTextContent(
			'{"unread":"all","reason":"","repository":""}',
		);
	});
});
