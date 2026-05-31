import { render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { Router } from "preact-router";
import { beforeEach, describe, expect, it } from "vitest";
import { setPath } from "../test/http";
import { useFilters } from "./useFilters";

function Filters() {
	const { filters, setFilter, clearFilters } = useFilters();
	return (
		<div>
			<div data-testid="state">{JSON.stringify(filters)}</div>
			<button type="button" onClick={() => setFilter("reason", ["subscribed"])}>
				set-reason
			</button>
			<button type="button" onClick={() => setFilter("unread", "read")}>
				set-unread
			</button>
			<button type="button" onClick={clearFilters}>
				clear
			</button>
		</div>
	);
}

// A mounted Router is required for preact-router's route() to update history.
function Harness() {
	return (
		<Router>
			<Filters default />
		</Router>
	);
}

describe("useFilters", () => {
	beforeEach(() => {
		setPath("/");
	});

	it("updates and clears filters", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		expect(screen.getByTestId("state")).toHaveTextContent(
			'{"unread":"all","reason":[],"repository":""}',
		);

		await user.click(screen.getByRole("button", { name: "set-reason" }));
		expect(screen.getByTestId("state")).toHaveTextContent(
			'"reason":["subscribed"]',
		);

		await user.click(screen.getByRole("button", { name: "set-unread" }));
		expect(screen.getByTestId("state")).toHaveTextContent('"unread":"read"');

		await user.click(screen.getByRole("button", { name: "clear" }));
		expect(screen.getByTestId("state")).toHaveTextContent(
			'{"unread":"all","reason":[],"repository":""}',
		);
	});

	it("mirrors filter changes into the URL query string", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		await user.click(screen.getByRole("button", { name: "set-reason" }));
		expect(globalThis.location.search).toBe("?reason=subscribed");

		await user.click(screen.getByRole("button", { name: "set-unread" }));
		expect(globalThis.location.search).toBe("?reason=subscribed&unread=read");

		await user.click(screen.getByRole("button", { name: "clear" }));
		expect(globalThis.location.search).toBe("");
	});

	it("initializes filter state from the URL query", () => {
		setPath("/?unread=read&reason=mention,subscribed&repository=org/repo");
		render(<Harness />);

		expect(screen.getByTestId("state")).toHaveTextContent(
			'{"unread":"read","reason":["mention","subscribed"],"repository":"org/repo"}',
		);
	});
});
