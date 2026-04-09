import { render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { makeItem } from "../test/fixtures";
import { FilterBar } from "./FilterBar";

describe("FilterBar", () => {
	it("renders deduped options and fires callbacks", async () => {
		const onFilterChange = vi.fn();
		const onClearFilters = vi.fn();
		const user = userEvent.setup();

		render(
			<FilterBar
				filters={{ unread: "all", reason: "", repository: "" }}
				items={[
					makeItem({ reason: "mention", repository: "org/a" }),
					makeItem({
						thread_id: "2",
						reason: "subscribed",
						repository: "org/b",
					}),
				]}
				onFilterChange={onFilterChange}
				onClearFilters={onClearFilters}
				generatedAt={"2026-04-09T10:00:00Z"}
			/>,
		);

		const reason = screen.getByLabelText("Reason filter");
		await user.selectOptions(reason, "subscribed");
		expect(onFilterChange).toHaveBeenCalledWith("reason", "subscribed");

		await user.click(screen.getByRole("button", { name: "Clear" }));
		expect(onClearFilters).toHaveBeenCalledTimes(1);
		expect(screen.getByText(/snapshot:/i)).toBeInTheDocument();
	});
});
