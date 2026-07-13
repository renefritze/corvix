import { render, screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeItem } from "../test/fixtures";
import type { ColumnWidths } from "../types";
import NotificationTable from "./NotificationTable.svelte";

const widths: ColumnWidths = {
	repository: 185,
	subject_type: 110,
	reason: 150,
	score: 75,
	updated_at: 110,
};

function renderTable(overrides: Record<string, unknown> = {}) {
	return render(NotificationTable, {
		props: {
			groups: [],
			sortColumn: "score",
			sortDirection: "desc",
			onSort: vi.fn(),
			onDismiss: vi.fn(),
			onDismissGroupRead: vi.fn(),
			onMarkGroupRead: vi.fn(),
			markingGroupNames: new Set<string>(),
			onOpenTarget: vi.fn(),
			onRequestIgnoreRule: vi.fn(),
			pendingDismissals: new Set<string>(),
			columnWidths: widths,
			onResizeStart: vi.fn(),
			onResetColumnWidth: vi.fn(),
			isCollapsed: () => false,
			onToggleCollapse: vi.fn(),
			...overrides,
		},
	});
}

describe("NotificationTable", () => {
	it("renders the labelled table with a group header and its rows", () => {
		const groups = [
			{
				name: "org/repo-a",
				items: [
					makeItem({ thread_id: "1", subject_title: "One" }),
					makeItem({ thread_id: "2", subject_title: "Two" }),
				],
			},
		];
		renderTable({ groups });
		expect(
			screen.getByRole("table", { name: "Notifications" }),
		).toBeInTheDocument();
		expect(screen.getByTestId("group-header-row")).toBeInTheDocument();
		expect(screen.getAllByRole("link")).toHaveLength(2);
	});

	it("sorts rows by score descending", () => {
		const groups = [
			{
				name: "org/repo-a",
				items: [
					makeItem({ thread_id: "1", score: 5, subject_title: "Low" }),
					makeItem({ thread_id: "2", score: 80, subject_title: "High" }),
				],
			},
		];
		renderTable({ groups, sortColumn: "score", sortDirection: "desc" });
		const links = screen.getAllByRole("link");
		expect(links[0]).toHaveTextContent("High");
		expect(links[1]).toHaveTextContent("Low");
	});

	it("sorts string columns case-insensitively and reverses on desc", () => {
		const groups = [
			{
				name: "org/repo-a",
				items: [
					makeItem({ thread_id: "1", subject_title: "zulu" }),
					makeItem({ thread_id: "2", subject_title: "Alpha" }),
				],
			},
		];
		const { unmount } = renderTable({
			groups,
			sortColumn: "subject_title",
			sortDirection: "asc",
		});
		let links = screen.getAllByRole("link");
		expect(links[0]).toHaveTextContent("Alpha");
		expect(links[1]).toHaveTextContent("zulu");
		unmount();

		renderTable({
			groups,
			sortColumn: "subject_title",
			sortDirection: "desc",
		});
		links = screen.getAllByRole("link");
		expect(links[0]).toHaveTextContent("zulu");
		expect(links[1]).toHaveTextContent("Alpha");
	});

	it("orders string sorts across greater-than and equal comparisons", () => {
		const groups = [
			{
				name: "org/repo-a",
				items: [
					makeItem({ thread_id: "1", subject_title: "Bravo" }),
					makeItem({ thread_id: "2", subject_title: "alpha" }),
					makeItem({ thread_id: "3", subject_title: "Bravo" }),
				],
			},
		];
		renderTable({ groups, sortColumn: "subject_title", sortDirection: "asc" });
		const links = screen.getAllByRole("link");
		expect(links[0]).toHaveTextContent("alpha");
		expect(links[1]).toHaveTextContent("Bravo");
		expect(links[2]).toHaveTextContent("Bravo");
	});

	it("hides the rows of a collapsed group but keeps its header", () => {
		const groups = [
			{
				name: "org/repo-a",
				items: [makeItem({ thread_id: "1", subject_title: "Hidden" })],
			},
		];
		renderTable({ groups, isCollapsed: () => true });
		expect(screen.getByTestId("group-header-row")).toBeInTheDocument();
		expect(screen.queryByRole("link")).toBeNull();
	});

	it("passes pendingDismissals through so a pending row is marked", () => {
		const item = makeItem({ thread_id: "1", subject_title: "One" });
		const groups = [{ name: "org/repo-a", items: [item] }];
		renderTable({
			groups,
			pendingDismissals: new Set([`${item.account_id}:${item.thread_id}`]),
		});
		const row = document.querySelector("tr[data-thread-id]");
		expect(row).not.toBeNull();
		expect(row?.className).toContain("dismissing");
	});

	it("invokes onMarkGroupRead with the group name and items", async () => {
		const onMarkGroupRead = vi.fn();
		const groups = [
			{
				name: "org/repo-a",
				items: [makeItem({ thread_id: "1", unread: true })],
			},
		];
		renderTable({ groups, onMarkGroupRead });
		await userEvent.click(
			screen.getByRole("button", {
				name: /Mark all visible unread notifications in org\/repo-a as read/,
			}),
		);
		expect(onMarkGroupRead).toHaveBeenCalledWith("org/repo-a", groups[0].items);
	});

	it("sorts numeric columns ascending and keeps equal values stable", () => {
		const groups = [
			{
				name: "org/repo-a",
				items: [
					makeItem({ thread_id: "1", score: 50, subject_title: "Mid" }),
					makeItem({ thread_id: "2", score: 10, subject_title: "Low" }),
					makeItem({ thread_id: "3", score: 50, subject_title: "AlsoMid" }),
				],
			},
		];
		renderTable({ groups, sortColumn: "score", sortDirection: "asc" });
		const links = screen.getAllByRole("link");
		expect(links[0]).toHaveTextContent("Low");
		expect(links[1]).toHaveTextContent("Mid");
		expect(links[2]).toHaveTextContent("AlsoMid");
	});

	it("invokes onDismissGroupRead from the group remove-read action", async () => {
		const onDismissGroupRead = vi.fn();
		const groups = [
			{
				name: "org/repo-a",
				items: [
					makeItem({ thread_id: "1", unread: true }),
					makeItem({ thread_id: "2", unread: false }),
				],
			},
		];
		renderTable({ groups, onDismissGroupRead });
		const button = screen.getByRole("button", {
			name: /Dismiss all visible read notifications in org\/repo-a/,
		});
		expect(button).toHaveTextContent("Remove read (1)");
		await userEvent.click(button);
		expect(onDismissGroupRead).toHaveBeenCalledWith(
			"org/repo-a",
			groups[0].items,
		);
	});

	it("disables the remove-read action while a read thread is pending dismissal", async () => {
		const readItem = makeItem({ thread_id: "2", unread: false });
		const groups = [
			{
				name: "org/repo-a",
				items: [makeItem({ thread_id: "1", unread: true }), readItem],
			},
		];
		const onDismissGroupRead = vi.fn();
		renderTable({
			groups,
			onDismissGroupRead,
			pendingDismissals: new Set([
				`${readItem.account_id}:${readItem.thread_id}`,
			]),
		});
		const button = screen.getByRole("button", {
			name: /Dismiss all visible read notifications in org\/repo-a/,
		});
		expect(button).toBeDisabled();
		await userEvent.click(button);
		expect(onDismissGroupRead).not.toHaveBeenCalled();
	});

	it("invokes onToggleCollapse with the group name from the header", async () => {
		const onToggleCollapse = vi.fn();
		const groups = [
			{ name: "org/repo-a", items: [makeItem({ thread_id: "1" })] },
		];
		renderTable({ groups, onToggleCollapse });
		await userEvent.click(
			screen.getByRole("button", { name: "Collapse org/repo-a" }),
		);
		expect(onToggleCollapse).toHaveBeenCalledWith("org/repo-a");
	});
});
