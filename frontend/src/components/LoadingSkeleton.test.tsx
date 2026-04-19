import { render, screen } from "@testing-library/preact";
import { LoadingSkeleton } from "./LoadingSkeleton";

describe("LoadingSkeleton", () => {
	it("renders a table placeholder with fixed row count", () => {
		render(<LoadingSkeleton />);
		expect(
			screen.getByRole("table", { name: "Loading notifications" }),
		).toBeInTheDocument();
		expect(document.querySelectorAll("tr.skeleton-row")).toHaveLength(9);
	});
});
