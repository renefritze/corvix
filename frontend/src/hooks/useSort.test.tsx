import { render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { Router } from "preact-router";
import { beforeEach, describe, expect, it } from "vitest";
import { setPath } from "../test/http";
import type { SortColumn, SortDirection } from "../types";
import { useSort } from "./useSort";

interface SortProps {
	readonly col?: SortColumn;
	readonly dir?: SortDirection;
}

function Sort({ col = "score", dir = "desc" }: SortProps) {
	const { sortColumn, sortDirection, handleSort } = useSort(col, dir);
	return (
		<div>
			<div data-testid="state">{`${sortColumn}:${sortDirection}`}</div>
			<button type="button" onClick={() => handleSort("score")}>
				sort-score
			</button>
			<button type="button" onClick={() => handleSort("repository")}>
				sort-repo
			</button>
		</div>
	);
}

// A mounted Router is required for preact-router's route() to update history,
// which is now the single source of truth for sort state.
function Harness(props: SortProps) {
	return (
		<Router>
			<Sort default {...props} />
		</Router>
	);
}

describe("useSort", () => {
	beforeEach(() => {
		setPath("/");
	});

	it("seeds from defaults and toggles direction on repeat column", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		expect(screen.getByTestId("state")).toHaveTextContent("score:desc");

		await user.click(screen.getByRole("button", { name: "sort-score" }));
		expect(screen.getByTestId("state")).toHaveTextContent("score:asc");

		await user.click(screen.getByRole("button", { name: "sort-repo" }));
		expect(screen.getByTestId("state")).toHaveTextContent("repository:desc");
	});

	it("seeds from the configured order when no URL query is present", () => {
		render(<Harness col="updated_at" dir="asc" />);
		expect(screen.getByTestId("state")).toHaveTextContent("updated_at:asc");
	});

	it("seeds from the URL query, overriding the configured order", () => {
		setPath("/?sort=reason&dir=asc");
		render(<Harness col="score" dir="desc" />);
		expect(screen.getByTestId("state")).toHaveTextContent("reason:asc");
	});

	it("writes sort changes back to the URL query", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		await user.click(screen.getByRole("button", { name: "sort-repo" }));
		expect(globalThis.location.search).toBe("?sort=repository&dir=desc");
		expect(screen.getByTestId("state")).toHaveTextContent("repository:desc");
	});
});
