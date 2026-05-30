import { render, screen, waitFor } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { makeItem } from "../test/fixtures";
import { requestUrl } from "../test/http";
import { useMarkRead } from "./useMarkRead";

function Harness({
	onRefresh,
	onError,
}: {
	onRefresh: () => Promise<void>;
	onError: (msg: string) => void;
}) {
	const { markingGroupNames, openTarget, markGroupRead } = useMarkRead(
		onRefresh,
		onError,
	);
	const group = [
		makeItem({ thread_id: "u-1", unread: true }),
		makeItem({ thread_id: "u-2", unread: true }),
		makeItem({ thread_id: "r-1", unread: false }),
	];
	return (
		<div>
			<div data-testid="marking">{[...markingGroupNames].join(",")}</div>
			<button type="button" onClick={() => openTarget("primary", "t-1")}>
				open
			</button>
			<button type="button" onClick={() => markGroupRead("group-a", group)}>
				mark-group
			</button>
			<button type="button" onClick={() => markGroupRead("empty", [])}>
				mark-empty
			</button>
		</div>
	);
}

function renderHarness() {
	const user = userEvent.setup();
	const onRefresh = vi.fn(async () => {});
	const onError = vi.fn();
	const fetchMock = vi.spyOn(globalThis, "fetch");
	render(<Harness onRefresh={onRefresh} onError={onError} />);
	return { user, onRefresh, onError, fetchMock };
}

const MARK_READ_INIT = { method: "POST", keepalive: true };

describe("useMarkRead", () => {
	it("marks a single thread read and refreshes", async () => {
		const { user, onRefresh, onError, fetchMock } = renderHarness();
		fetchMock.mockResolvedValue({ ok: true } as Response);

		await user.click(screen.getByRole("button", { name: "open" }));

		await waitFor(() => expect(onRefresh).toHaveBeenCalledTimes(1));
		expect(fetchMock).toHaveBeenCalledWith(
			"/api/v1/notifications/primary/t-1/mark-read",
			MARK_READ_INIT,
		);
		expect(onError).not.toHaveBeenCalled();
	});

	it("reports an error when a single mark-read fails", async () => {
		const { user, onRefresh, onError, fetchMock } = renderHarness();
		fetchMock.mockResolvedValue({ ok: false, status: 500 } as Response);

		await user.click(screen.getByRole("button", { name: "open" }));

		await waitFor(() =>
			expect(onError).toHaveBeenCalledWith("Mark read failed: 500"),
		);
		expect(onRefresh).not.toHaveBeenCalled();
	});

	it("marks only unread group items, tracks progress, and refreshes", async () => {
		const { user, onRefresh, onError, fetchMock } = renderHarness();
		// Keep the mark-read requests in flight so the group stays "marking".
		const resolvers: Array<(value: Response) => void> = [];
		fetchMock.mockImplementation(
			() =>
				new Promise<Response>((resolve) => {
					resolvers.push(resolve);
				}),
		);

		await user.click(screen.getByRole("button", { name: "mark-group" }));

		await waitFor(() =>
			expect(screen.getByTestId("marking")).toHaveTextContent("group-a"),
		);
		const markReadCalls = fetchMock.mock.calls.filter((call) =>
			requestUrl(call[0]).includes("/mark-read"),
		);
		expect(markReadCalls).toHaveLength(2);
		expect(fetchMock).toHaveBeenCalledWith(
			"/api/v1/notifications/primary/u-1/mark-read",
			MARK_READ_INIT,
		);
		expect(fetchMock).not.toHaveBeenCalledWith(
			"/api/v1/notifications/primary/r-1/mark-read",
			MARK_READ_INIT,
		);

		for (const resolve of resolvers) {
			resolve({ ok: true } as Response);
		}
		await waitFor(() =>
			expect(screen.getByTestId("marking")).toHaveTextContent(""),
		);
		await waitFor(() => expect(onRefresh).toHaveBeenCalledTimes(1));
		expect(onError).not.toHaveBeenCalled();
	});

	it("reports the failure count when group items fail to mark read", async () => {
		const { user, onError, fetchMock } = renderHarness();
		fetchMock.mockResolvedValue({ ok: false, status: 500 } as Response);

		await user.click(screen.getByRole("button", { name: "mark-group" }));

		await waitFor(() =>
			expect(onError).toHaveBeenCalledWith(
				"Mark all read failed for 2 notifications",
			),
		);
	});

	it("does nothing when a group has no unread items", async () => {
		const { user, onRefresh, fetchMock } = renderHarness();

		await user.click(screen.getByRole("button", { name: "mark-empty" }));

		expect(fetchMock).not.toHaveBeenCalled();
		expect(onRefresh).not.toHaveBeenCalled();
	});
});
