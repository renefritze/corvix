import { render, screen, waitFor } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { makeSnapshot } from "../test/fixtures";
import { type FetchInput, requestUrl, setPath } from "../test/http";
import {
	parseDashboardFromPath,
	useDashboardState,
} from "./useDashboardState";

function Harness() {
	const { currentDashboard, dashboardNames, setDashboard, loading } =
		useDashboardState();
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

function mockSnapshotByDashboard(): void {
	vi.spyOn(globalThis, "fetch").mockImplementation(async (input: FetchInput) => {
		const url = requestUrl(input);
		const name = url.includes("dashboard=triage") ? "triage" : "overview";
		return {
			ok: true,
			json: async () =>
				makeSnapshot({ name, dashboard_names: ["overview", "triage"] }),
		} as Response;
	});
}

describe("parseDashboardFromPath", () => {
	it("extracts and decodes the dashboard name", () => {
		expect(parseDashboardFromPath("/dashboards/Triage%20Board")).toBe(
			"Triage Board",
		);
	});

	it("returns undefined for non-dashboard or empty paths", () => {
		expect(parseDashboardFromPath("/")).toBeUndefined();
		expect(parseDashboardFromPath("/dashboards/")).toBeUndefined();
	});
});

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

	it("selects a dashboard and pushes the matching path", async () => {
		setPath("/");
		mockSnapshotByDashboard();
		const user = userEvent.setup();

		render(<Harness />);
		await waitFor(() =>
			expect(screen.getByTestId("current")).toHaveTextContent("overview"),
		);

		await user.click(screen.getByRole("button", { name: "select-triage" }));
		await waitFor(() =>
			expect(screen.getByTestId("current")).toHaveTextContent("triage"),
		);
		await waitFor(() =>
			expect(globalThis.location.pathname).toBe("/dashboards/triage"),
		);
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

	it("restores the default dashboard on popstate to an unknown name", async () => {
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
});
