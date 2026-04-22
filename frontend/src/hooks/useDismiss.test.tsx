import { fireEvent, render, screen, waitFor } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { dismissNotification } from "../api";
import { useDismiss } from "./useDismiss";

vi.mock("../api", () => ({
	dismissNotification: vi.fn(),
}));

function deferred<T>() {
	let resolve!: (value: T | PromiseLike<T>) => void;
	const promise = new Promise<T>((res) => {
		resolve = res;
	});
	return { promise, resolve };
}

function Harness({
	currentThreadIds,
	onRefresh,
	onError,
}: Readonly<{
	currentThreadIds: Set<string>;
	onRefresh: () => Promise<void>;
	onError: (message: string) => void;
}>) {
	const { pending, dismiss, undo, undoAll, hiddenThreadIds } = useDismiss(
		onRefresh,
		onError,
		currentThreadIds,
	);

	return (
		<div>
			<div data-testid="pending-size">{pending.size}</div>
			<div data-testid="hidden-size">{hiddenThreadIds.size}</div>
			<button type="button" onClick={() => dismiss("primary", "thread-1")}>
				dismiss
			</button>
			<button type="button" onClick={() => dismiss("primary", "thread-2")}>
				dismiss-2
			</button>
			<button type="button" onClick={() => undo("primary", "thread-1")}>
				undo
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
		const request = deferred<void>();
		vi.mocked(dismissNotification).mockReturnValue(request.promise);
		const onRefresh = vi.fn().mockResolvedValue(undefined);
		const onError = vi.fn();
		const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

		render(
			<Harness
				currentThreadIds={new Set(["primary:thread-1"])}
				onRefresh={onRefresh}
				onError={onError}
			/>,
		);

		await user.click(screen.getByRole("button", { name: "dismiss" }));
		expect(screen.getByTestId("pending-size")).toHaveTextContent("1");

		vi.advanceTimersByTime(3_100);
		expect(screen.getByTestId("pending-size")).toHaveTextContent("1");
		expect(screen.getByTestId("hidden-size")).toHaveTextContent("1");

		request.resolve();
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
				currentThreadIds={new Set(["primary:thread-1"])}
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
				currentThreadIds={new Set(["primary:thread-1"])}
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

	it("undo cancels one pending dismissal", async () => {
		vi.useFakeTimers();
		vi.mocked(dismissNotification).mockResolvedValue(undefined);
		const onRefresh = vi.fn().mockResolvedValue(undefined);
		const onError = vi.fn();

		render(
			<Harness
				currentThreadIds={new Set(["primary:thread-1", "primary:thread-2"])}
				onRefresh={onRefresh}
				onError={onError}
			/>,
		);

		fireEvent.click(screen.getByRole("button", { name: "dismiss" }));
		expect(screen.getByTestId("pending-size")).toHaveTextContent("1");

		fireEvent.click(screen.getByRole("button", { name: "undo" }));
		expect(screen.getByTestId("pending-size")).toHaveTextContent("0");

		vi.advanceTimersByTime(3_500);
		expect(dismissNotification).not.toHaveBeenCalled();
		expect(onRefresh).not.toHaveBeenCalled();
	});

	it("replaces existing pending timer on repeated dismiss", async () => {
		vi.useFakeTimers();
		vi.mocked(dismissNotification).mockResolvedValue(undefined);
		const onRefresh = vi.fn().mockResolvedValue(undefined);
		const onError = vi.fn();

		render(
			<Harness
				currentThreadIds={new Set(["primary:thread-1"])}
				onRefresh={onRefresh}
				onError={onError}
			/>,
		);

		fireEvent.click(screen.getByRole("button", { name: "dismiss" }));
		expect(screen.getByTestId("pending-size")).toHaveTextContent("1");
		fireEvent.click(screen.getByRole("button", { name: "dismiss" }));

		expect(screen.getByTestId("pending-size")).toHaveTextContent("1");

		vi.advanceTimersByTime(3_500);
		await waitFor(() => {
			expect(dismissNotification).toHaveBeenCalledTimes(1);
		});
	});

	it("does not re-dismiss committed threads", async () => {
		vi.useFakeTimers();
		vi.mocked(dismissNotification).mockResolvedValue(undefined);
		const onRefresh = vi.fn().mockResolvedValue(undefined);
		const onError = vi.fn();
		const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

		render(
			<Harness
				currentThreadIds={new Set(["primary:thread-1"])}
				onRefresh={onRefresh}
				onError={onError}
			/>,
		);

		await user.click(screen.getByRole("button", { name: "dismiss" }));
		vi.advanceTimersByTime(3_500);
		await waitFor(() => {
			expect(dismissNotification).toHaveBeenCalledTimes(1);
		});

		await user.click(screen.getByRole("button", { name: "dismiss" }));
		vi.advanceTimersByTime(3_500);
		expect(dismissNotification).toHaveBeenCalledTimes(1);
		expect(onError).not.toHaveBeenCalled();
	});

	it("drops committed entries when the thread no longer exists", async () => {
		vi.useFakeTimers();
		vi.mocked(dismissNotification).mockResolvedValue(undefined);
		const onRefresh = vi.fn().mockResolvedValue(undefined);
		const onError = vi.fn();
		const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

		const { rerender } = render(
			<Harness
				currentThreadIds={new Set(["primary:thread-1"])}
				onRefresh={onRefresh}
				onError={onError}
			/>,
		);

		await user.click(screen.getByRole("button", { name: "dismiss" }));
		vi.advanceTimersByTime(3_500);
		await waitFor(() => {
			expect(screen.getByTestId("hidden-size")).toHaveTextContent("1");
		});

		rerender(
			<Harness
				currentThreadIds={new Set()}
				onRefresh={onRefresh}
				onError={onError}
			/>,
		);

		await waitFor(() => {
			expect(screen.getByTestId("hidden-size")).toHaveTextContent("0");
		});
	});

	it("reports refresh errors after a successful dismiss call", async () => {
		vi.useFakeTimers();
		vi.mocked(dismissNotification).mockResolvedValue(undefined);
		const onRefresh = vi.fn().mockRejectedValue(new Error("refresh boom"));
		const onError = vi.fn();
		const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

		render(
			<Harness
				currentThreadIds={new Set(["primary:thread-1"])}
				onRefresh={onRefresh}
				onError={onError}
			/>,
		);

		await user.click(screen.getByRole("button", { name: "dismiss" }));
		vi.advanceTimersByTime(3_500);

		await waitFor(() => {
			expect(onError).toHaveBeenCalledWith("refresh boom");
		});
		expect(screen.getByTestId("pending-size")).toHaveTextContent("0");
	});
});
