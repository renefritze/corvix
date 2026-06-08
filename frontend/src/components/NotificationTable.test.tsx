import { render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { makeItem } from "../test/fixtures";
import type { ColumnWidths } from "../types";
import { NotificationTable } from "./NotificationTable";

const widths: ColumnWidths = {
	repository: 185,
	subject_type: 110,
	reason: 150,
	score: 75,
	updated_at: 110,
};

const resizeProps = {
	columnWidths: widths,
	onResizeStart: vi.fn(),
	onResetColumnWidth: vi.fn(),
};

describe("NotificationTable", () => {
	it("renders groups and sorts rows", () => {
		const groups = [
			{
				name: "org/repo-a",
				items: [
					makeItem({ thread_id: "1", score: 5, subject_title: "Low" }),
					makeItem({ thread_id: "2", score: 80, subject_title: "High" }),
				],
			},
		];

		render(
			<NotificationTable
				groups={groups}
				sortColumn="score"
				sortDirection="desc"
				onSort={vi.fn()}
				onDismiss={vi.fn()}
				onDismissGroupRead={vi.fn()}
				onMarkGroupRead={vi.fn()}
				markingGroupNames={new Set()}
				onOpenTarget={vi.fn()}
				onRequestIgnoreRule={vi.fn()}
				pendingDismissals={new Set(["1"])}
				{...resizeProps}
			/>,
		);

		expect(screen.getAllByText("org/repo-a").length).toBeGreaterThan(0);
		const links = screen.getAllByRole("link");
		expect(links[0]).toHaveTextContent("High");
		expect(links[1]).toHaveTextContent("Low");
		expect(screen.getByRole("table", { name: "Notifications" })).toBeVisible();
	});

	it("sorts string columns case-insensitively", () => {
		const groups = [
			{
				name: "org/repo-a",
				items: [
					makeItem({ thread_id: "1", subject_title: "zulu" }),
					makeItem({ thread_id: "2", subject_title: "Alpha" }),
				],
			},
		];

		render(
			<NotificationTable
				groups={groups}
				sortColumn="subject_title"
				sortDirection="asc"
				onSort={vi.fn()}
				onDismiss={vi.fn()}
				onDismissGroupRead={vi.fn()}
				onMarkGroupRead={vi.fn()}
				markingGroupNames={new Set()}
				onOpenTarget={vi.fn()}
				onRequestIgnoreRule={vi.fn()}
				pendingDismissals={new Set()}
				{...resizeProps}
			/>,
		);

		const links = screen.getAllByRole("link");
		expect(links[0]).toHaveTextContent("Alpha");
		expect(links[1]).toHaveTextContent("zulu");
	});

	it("renders group mark-all-read action and invokes callback", async () => {
		const groups = [
			{
				name: "org/repo-a",
				items: [
					makeItem({ thread_id: "1", unread: true, subject_title: "One" }),
					makeItem({ thread_id: "2", unread: false, subject_title: "Two" }),
				],
			},
		];
		const onMarkGroupRead = vi.fn();

		render(
			<NotificationTable
				groups={groups}
				sortColumn="score"
				sortDirection="desc"
				onSort={vi.fn()}
				onDismiss={vi.fn()}
				onDismissGroupRead={vi.fn()}
				onMarkGroupRead={onMarkGroupRead}
				markingGroupNames={new Set()}
				onOpenTarget={vi.fn()}
				onRequestIgnoreRule={vi.fn()}
				pendingDismissals={new Set()}
				{...resizeProps}
			/>,
		);

		const user = userEvent.setup();
		await user.click(
			screen.getByRole("button", {
				name: /Mark all visible unread notifications in org\/repo-a as read/,
			}),
		);

		expect(onMarkGroupRead).toHaveBeenCalledTimes(1);
		expect(onMarkGroupRead).toHaveBeenCalledWith("org/repo-a", groups[0].items);
	});

	it("renders group remove-read action and invokes callback", async () => {
		const groups = [
			{
				name: "org/repo-a",
				items: [
					makeItem({ thread_id: "1", unread: true, subject_title: "One" }),
					makeItem({ thread_id: "2", unread: false, subject_title: "Two" }),
				],
			},
		];
		const onDismissGroupRead = vi.fn();

		render(
			<NotificationTable
				groups={groups}
				sortColumn="score"
				sortDirection="desc"
				onSort={vi.fn()}
				onDismiss={vi.fn()}
				onDismissGroupRead={onDismissGroupRead}
				onMarkGroupRead={vi.fn()}
				markingGroupNames={new Set()}
				onOpenTarget={vi.fn()}
				onRequestIgnoreRule={vi.fn()}
				pendingDismissals={new Set()}
				{...resizeProps}
			/>,
		);

		const user = userEvent.setup();
		const removeReadButton = screen.getByRole("button", {
			name: /Dismiss all visible read notifications in org\/repo-a/,
		});
		expect(removeReadButton).toHaveTextContent("Remove read (1)");

		await user.click(removeReadButton);

		expect(onDismissGroupRead).toHaveBeenCalledTimes(1);
		expect(onDismissGroupRead).toHaveBeenCalledWith(
			"org/repo-a",
			groups[0].items,
		);
	});

	it("disables group action while mark-read batch is in progress", () => {
		const groups = [
			{
				name: "org/repo-a",
				items: [makeItem({ thread_id: "1", unread: true })],
			},
		];

		render(
			<NotificationTable
				groups={groups}
				sortColumn="score"
				sortDirection="desc"
				onSort={vi.fn()}
				onDismiss={vi.fn()}
				onDismissGroupRead={vi.fn()}
				onMarkGroupRead={vi.fn()}
				markingGroupNames={new Set(["org/repo-a"])}
				onOpenTarget={vi.fn()}
				onRequestIgnoreRule={vi.fn()}
				pendingDismissals={new Set()}
				{...resizeProps}
			/>,
		);

		const button = screen.getByRole("button", {
			name: /Mark all visible unread notifications in org\/repo-a as read/,
		});
		expect(button).toBeDisabled();
		expect(button).toHaveTextContent("Marking...");
	});
});
