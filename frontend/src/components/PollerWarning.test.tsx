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

describe("PollerWarning", () => {
	it("renders null when status is ok and not stale", () => {
		const { container } = render(
			<PollerWarning poller={makePoller({ status: "ok", stale: false })} />,
		);
		expect(container.firstChild).toBeNull();
	});

	it("renders error alert with last_error message", () => {
		render(
			<PollerWarning
				poller={makePoller({
					status: "error",
					last_error: "line1\nline2\nline3\nlast two lines",
				})}
			/>,
		);
		const alert = screen.getByRole("alert");
		expect(alert).toHaveClass("poller-warning--error");
		expect(alert).toHaveTextContent("line3 last two lines");
	});

	it("renders error alert with default message when last_error is null", () => {
		render(
			<PollerWarning
				poller={makePoller({ status: "error", last_error: null })}
			/>,
		);
		const alert = screen.getByRole("alert");
		expect(alert).toHaveClass("poller-warning--error");
		expect(alert).toHaveTextContent("Poller encountered an error.");
	});

	it("renders pending alert for unknown status", () => {
		render(<PollerWarning poller={makePoller({ status: "unknown" })} />);
		const status = screen.getByRole("status");
		expect(status).toHaveClass("poller-warning--pending");
		expect(status).toHaveTextContent("Waiting for poller to start...");
	});

	it("renders pending alert for starting status", () => {
		render(<PollerWarning poller={makePoller({ status: "starting" })} />);
		const status = screen.getByRole("status");
		expect(status).toHaveClass("poller-warning--pending");
		expect(status).toHaveTextContent("Waiting for poller to start...");
	});

	it("renders stale alert when ok but stale without last_poll_time", () => {
		render(
			<PollerWarning
				poller={makePoller({
					status: "ok",
					stale: true,
					last_poll_time: null,
				})}
			/>,
		);
		const status = screen.getByRole("status");
		expect(status).toHaveClass("poller-warning--stale");
		expect(status).toHaveTextContent("Data may be stale.");
	});

	it("renders stale alert with seconds-ago timestamp", () => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date("2026-04-09T10:01:30Z"));
		render(
			<PollerWarning
				poller={makePoller({
					status: "ok",
					stale: true,
					last_poll_time: "2026-04-09T10:01:00Z",
				})}
			/>,
		);
		const status = screen.getByRole("status");
		expect(status).toHaveTextContent("(last update 30s ago)");
		vi.useRealTimers();
	});

	it("renders stale alert with minutes-ago timestamp", () => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date("2026-04-09T10:05:00Z"));
		render(
			<PollerWarning
				poller={makePoller({
					status: "ok",
					stale: true,
					last_poll_time: "2026-04-09T10:00:00Z",
				})}
			/>,
		);
		const status = screen.getByRole("status");
		expect(status).toHaveTextContent("(last update 5m ago)");
		vi.useRealTimers();
	});

	it("renders stale alert with hours-ago timestamp", () => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date("2026-04-09T12:00:00Z"));
		render(
			<PollerWarning
				poller={makePoller({
					status: "ok",
					stale: true,
					last_poll_time: "2026-04-09T10:00:00Z",
				})}
			/>,
		);
		const status = screen.getByRole("status");
		expect(status).toHaveTextContent("(last update 2h ago)");
		vi.useRealTimers();
	});

	it("handles invalid last_poll_time gracefully", () => {
		render(
			<PollerWarning
				poller={makePoller({
					status: "ok",
					stale: true,
					last_poll_time: "not-a-date",
				})}
			/>,
		);
		const status = screen.getByRole("status");
		expect(status).toHaveTextContent("Data may be stale.");
	});
});
