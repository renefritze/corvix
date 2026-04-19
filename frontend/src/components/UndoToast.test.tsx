import { render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { UndoToast } from "./UndoToast";

describe("UndoToast", () => {
	it("hides when count is zero and shows when active", async () => {
		const user = userEvent.setup();
		const onUndoAll = vi.fn();
		const { rerender } = render(<UndoToast count={0} onUndoAll={onUndoAll} />);

		expect(screen.queryByRole("status")).not.toBeInTheDocument();

		rerender(<UndoToast count={2} onUndoAll={onUndoAll} />);
		expect(screen.getByRole("status")).toHaveTextContent(
			"2 notifications dismissing",
		);

		await user.click(screen.getByRole("button", { name: "Undo" }));
		expect(onUndoAll).toHaveBeenCalledTimes(1);
	});
});
