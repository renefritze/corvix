import { render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { useSort } from "./useSort";

function Harness({
	initialColumn,
	initialDir,
}: {
	initialColumn?: "score" | "repository";
	initialDir?: "asc" | "desc";
}) {
	const { sortColumn, sortDirection, handleSort } = useSort(
		initialColumn,
		initialDir,
	);

	return (
		<div>
			<div data-testid="state">{`${sortColumn}:${sortDirection}`}</div>
			<button type="button" onClick={() => handleSort("score")}>
				score
			</button>
			<button type="button" onClick={() => handleSort("repository")}>
				repo
			</button>
		</div>
	);
}

describe("useSort", () => {
	it("toggles direction when sorting current column", async () => {
		const user = userEvent.setup();
		render(<Harness initialColumn="score" initialDir="desc" />);
		expect(screen.getByTestId("state")).toHaveTextContent("score:desc");

		await user.click(screen.getByRole("button", { name: "score" }));
		expect(screen.getByTestId("state")).toHaveTextContent("score:asc");
	});

	it("switching column resets to desc", async () => {
		const user = userEvent.setup();
		render(<Harness initialColumn="score" initialDir="asc" />);

		await user.click(screen.getByRole("button", { name: "repo" }));
		expect(screen.getByTestId("state")).toHaveTextContent("repository:desc");
	});
});
