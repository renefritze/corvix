import { act, render, renderHook, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { Router } from "preact-router";
import { beforeEach, describe, expect, it } from "vitest";
import { setPath } from "../test/http";
import type { SortColumn, SortDirection } from "../types";
import { useSort } from "./useSort";

function Sort() {
	const { sortColumn, sortDirection, handleSort } = useSort();
	return (
		<div>
			<div data-testid="state">{`${sortColumn}:${sortDirection}`}</div>
			<button type="button" onClick={() => handleSort("repository")}>
				sort-repo
			</button>
		</div>
	);
}

// A mounted Router is required for preact-router's route() to update history.
function Harness() {
	return (
		<Router>
			<Sort default />
		</Router>
	);
}

describe("useSort", () => {
	beforeEach(() => {
		setPath("/");
	});

	it("seeds from defaults and toggles direction on repeat column", () => {
		const { result } = renderHook(() => useSort());

		expect(result.current.sortColumn).toBe("score");
		expect(result.current.sortDirection).toBe("desc");

		act(() => {
			result.current.handleSort("score");
		});
		expect(result.current.sortDirection).toBe("asc");

		act(() => {
			result.current.handleSort("repository");
		});
		expect(result.current.sortColumn).toBe("repository");
		expect(result.current.sortDirection).toBe("desc");
	});

	it("resets sort when the seeded column or direction changes", () => {
		const { result, rerender } = renderHook(
			({ col, dir }: { col: SortColumn; dir: SortDirection }) =>
				useSort(col, dir),
			{
				initialProps: {
					col: "score" as SortColumn,
					dir: "desc" as SortDirection,
				},
			},
		);

		act(() => {
			result.current.handleSort("reason");
		});
		expect(result.current.sortColumn).toBe("reason");

		rerender({ col: "updated_at", dir: "asc" });
		expect(result.current.sortColumn).toBe("updated_at");
		expect(result.current.sortDirection).toBe("asc");
	});

	it("seeds from the URL query, overriding the configured order", () => {
		setPath("/?sort=reason&dir=asc");
		const { result, rerender } = renderHook(
			({ col, dir }: { col: SortColumn; dir: SortDirection }) =>
				useSort(col, dir),
			{
				initialProps: {
					col: "score" as SortColumn,
					dir: "desc" as SortDirection,
				},
			},
		);

		expect(result.current.sortColumn).toBe("reason");
		expect(result.current.sortDirection).toBe("asc");

		// The dashboard's configured order no longer re-seeds once the URL drives.
		rerender({ col: "updated_at", dir: "desc" });
		expect(result.current.sortColumn).toBe("reason");
	});

	it("writes sort changes back to the URL query", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		await user.click(screen.getByRole("button", { name: "sort-repo" }));
		expect(globalThis.location.search).toBe("?sort=repository&dir=desc");
		expect(screen.getByTestId("state")).toHaveTextContent("repository:desc");
	});
});
