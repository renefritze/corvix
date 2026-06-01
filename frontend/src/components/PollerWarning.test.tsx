import { render, screen } from "@testing-library/preact";
import type { PollerStatus } from "../types";
import { PollerWarning } from "./PollerWarning";

function makePoller(overrides: Partial<PollerStatus> = {}): PollerStatus {
	return {
		status: "ok",
		last_poll_time: null,
		last_error: null,
		last_error_time: null,
		stale: false,
		...overrides,
	};
}

function renderAlert(poller: PollerStatus) {
	render(<PollerWarning poller={poller} />);
	return screen.getByRole("alert");
}

function renderStatus(poller: PollerStatus) {
	render(<PollerWarning poller={poller} />);
	return screen.getByRole("status");
}

function makeStalePoller(overrides: Partial<PollerStatus> = {}) {
	return makePoller({ status: "ok", stale: true, ...overrides });
}

describe("PollerWarning", () => {
	it("renders null when status is ok and not stale", () => {
		const { container } = render(<PollerWarning poller={makePoller()} />);
		expect(container.firstChild).toBeNull();
	});

	describe("error status", () => {
		it.each([
			[
				"uses last_error message when present",
				"line1\nline2\nline3\nlast two lines",
				"line3 last two lines",
			],
			[
				"uses default message when last_error is null",
				null,
				"Poller encountered an error.",
			],
		])("%s", (_, lastError, expectedText) => {
			const alert = renderAlert(
				makePoller({ status: "error", last_error: lastError }),
			);
			expect(alert).toHaveTextContent(expectedText);
		});
	});

	describe("pending status", () => {
		it.each(["unknown", "starting"])(
			"renders pending alert for status %s",
			(status) => {
				const el = renderStatus(makePoller({ status }));
				expect(el).toHaveTextContent("Waiting for poller to start...");
			},
		);
	});

	describe("stale status", () => {
		it("renders stale alert without timestamp when last_poll_time is null", () => {
			const el = renderStatus(makeStalePoller({ last_poll_time: null }));
			expect(el).toHaveTextContent("Data may be stale.");
		});

		it("renders stale alert without timestamp when last_poll_time is invalid", () => {
			const el = renderStatus(
				makeStalePoller({ last_poll_time: "not-a-date" }),
			);
			expect(el).toHaveTextContent("Data may be stale.");
		});

		it.each([
			[
				new Date("2026-04-09T10:01:30Z"),
				"2026-04-09T10:01:00Z",
				"(last update 30s ago)",
			],
			[
				new Date("2026-04-09T10:05:00Z"),
				"2026-04-09T10:00:00Z",
				"(last update 5m ago)",
			],
			[
				new Date("2026-04-09T12:00:00Z"),
				"2026-04-09T10:00:00Z",
				"(last update 2h ago)",
			],
		])("renders timestamp %s", (now, lastPollTime, expectedText) => {
			vi.useFakeTimers();
			vi.setSystemTime(now);
			const el = renderStatus(
				makeStalePoller({ last_poll_time: lastPollTime }),
			);
			expect(el).toHaveTextContent(expectedText);
			vi.useRealTimers();
		});
	});
});
