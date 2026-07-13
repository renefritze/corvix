import { render, screen } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { PollerStatus } from "../types";
import PollerWarning from "./PollerWarning.svelte";

function makePoller(overrides: Partial<PollerStatus> = {}): PollerStatus {
	return {
		status: "ok",
		last_poll_time: null,
		last_error: null,
		last_error_time: null,
		stale: false,
		account_errors: [],
		...overrides,
	};
}

describe("PollerWarning", () => {
	afterEach(() => {
		vi.useRealTimers();
	});

	it("renders nothing when status is ok and not stale", () => {
		const { container } = render(PollerWarning, {
			props: { poller: makePoller() },
		});
		expect(container.querySelector(".poller")).toBeNull();
	});

	it("shows the last two lines of last_error in an alert", () => {
		render(PollerWarning, {
			props: {
				poller: makePoller({
					status: "error",
					last_error: "line1\nline2\nline3\nlast two lines",
				}),
			},
		});
		expect(screen.getByRole("alert")).toHaveTextContent("line3 last two lines");
	});

	it("uses a default error message when last_error is null", () => {
		render(PollerWarning, {
			props: { poller: makePoller({ status: "error", last_error: null }) },
		});
		expect(screen.getByRole("alert")).toHaveTextContent(
			"Poller encountered an error.",
		);
	});

	it("appends the last error time when present", () => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date("2026-04-09T10:00:30Z"));
		render(PollerWarning, {
			props: {
				poller: makePoller({
					status: "error",
					last_error: "kaboom",
					last_error_time: "2026-04-09T10:00:00Z",
				}),
			},
		});
		expect(screen.getByRole("alert")).toHaveTextContent("(30s ago)");
	});

	it.each(["unknown", "starting"])(
		"shows the waiting-for-poller status for status %s",
		(status) => {
			render(PollerWarning, { props: { poller: makePoller({ status }) } });
			expect(screen.getByRole("status")).toHaveTextContent(
				"Waiting for poller to start...",
			);
		},
	);

	it("shows the stale warning without a timestamp when last_poll_time is null", () => {
		render(PollerWarning, {
			props: { poller: makePoller({ stale: true, last_poll_time: null }) },
		});
		expect(screen.getByRole("status")).toHaveTextContent("Data may be stale.");
	});

	it("ignores an unparseable last_poll_time when stale", () => {
		render(PollerWarning, {
			props: { poller: makePoller({ stale: true, last_poll_time: "nope" }) },
		});
		expect(screen.getByRole("status")).toHaveTextContent("Data may be stale.");
		expect(screen.getByRole("status")).not.toHaveTextContent("last update");
	});

	it("formats an hours-ago last-update timestamp", () => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date("2026-04-09T12:00:00Z"));
		render(PollerWarning, {
			props: {
				poller: makePoller({
					stale: true,
					last_poll_time: "2026-04-09T10:00:00Z",
				}),
			},
		});
		expect(screen.getByRole("status")).toHaveTextContent("(last update 2h ago)");
	});

	it("shows the stale warning with a formatted last-update timestamp", () => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date("2026-04-09T10:05:00Z"));
		render(PollerWarning, {
			props: {
				poller: makePoller({
					stale: true,
					last_poll_time: "2026-04-09T10:00:00Z",
				}),
			},
		});
		expect(screen.getByRole("status")).toHaveTextContent(
			"Data may be stale (last update 5m ago).",
		);
	});

	it("does not show the stale warning when status is error", () => {
		render(PollerWarning, {
			props: {
				poller: makePoller({ status: "error", stale: true, last_error: "x" }),
			},
		});
		// Only the error alert should render, no stale status.
		expect(screen.queryByRole("status")).toBeNull();
		expect(screen.getByRole("alert")).toBeInTheDocument();
	});

	it("renders a banner per account error", () => {
		render(PollerWarning, {
			props: {
				poller: makePoller({
					account_errors: [
						{
							account_id: "a1",
							account_label: "Account One",
							error: "token expired",
						},
						{ account_id: "a2", account_label: "Account Two", error: "" },
					],
				}),
			},
		});
		const alerts = screen.getAllByRole("alert");
		expect(alerts).toHaveLength(2);
		expect(alerts[0]).toHaveTextContent("Account One");
		expect(alerts[0]).toHaveTextContent("token expired");
		// Empty error string falls back to the default message.
		expect(alerts[1]).toHaveTextContent("Failed to fetch notifications.");
	});
});
