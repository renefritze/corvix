import { render, screen, waitFor } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { Router } from "preact-router";
import { makeSnapshot } from "../test/fixtures";
import { type FetchInput, requestUrl, setPath } from "../test/http";
import { useDashboardState } from "./useDashboardState";

interface DashboardProps {
	readonly name?: string;
}

function Dashboard({ name }: DashboardProps) {
	const { currentDashboard, dashboardNames, setDashboard, loading } =
		useDashboardState(name);
	return (
		<div>
			<div data-testid="loading">{String(loading)}</div>
			<div data-testid="current">{currentDashboard ?? "none"}</div>
			<div data-testid="names">{dashboardNames.join(",")}</div>
			<button type="button" onClick={() => setDashboard("triage")}>
				select-triage
			</button>
		</div>
	);
}

function Harness() {
	return (
		<Router>
			<Dashboard path="/" />
			<Dashboard path="/dashboards/:name" />
		</Router>
	);
}

function mockSnapshotByDashboard(): void {
	vi.spyOn(globalThis, "fetch").mockImplementation(
		async (input: FetchInput) => {
			const url = requestUrl(input);
			const name = url.includes("dashboard=triage") ? "triage" : "overview";
			return {
				ok: true,
				json: async () =>
					makeSnapshot({ name, dashboard_names: ["overview", "triage"] }),
			} as Response;
		},
	);
}

describe("useDashboardState", () => {
	it("defaults to the first dashboard and normalizes the URL", async () => {
		setPath("/");
		mockSnapshotByDashboard();

		render(<Harness />);

		await waitFor(() =>
			expect(screen.getByTestId("current")).toHaveTextContent("overview"),
		);
		expect(screen.getByTestId("names")).toHaveTextContent("overview,triage");
		await waitFor(() =>
			expect(globalThis.location.pathname).toBe("/dashboards/overview"),
		);
	});

	it("selects a dashboard and pushes a new history entry", async () => {
		setPath("/");
		mockSnapshotByDashboard();
		const user = userEvent.setup();

		render(<Harness />);
		await waitFor(() =>
			expect(globalThis.location.pathname).toBe("/dashboards/overview"),
		);

		const lengthBefore = globalThis.history.length;
		await user.click(screen.getByRole("button", { name: "select-triage" }));
		await waitFor(() =>
			expect(screen.getByTestId("current")).toHaveTextContent("triage"),
		);
		await waitFor(() =>
			expect(globalThis.location.pathname).toBe("/dashboards/triage"),
		);
		// A user selection pushes, so a new entry is added to history.
		expect(globalThis.history.length).toBe(lengthBefore + 1);
	});

	it("replaces history when normalizing the URL automatically", async () => {
		setPath("/");
		mockSnapshotByDashboard();
		const lengthBefore = globalThis.history.length;

		render(<Harness />);

		await waitFor(() =>
			expect(globalThis.location.pathname).toBe("/dashboards/overview"),
		);
		// Normalization replaces, so no new history entry is created.
		expect(globalThis.history.length).toBe(lengthBefore);
	});

	it("falls back to the default dashboard for an unknown URL name", async () => {
		setPath("/dashboards/unknown");
		mockSnapshotByDashboard();

		render(<Harness />);

		await waitFor(() =>
			expect(screen.getByTestId("current")).toHaveTextContent("overview"),
		);
		await waitFor(() =>
			expect(globalThis.location.pathname).toBe("/dashboards/overview"),
		);
	});

	it("restores the default dashboard on back navigation to an unknown name", async () => {
		setPath("/dashboards/overview");
		mockSnapshotByDashboard();

		render(<Harness />);
		await waitFor(() =>
			expect(screen.getByTestId("current")).toHaveTextContent("overview"),
		);

		setPath("/dashboards/does-not-exist");
		globalThis.dispatchEvent(new PopStateEvent("popstate"));

		await waitFor(() =>
			expect(globalThis.location.pathname).toBe("/dashboards/overview"),
		);
	});

	it("reads the dashboard name from the route and preserves the query", async () => {
		setPath("/dashboards/triage?unread=unread");
		mockSnapshotByDashboard();

		render(<Harness />);

		await waitFor(() =>
			expect(screen.getByTestId("current")).toHaveTextContent("triage"),
		);
		expect(globalThis.location.pathname).toBe("/dashboards/triage");
		expect(globalThis.location.search).toBe("?unread=unread");
	});
});
