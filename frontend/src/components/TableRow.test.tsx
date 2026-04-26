import { fireEvent, render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { makeItem } from "../test/fixtures";
import { TableRow } from "./TableRow";

describe("TableRow", () => {
	it("renders fields and forwards callbacks", async () => {
		const onDismiss = vi.fn();
		const onOpenTarget = vi.fn();
		const user = userEvent.setup();

		render(
			<table>
				<tbody>
					<TableRow
						item={makeItem({ thread_id: "t-1", subject_title: "My title" })}
						onDismiss={onDismiss}
						onOpenTarget={onOpenTarget}
						onRequestIgnoreRule={vi.fn()}
						isPendingDismissal={false}
					/>
				</tbody>
			</table>,
		);

		expect(screen.getByText("My title")).toBeInTheDocument();
		expect(screen.getByText("org/repo-a")).toBeInTheDocument();

		await user.click(screen.getByRole("link", { name: "My title" }));
		expect(onOpenTarget).toHaveBeenCalledWith("primary", "t-1");

		await user.click(screen.getByRole("button", { name: "Dismiss My title" }));
		expect(onDismiss).toHaveBeenCalledWith("primary", "t-1");
	});

	it("does not mark already read items as opened", async () => {
		const onOpenTarget = vi.fn();
		const user = userEvent.setup();

		render(
			<table>
				<tbody>
					<TableRow
						item={makeItem({
							thread_id: "t-2",
							unread: false,
							subject_title: "Done",
						})}
						onDismiss={vi.fn()}
						onOpenTarget={onOpenTarget}
						onRequestIgnoreRule={vi.fn()}
						isPendingDismissal={false}
					/>
				</tbody>
			</table>,
		);

		await user.click(screen.getByRole("link", { name: "Done" }));
		expect(onOpenTarget).not.toHaveBeenCalled();
	});

	it("marks unread items as opened on middle click", async () => {
		const onOpenTarget = vi.fn();

		render(
			<table>
				<tbody>
					<TableRow
						item={makeItem({ thread_id: "t-3", subject_title: "Middle" })}
						onDismiss={vi.fn()}
						onOpenTarget={onOpenTarget}
						onRequestIgnoreRule={vi.fn()}
						isPendingDismissal={false}
					/>
				</tbody>
			</table>,
		);

		screen
			.getByRole("link", { name: "Middle" })
			.dispatchEvent(new MouseEvent("auxclick", { bubbles: true, button: 1 }));

		expect(onOpenTarget).toHaveBeenCalledWith("primary", "t-3");
	});

	it("renders plain title text when web_url is missing", () => {
		render(
			<table>
				<tbody>
					<TableRow
						item={makeItem({
							thread_id: "t-4",
							subject_title: "No Link",
							web_url: null,
						})}
						onDismiss={vi.fn()}
						onOpenTarget={vi.fn()}
						onRequestIgnoreRule={vi.fn()}
						isPendingDismissal={false}
					/>
				</tbody>
			</table>,
		);

		expect(screen.queryByRole("link", { name: "No Link" })).toBeNull();
		expect(screen.getByText("No Link")).toBeInTheDocument();
	});

	it("opens row actions from context menu and actions button", async () => {
		const onRequestIgnoreRule = vi.fn();
		const user = userEvent.setup();

		render(
			<table>
				<tbody>
					<TableRow
						item={makeItem({ thread_id: "t-3", subject_title: "Has menu" })}
						onDismiss={vi.fn()}
						onOpenTarget={vi.fn()}
						onRequestIgnoreRule={onRequestIgnoreRule}
						isPendingDismissal={false}
					/>
				</tbody>
			</table>,
		);

		const row = screen.getByRole("row");
		fireEvent.contextMenu(row, { clientX: 120, clientY: 140 });
		expect(onRequestIgnoreRule).toHaveBeenNthCalledWith(
			1,
			expect.objectContaining({ thread_id: "t-3" }),
			{ x: 120, y: 140 },
		);

		const menuButton = screen.getByRole("button", {
			name: "Notification actions for Has menu",
		});
		vi.spyOn(menuButton, "getBoundingClientRect").mockReturnValue({
			left: 40,
			right: 60,
			top: 20,
			bottom: 50,
			width: 20,
			height: 30,
			x: 40,
			y: 20,
			toJSON: () => ({}),
		} as DOMRect);

		await user.click(menuButton);
		expect(onRequestIgnoreRule).toHaveBeenNthCalledWith(
			2,
			expect.objectContaining({ thread_id: "t-3" }),
			{ x: 40, y: 54 },
		);
	});
});
