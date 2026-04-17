import { render, screen, waitFor } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { fetchSnapshot } from "../api";
import { makeSnapshot } from "../test/fixtures";
import { useSnapshot } from "./useSnapshot";

vi.mock("../api", () => ({
	fetchSnapshot: vi.fn(),
}));

function Harness({ dashboard }: { dashboard?: string }) {
	const { snapshot, loading, refreshing, manualRefreshing, error, refresh } =
		useSnapshot(dashboard);
	return (
		<div>
			<div data-testid="loading">{String(loading)}</div>
			<div data-testid="refreshing">{String(refreshing)}</div>
			<div data-testid="manual-refreshing">{String(manualRefreshing)}</div>
			<div data-testid="name">{snapshot?.name ?? "none"}</div>
			<div data-testid="error">{error ?? "none"}</div>
			<button type="button" onClick={() => void refresh()}>
				refresh
			</button>
		</div>
	);
}

describe("useSnapshot", () => {
	it("loads initial snapshot and handles refresh", async () => {
		const mockedFetch = vi.mocked(fetchSnapshot);
		mockedFetch.mockResolvedValue(makeSnapshot({ name: "overview" }));

		render(<Harness dashboard="overview" />);

		await waitFor(() => {
			expect(screen.getByTestId("name")).toHaveTextContent("overview");
		});
		expect(screen.getByTestId("loading")).toHaveTextContent("false");
		expect(mockedFetch).toHaveBeenCalledWith("overview");

		const user = userEvent.setup();
		await user.click(screen.getByRole("button", { name: "refresh" }));
		await waitFor(() => {
			expect(mockedFetch).toHaveBeenCalledTimes(2);
		});
	});

	it("surfaces fetch errors", async () => {
		const mockedFetch = vi.mocked(fetchSnapshot);
		mockedFetch.mockRejectedValue(new Error("boom"));

		render(<Harness />);

		await waitFor(() => {
			expect(screen.getByTestId("error")).toHaveTextContent("boom");
		});
		expect(screen.getByTestId("loading")).toHaveTextContent("false");
	});

	it("queues a reload if another request arrives while in flight", async () => {
		const mockedFetch = vi.mocked(fetchSnapshot);
		let resolver: ((value: ReturnType<typeof makeSnapshot>) => void) | null =
			null;
		mockedFetch.mockImplementation(
			() =>
				new Promise((resolve) => {
					resolver = resolve;
				}),
		);

		render(<Harness />);

		const user = userEvent.setup();
		await user.click(screen.getByRole("button", { name: "refresh" }));
		expect(mockedFetch).toHaveBeenCalledTimes(1);

		resolver?.(makeSnapshot({ name: "first" }));
		await waitFor(() => {
			expect(mockedFetch).toHaveBeenCalledTimes(2);
		});
	});

	it("does not mark manual refresh state during auto-refresh", async () => {
		vi.useFakeTimers();
		const mockedFetch = vi.mocked(fetchSnapshot);
		let autoResolver:
			| ((value: ReturnType<typeof makeSnapshot>) => void)
			| null = null;
		mockedFetch
			.mockResolvedValueOnce(makeSnapshot({ name: "overview" }))
			.mockImplementationOnce(
				() =>
					new Promise((resolve) => {
						autoResolver = resolve;
					}),
			);

		render(<Harness dashboard="overview" />);

		await waitFor(() => {
			expect(screen.getByTestId("name")).toHaveTextContent("overview");
		});

		await vi.advanceTimersByTimeAsync(15_000);

		await waitFor(() => {
			expect(screen.getByTestId("refreshing")).toHaveTextContent("true");
		});
		expect(screen.getByTestId("manual-refreshing")).toHaveTextContent("false");

		autoResolver?.(makeSnapshot({ name: "overview" }));
		await waitFor(() => {
			expect(screen.getByTestId("refreshing")).toHaveTextContent("false");
		});

		vi.useRealTimers();
	});
});
