import { render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { TableHeader } from "./TableHeader";

describe("TableHeader", () => {
	it("shows active sort and handles interactions", async () => {
		const onSort = vi.fn();
		const onResizeStart = vi.fn();
		const onResetColumnWidth = vi.fn();
		const user = userEvent.setup();

		const { container } = render(
			<table>
				<TableHeader
					sortColumn="score"
					sortDirection="asc"
					onSort={onSort}
					columnWidths={{
						repository: 190,
						subject_type: 110,
						reason: 150,
						score: 75,
						updated_at: 110,
					}}
					onResizeStart={onResizeStart}
					onResetColumnWidth={onResetColumnWidth}
				/>
			</table>,
		);

		const scoreHeader = screen
			.getByRole("button", { name: /score/i })
			.closest("th");
		expect(scoreHeader).toHaveAttribute("aria-sort", "ascending");

		await user.click(screen.getByRole("button", { name: /repository/i }));
		expect(onSort).toHaveBeenCalledWith("repository");

		const handle = container.querySelector(
			".col-repository .col-resize-handle",
		);
		expect(handle).not.toBeNull();
		handle?.dispatchEvent(
			new MouseEvent("mousedown", { bubbles: true, clientX: 240 }),
		);
		handle?.dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));

		expect(onResizeStart).toHaveBeenCalledWith("repository", 240);
		expect(onResetColumnWidth).toHaveBeenCalledWith("repository");
	});
});
