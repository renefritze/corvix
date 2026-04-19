import { render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { useRef } from "preact/hooks";
import { useKeyboard } from "./useKeyboard";

function Harness({
	onRefresh,
	onFocusFilters,
	onDismissFocused,
	onToggleShortcuts,
}: {
	onRefresh: () => void;
	onFocusFilters: () => void;
	onDismissFocused: () => void;
	onToggleShortcuts: () => void;
}) {
	const filterRef = useRef<HTMLSelectElement | null>(null);
	useKeyboard({
		onRefresh,
		onFocusFilters: () => {
			onFocusFilters();
			filterRef.current?.focus();
		},
		onDismissFocused,
		onToggleShortcuts,
	});

	return (
		<div>
			<select ref={filterRef} aria-label="Unread state filter">
				<option>all</option>
			</select>
			<input aria-label="search" />
			<table>
				<tbody>
					<tr class="notification-row" tabIndex={0} data-testid="row-1">
						<td>
							<a href="#row-1" class="title-link">
								Row 1
							</a>
						</td>
					</tr>
					<tr class="notification-row" tabIndex={0} data-testid="row-2">
						<td>
							<a href="#row-2" class="title-link">
								Row 2
							</a>
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	);
}

describe("useKeyboard", () => {
	it("handles shortcut keys and ignores typing targets", async () => {
		const user = userEvent.setup();
		const onRefresh = vi.fn();
		const onFocusFilters = vi.fn();
		const onDismissFocused = vi.fn();
		const onToggleShortcuts = vi.fn();

		render(
			<Harness
				onRefresh={onRefresh}
				onFocusFilters={onFocusFilters}
				onDismissFocused={onDismissFocused}
				onToggleShortcuts={onToggleShortcuts}
			/>,
		);

		await user.keyboard("r");
		expect(onRefresh).toHaveBeenCalledTimes(1);

		await user.keyboard("?");
		expect(onToggleShortcuts).toHaveBeenCalledTimes(1);

		await user.keyboard("f");
		expect(onFocusFilters).toHaveBeenCalledTimes(1);
		expect(screen.getByLabelText("Unread state filter")).toHaveFocus();

		const firstRow = screen.getByTestId("row-1");
		const secondRow = screen.getByTestId("row-2");
		firstRow.focus();
		await user.keyboard("j");
		expect(secondRow).toHaveFocus();
		await user.keyboard("k");
		expect(firstRow).toHaveFocus();

		await user.keyboard("d");
		expect(onDismissFocused).toHaveBeenCalledTimes(1);

		const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click");
		firstRow.focus();
		await user.keyboard("{Enter}");
		expect(clickSpy).toHaveBeenCalledTimes(1);

		await user.keyboard("{Escape}");
		expect(firstRow).not.toHaveFocus();

		screen.getByLabelText("search").focus();
		await user.keyboard("r");
		expect(onRefresh).toHaveBeenCalledTimes(1);
	});
});
