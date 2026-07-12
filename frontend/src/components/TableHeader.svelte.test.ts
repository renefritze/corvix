import { render, screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ColumnWidths } from "../types";
import TableHeader from "./TableHeader.svelte";

const widths: ColumnWidths = {
	repository: 190,
	subject_type: 110,
	reason: 150,
	score: 75,
	updated_at: 110,
};

function renderHeader(overrides: Record<string, unknown> = {}) {
	return render(TableHeader, {
		props: {
			sortColumn: "score",
			sortDirection: "asc",
			onSort: vi.fn(),
			columnWidths: widths,
			onResizeStart: vi.fn(),
			onResetColumnWidth: vi.fn(),
			...overrides,
		},
	});
}

describe("TableHeader", () => {
	it("reflects the active sort column and direction via aria-sort", () => {
		renderHeader({ sortColumn: "score", sortDirection: "asc" });
		const scoreHeader = screen
			.getByRole("button", { name: /^Score\b/i })
			.closest("th");
		expect(scoreHeader).toHaveAttribute("aria-sort", "ascending");
		const repoHeader = screen
			.getByRole("button", { name: /^Repository$/i })
			.closest("th");
		expect(repoHeader).toHaveAttribute("aria-sort", "none");
	});

	it("shows a descending aria-sort when sortDirection is desc", () => {
		renderHeader({ sortColumn: "repository", sortDirection: "desc" });
		const repoHeader = screen
			.getByRole("button", { name: /^Repository$/i })
			.closest("th");
		expect(repoHeader).toHaveAttribute("aria-sort", "descending");
	});

	it("fires onSort with the column key when a header button is clicked", async () => {
		const onSort = vi.fn();
		renderHeader({ onSort });
		await userEvent.click(
			screen.getByRole("button", { name: /^Repository$/i }),
		);
		expect(onSort).toHaveBeenCalledWith("repository");
	});

	it("marks the non-resizable title column active with a descending arrow", () => {
		renderHeader({ sortColumn: "subject_title", sortDirection: "desc" });
		const titleHeader = screen
			.getByRole("button", { name: /^Title/i })
			.closest("th");
		expect(titleHeader).toHaveAttribute("aria-sort", "descending");
		// The title column is not resizable, so no resize handle is rendered for it.
		expect(
			screen.queryByRole("button", { name: "Resize Title column" }),
		).toBeNull();
	});

	it("renders a resize handle for every resizable column", () => {
		renderHeader();
		for (const label of ["Repository", "Type", "Reason", "Score", "Updated"]) {
			expect(
				screen.getByRole("button", { name: `Resize ${label} column` }),
			).toBeInTheDocument();
		}
	});

	it("applies the configured column width to resizable columns", () => {
		renderHeader();
		const repoHeader = screen
			.getByRole("button", { name: /^Repository$/i })
			.closest("th");
		expect(repoHeader).toHaveStyle({ width: "190px" });
	});

	it("fires onResizeStart on resize-handle mousedown and onResetColumnWidth on dblclick", () => {
		const onResizeStart = vi.fn();
		const onResetColumnWidth = vi.fn();
		renderHeader({ onResizeStart, onResetColumnWidth });
		const handle = screen.getByRole("button", {
			name: "Resize Repository column",
		});
		handle.dispatchEvent(
			new MouseEvent("mousedown", { bubbles: true, clientX: 240 }),
		);
		handle.dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));
		expect(onResizeStart).toHaveBeenCalledWith("repository", 240);
		expect(onResetColumnWidth).toHaveBeenCalledWith("repository");
	});
});
