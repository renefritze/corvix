import { render, screen } from "@testing-library/preact";
import { makeItem } from "../test/fixtures";
import { NotificationTable } from "./NotificationTable";

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
				onOpenTarget={vi.fn()}
				pendingDismissals={new Set(["1"])}
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
				onOpenTarget={vi.fn()}
				pendingDismissals={new Set()}
			/>,
		);

		const links = screen.getAllByRole("link");
		expect(links[0]).toHaveTextContent("Alpha");
		expect(links[1]).toHaveTextContent("zulu");
	});
});
