import { render, screen } from "@testing-library/preact";
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
						isPendingDismissal={false}
					/>
				</tbody>
			</table>,
		);

		await user.click(screen.getByRole("link", { name: "Done" }));
		expect(onOpenTarget).not.toHaveBeenCalled();
	});
});
