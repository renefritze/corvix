import { fireEvent, render, screen, waitFor } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { useColumnResize } from "./useColumnResize";

function Harness() {
	const { widths, startResize, resetColumnWidth } = useColumnResize();
	return (
		<div>
			<div data-testid="repo-width">{widths.repository}</div>
			<button type="button" onMouseDown={() => startResize("repository", 100)}>
				start
			</button>
			<button type="button" onClick={() => resetColumnWidth("repository")}>
				reset
			</button>
		</div>
	);
}

describe("useColumnResize", () => {
	it("resizes and resets column width", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		expect(screen.getByTestId("repo-width")).toHaveTextContent("185");
		await user.pointer([
			{
				target: screen.getByRole("button", { name: "start" }),
				keys: "[MouseLeft>]",
			},
		]);
		window.dispatchEvent(new MouseEvent("mousemove", { clientX: 150 }));
		await waitFor(() => {
			expect(screen.getByTestId("repo-width")).toHaveTextContent("235");
		});

		window.dispatchEvent(new MouseEvent("mouseup"));
		await user.click(screen.getByRole("button", { name: "reset" }));
		expect(screen.getByTestId("repo-width")).toHaveTextContent("185");
	});

	it("falls back from invalid storage and clamps at minimum width", async () => {
		localStorage.setItem("corvix.table.columnWidths", "{broken");
		render(<Harness />);
		expect(screen.getByTestId("repo-width")).toHaveTextContent("185");

		fireEvent.mouseDown(screen.getByRole("button", { name: "start" }));
		window.dispatchEvent(new MouseEvent("mousemove", { clientX: -10_000 }));
		await waitFor(() => {
			expect(screen.getByTestId("repo-width")).toHaveTextContent("120");
		});
	});

	it("clamps too-small stored widths from localStorage", () => {
		localStorage.setItem(
			"corvix.table.columnWidths",
			JSON.stringify({ repository: 10 }),
		);

		render(<Harness />);

		expect(screen.getByTestId("repo-width")).toHaveTextContent("120");
	});
});
