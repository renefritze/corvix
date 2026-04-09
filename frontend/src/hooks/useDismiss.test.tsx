import { fireEvent, render, screen, waitFor } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { dismissNotification } from "../api";
import { useDismiss } from "./useDismiss";

vi.mock("../api", () => ({
	dismissNotification: vi.fn(),
}));

function Harness({
	currentThreadIds,
	onRefresh,
	onError,
}: {
	currentThreadIds: Set<string>;
	onRefresh: () => Promise<void>;
	onError: (message: string) => void;
}) {
	const { pending, dismiss, undoAll, hiddenThreadIds } = useDismiss(
		onRefresh,
		onError,
		currentThreadIds,
	);

	return (
		<div>
			<div data-testid="pending-size">{pending.size}</div>
			<div data-testid="hidden-size">{hiddenThreadIds.size}</div>
			<button type="button" onClick={() => dismiss("thread-1")}>
				dismiss
			</button>
			<button type="button" onClick={undoAll}>
				undo-all
			</button>
		</div>
	);
}

describe("useDismiss", () => {
	it("queues and commits dismissal after timeout", async () => {
		vi.useFakeTimers();
		vi.mocked(dismissNotification).mockResolvedValue(undefined);
		const onRefresh = vi.fn().mockResolvedValue(undefined);
		const onError = vi.fn();
		const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

		render(
			<Harness
				currentThreadIds={new Set(["thread-1"])}
				onRefresh={onRefresh}
				onError={onError}
			/>,
		);

		await user.click(screen.getByRole("button", { name: "dismiss" }));
		expect(screen.getByTestId("pending-size")).toHaveTextContent("1");

		vi.advanceTimersByTime(3_100);
		await waitFor(() => {
			expect(screen.getByTestId("pending-size")).toHaveTextContent("0");
		});
		expect(onRefresh).toHaveBeenCalledTimes(1);
		expect(onError).not.toHaveBeenCalled();
		expect(screen.getByTestId("hidden-size")).toHaveTextContent("1");
	});

	it("undo all cancels pending dismissals", async () => {
		vi.useFakeTimers();
		vi.mocked(dismissNotification).mockResolvedValue(undefined);
		const onRefresh = vi.fn().mockResolvedValue(undefined);
		const onError = vi.fn();

		render(
			<Harness
				currentThreadIds={new Set(["thread-1"])}
				onRefresh={onRefresh}
				onError={onError}
			/>,
		);
		fireEvent.click(screen.getByRole("button", { name: "dismiss" }));
		expect(screen.getByTestId("pending-size")).toHaveTextContent("1");

		fireEvent.click(screen.getByRole("button", { name: "undo-all" }));
		expect(screen.getByTestId("pending-size")).toHaveTextContent("0");

		vi.advanceTimersByTime(3_500);
		expect(dismissNotification).not.toHaveBeenCalled();
		expect(onRefresh).not.toHaveBeenCalled();
		expect(onError).not.toHaveBeenCalled();
	});

	it("reports errors from dismiss API", async () => {
		vi.useFakeTimers();
		vi.mocked(dismissNotification).mockRejectedValue(new Error("network"));
		const onRefresh = vi.fn().mockResolvedValue(undefined);
		const onError = vi.fn();
		const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

		render(
			<Harness
				currentThreadIds={new Set(["thread-1"])}
				onRefresh={onRefresh}
				onError={onError}
			/>,
		);

		await user.click(screen.getByRole("button", { name: "dismiss" }));
		vi.advanceTimersByTime(3_100);
		await waitFor(() => {
			expect(onError).toHaveBeenCalledWith("network");
		});
		expect(onRefresh).not.toHaveBeenCalled();
	});
});
