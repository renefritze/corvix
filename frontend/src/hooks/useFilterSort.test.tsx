import { render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { makeSnapshot } from "../test/fixtures";
import type { SnapshotPayload } from "../types";
import { useFilterSort } from "./useFilterSort";

function Harness({ snapshot }: { readonly snapshot: SnapshotPayload | null }) {
	const {
		filters,
		setFilter,
		clearFilters,
		sortColumn,
		sortDirection,
		handleSort,
		dashboardAllowsRead,
		effectiveUnreadFilter,
	} = useFilterSort(snapshot);
	return (
		<div>
			<div data-testid="sort">{`${sortColumn}:${sortDirection}`}</div>
			<div data-testid="allows-read">{String(dashboardAllowsRead)}</div>
			<div data-testid="effective-unread">{effectiveUnreadFilter}</div>
			<div data-testid="filters">{JSON.stringify(filters)}</div>
			<button type="button" onClick={() => handleSort("repository")}>
				sort-repo
			</button>
			<button type="button" onClick={() => setFilter("unread", "read")}>
				set-read
			</button>
			<button type="button" onClick={clearFilters}>
				clear
			</button>
		</div>
	);
}

describe("useFilterSort", () => {
	it("seeds sort from the snapshot configuration", () => {
		render(
			<Harness
				snapshot={makeSnapshot({ sort_by: "updated_at", descending: false })}
			/>,
		);
		expect(screen.getByTestId("sort")).toHaveTextContent("updated_at:asc");
	});

	it("maps each configured sort key to its column", () => {
		const cases: Array<[string, string]> = [
			["title", "subject_title"],
			["repository", "repository"],
			["subject_type", "subject_type"],
			["reason", "reason"],
			["updated_at", "updated_at"],
			["unknown", "score"],
		];
		for (const [sortBy, expected] of cases) {
			const { unmount } = render(
				<Harness snapshot={makeSnapshot({ sort_by: sortBy })} />,
			);
			expect(screen.getByTestId("sort")).toHaveTextContent(`${expected}:desc`);
			unmount();
		}
	});

	it("toggles sort direction when the same column is selected again", async () => {
		const user = userEvent.setup();
		render(<Harness snapshot={makeSnapshot({ sort_by: "repository" })} />);
		expect(screen.getByTestId("sort")).toHaveTextContent("repository:desc");
		await user.click(screen.getByRole("button", { name: "sort-repo" }));
		expect(screen.getByTestId("sort")).toHaveTextContent("repository:asc");
	});

	it("locks the unread filter to unread when the dashboard excludes read", async () => {
		const user = userEvent.setup();
		render(<Harness snapshot={makeSnapshot({ include_read: false })} />);
		expect(screen.getByTestId("allows-read")).toHaveTextContent("false");
		expect(screen.getByTestId("effective-unread")).toHaveTextContent("unread");

		await user.click(screen.getByRole("button", { name: "set-read" }));
		// Underlying filter state changes, but the effective value stays locked.
		expect(screen.getByTestId("filters")).toHaveTextContent('"unread":"read"');
		expect(screen.getByTestId("effective-unread")).toHaveTextContent("unread");
	});

	it("respects the unread filter when the dashboard allows read", async () => {
		const user = userEvent.setup();
		render(<Harness snapshot={makeSnapshot({ include_read: true })} />);
		await user.click(screen.getByRole("button", { name: "set-read" }));
		expect(screen.getByTestId("effective-unread")).toHaveTextContent("read");
		await user.click(screen.getByRole("button", { name: "clear" }));
		expect(screen.getByTestId("effective-unread")).toHaveTextContent("all");
	});

	it("defaults sort and read access when no snapshot is present", () => {
		render(<Harness snapshot={null} />);
		expect(screen.getByTestId("sort")).toHaveTextContent("score:desc");
		expect(screen.getByTestId("allows-read")).toHaveTextContent("true");
	});

	it("re-seeds sort when the snapshot configuration changes", () => {
		const { rerender } = render(
			<Harness snapshot={makeSnapshot({ sort_by: "score" })} />,
		);
		expect(screen.getByTestId("sort")).toHaveTextContent("score:desc");
		rerender(
			<Harness
				snapshot={makeSnapshot({ sort_by: "reason", descending: false })}
			/>,
		);
		expect(screen.getByTestId("sort")).toHaveTextContent("reason:asc");
	});
});
