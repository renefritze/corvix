import { act, render, screen, waitFor } from "@testing-library/preact";
import { fetchSnapshot } from "../api";
import { makeSnapshot } from "../test/fixtures";
import { useSnapshot } from "./useSnapshot";

// Keep the real `snapshotEventsUrl` (so we can assert the SSE URL) but stub the
// network fetch used for the initial load and the polling fallback.
vi.mock("../api", async (importOriginal) => {
	const actual = await importOriginal<typeof import("../api")>();
	return { ...actual, fetchSnapshot: vi.fn() };
});

type Listener = (event: MessageEvent) => void;

class MockEventSource {
	static readonly CONNECTING = 0;
	static readonly OPEN = 1;
	static readonly CLOSED = 2;
	static instances: MockEventSource[] = [];

	url: string;
	readyState: number = MockEventSource.CONNECTING;
	onerror: ((event: Event) => void) | null = null;
	closed = false;
	private readonly listeners = new Map<string, Listener[]>();

	constructor(url: string) {
		this.url = url;
		MockEventSource.instances.push(this);
	}

	addEventListener(type: string, callback: Listener): void {
		const existing = this.listeners.get(type) ?? [];
		existing.push(callback);
		this.listeners.set(type, existing);
	}

	close(): void {
		this.closed = true;
		this.readyState = MockEventSource.CLOSED;
	}

	emit(type: string, data: string): void {
		for (const callback of this.listeners.get(type) ?? []) {
			callback({ data } as MessageEvent);
		}
	}

	emitConnectionError(readyState: number): void {
		this.readyState = readyState;
		this.onerror?.(new Event("error"));
	}
}

function Harness({ dashboard }: Readonly<{ dashboard?: string }>) {
	const { snapshot, error } = useSnapshot(dashboard);
	return (
		<div>
			<div data-testid="name">{snapshot?.name ?? "none"}</div>
			<div data-testid="error">{error ?? "none"}</div>
		</div>
	);
}

describe("useSnapshot (SSE)", () => {
	beforeEach(() => {
		MockEventSource.instances = [];
		vi.stubGlobal("EventSource", MockEventSource);
		vi.mocked(fetchSnapshot).mockResolvedValue(makeSnapshot({ name: "initial" }));
	});

	afterEach(() => {
		vi.unstubAllGlobals();
		vi.useRealTimers();
		vi.clearAllMocks();
	});

	it("opens an EventSource with the dashboard-scoped URL", async () => {
		render(<Harness dashboard="overview" />);
		await waitFor(() => {
			expect(MockEventSource.instances).toHaveLength(1);
		});
		expect(MockEventSource.instances[0].url).toBe(
			"/api/v1/events?dashboard=overview",
		);
	});

	it("updates the snapshot from a pushed 'snapshot' event", async () => {
		render(<Harness />);
		await waitFor(() => {
			expect(MockEventSource.instances).toHaveLength(1);
		});
		const source = MockEventSource.instances[0];
		expect(source.url).toBe("/api/v1/events");

		act(() => {
			source.emit("snapshot", JSON.stringify(makeSnapshot({ name: "live" })));
		});

		await waitFor(() => {
			expect(screen.getByTestId("name")).toHaveTextContent("live");
		});
		expect(screen.getByTestId("error")).toHaveTextContent("none");
	});

	it("ignores malformed 'snapshot' frames", async () => {
		render(<Harness />);
		await waitFor(() => {
			expect(screen.getByTestId("name")).toHaveTextContent("initial");
		});
		const source = MockEventSource.instances[0];

		act(() => {
			source.emit("snapshot", "not-json{");
		});

		// The bad frame is swallowed; the last good snapshot remains.
		expect(screen.getByTestId("name")).toHaveTextContent("initial");
	});

	it("surfaces a server 'snapshot-error' event", async () => {
		render(<Harness />);
		await waitFor(() => {
			expect(MockEventSource.instances).toHaveLength(1);
		});
		const source = MockEventSource.instances[0];

		act(() => {
			source.emit(
				"snapshot-error",
				JSON.stringify({ detail: "config broken", status_code: 500 }),
			);
		});

		await waitFor(() => {
			expect(screen.getByTestId("error")).toHaveTextContent("config broken");
		});
	});

	it("falls back to a generic message for a non-JSON 'snapshot-error'", async () => {
		render(<Harness />);
		await waitFor(() => {
			expect(MockEventSource.instances).toHaveLength(1);
		});
		const source = MockEventSource.instances[0];

		act(() => {
			source.emit("snapshot-error", "boom");
		});

		await waitFor(() => {
			expect(screen.getByTestId("error")).toHaveTextContent(
				"Snapshot stream error",
			);
		});
	});

	it("polls as a fallback only after the connection is permanently closed", async () => {
		vi.useFakeTimers();
		render(<Harness />);
		await vi.waitFor(() => {
			expect(MockEventSource.instances).toHaveLength(1);
		});
		const source = MockEventSource.instances[0];
		const callsAfterInitial = vi.mocked(fetchSnapshot).mock.calls.length;

		// A transient error (still connecting) must NOT start polling.
		act(() => {
			source.emitConnectionError(MockEventSource.CONNECTING);
		});
		await vi.advanceTimersByTimeAsync(30_000);
		expect(vi.mocked(fetchSnapshot).mock.calls.length).toBe(callsAfterInitial);

		// A permanent close DOES start the polling fallback.
		act(() => {
			source.emitConnectionError(MockEventSource.CLOSED);
		});
		await vi.advanceTimersByTimeAsync(15_000);
		expect(vi.mocked(fetchSnapshot).mock.calls.length).toBeGreaterThan(
			callsAfterInitial,
		);
	});

	it("closes the EventSource on unmount", async () => {
		const { unmount } = render(<Harness />);
		await waitFor(() => {
			expect(MockEventSource.instances).toHaveLength(1);
		});
		const source = MockEventSource.instances[0];
		unmount();
		expect(source.closed).toBe(true);
	});

	it("does not start polling when an error fires after unmount", async () => {
		vi.useFakeTimers();
		const { unmount } = render(<Harness />);
		await vi.waitFor(() => {
			expect(MockEventSource.instances).toHaveLength(1);
		});
		const source = MockEventSource.instances[0];
		const callsBefore = vi.mocked(fetchSnapshot).mock.calls.length;

		unmount();
		// A late error dispatched during/after close must not start a fallback
		// interval that would outlive the unmounted component.
		act(() => {
			source.emitConnectionError(MockEventSource.CLOSED);
		});
		await vi.advanceTimersByTimeAsync(30_000);

		expect(vi.mocked(fetchSnapshot).mock.calls.length).toBe(callsBefore);
	});
});
