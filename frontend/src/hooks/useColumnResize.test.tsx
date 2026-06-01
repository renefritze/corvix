import { fireEvent, render, screen, waitFor } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { useColumnResize } from "./useColumnResize";

const STORAGE_KEY = "corvix.table.columnWidths.v2";
const LEGACY_KEY = "corvix.table.columnWidths";

function Harness() {
	const { widths, startResize, resetColumnWidth, resetLayout } =
		useColumnResize();
	return (
		<div>
			<div data-testid="repo-width">{widths.repository}</div>
			<div data-testid="score-width">{widths.score}</div>
			<button type="button" onMouseDown={() => startResize("repository", 100)}>
				start
			</button>
			<button type="button" onClick={() => resetColumnWidth("repository")}>
				reset
			</button>
			<button type="button" onClick={resetLayout}>
				reset all
			</button>
		</div>
	);
}

describe("useColumnResize", () => {
	it("resizes and resets column width", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		expect(screen.getByTestId("repo-width")).toHaveTextContent("185");
		await user.pointer([
			{
				target: screen.getByRole("button", { name: "start" }),
				keys: "[MouseLeft>]",
			},
		]);
		globalThis.window.dispatchEvent(
			new MouseEvent("mousemove", { clientX: 150 }),
		);
		await waitFor(() => {
			expect(screen.getByTestId("repo-width")).toHaveTextContent("235");
		});

		globalThis.window.dispatchEvent(new MouseEvent("mouseup"));
		await user.click(screen.getByRole("button", { name: "reset" }));
		expect(screen.getByTestId("repo-width")).toHaveTextContent("185");
	});

	it("falls back from invalid storage and clamps at minimum width", async () => {
		localStorage.setItem("corvix.table.columnWidths", "{broken");
		render(<Harness />);
		expect(screen.getByTestId("repo-width")).toHaveTextContent("185");

		fireEvent.mouseDown(screen.getByRole("button", { name: "start" }));
		globalThis.window.dispatchEvent(
			new MouseEvent("mousemove", { clientX: -10_000 }),
		);
		await waitFor(() => {
			expect(screen.getByTestId("repo-width")).toHaveTextContent("120");
		});
	});

	it("clamps too-small stored widths from localStorage", () => {
		localStorage.setItem(
			"corvix.table.columnWidths",
			JSON.stringify({ repository: 10 }),
		);

		render(<Harness />);

		expect(screen.getByTestId("repo-width")).toHaveTextContent("120");
	});

	it("normalizes partially invalid stored widths", () => {
		localStorage.setItem(
			"corvix.table.columnWidths",
			JSON.stringify({
				repository: "nope",
				subject_type: 20,
				reason: 210,
				score: null,
				updated_at: 90,
			}),
		);

		render(<Harness />);

		expect(screen.getByTestId("repo-width")).toHaveTextContent("185");
	});

	it("removes resize listeners on unmount", async () => {
		const user = userEvent.setup();
		const { unmount } = render(<Harness />);

		await user.pointer([
			{
				target: screen.getByRole("button", { name: "start" }),
				keys: "[MouseLeft>]",
			},
		]);
		unmount();

		expect(document.body.classList.contains("col-resizing")).toBe(false);
	});

	it("ignores mousemove events before resizing starts", () => {
		render(<Harness />);

		globalThis.window.dispatchEvent(
			new MouseEvent("mousemove", { clientX: 999 }),
		);

		expect(screen.getByTestId("repo-width")).toHaveTextContent("185");
	});

	it("does not change width when the pointer does not move", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		await user.pointer([
			{
				target: screen.getByRole("button", { name: "start" }),
				keys: "[MouseLeft>]",
			},
		]);
		globalThis.window.dispatchEvent(
			new MouseEvent("mousemove", { clientX: 100 }),
		);

		await waitFor(() => {
			expect(screen.getByTestId("repo-width")).toHaveTextContent("185");
		});
	});

	it("swallows localStorage write errors while resizing", async () => {
		const user = userEvent.setup();
		vi.spyOn(globalThis.window.localStorage, "setItem").mockImplementation(
			() => {
				throw new Error("quota");
			},
		);

		render(<Harness />);

		await user.pointer([
			{
				target: screen.getByRole("button", { name: "start" }),
				keys: "[MouseLeft>]",
			},
		]);
		expect(() => {
			globalThis.window.dispatchEvent(
				new MouseEvent("mousemove", { clientX: 150 }),
			);
		}).not.toThrow();

		await waitFor(() => {
			expect(screen.getByTestId("repo-width")).toHaveTextContent("235");
		});
	});

	it("persists widths under the versioned storage key", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		await user.pointer([
			{
				target: screen.getByRole("button", { name: "start" }),
				keys: "[MouseLeft>]",
			},
		]);
		globalThis.window.dispatchEvent(
			new MouseEvent("mousemove", { clientX: 150 }),
		);

		await waitFor(() => {
			const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
			expect(stored.repository).toBe(235);
		});
	});

	it("migrates widths from the legacy unversioned key and removes it", async () => {
		localStorage.setItem(LEGACY_KEY, JSON.stringify({ repository: 240 }));

		render(<Harness />);

		expect(screen.getByTestId("repo-width")).toHaveTextContent("240");
		await waitFor(() => {
			expect(localStorage.getItem(LEGACY_KEY)).toBeNull();
		});
		const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
		expect(stored.repository).toBe(240);
	});

	it("prefers the current versioned key over the legacy key", () => {
		localStorage.setItem(LEGACY_KEY, JSON.stringify({ repository: 240 }));
		localStorage.setItem(STORAGE_KEY, JSON.stringify({ repository: 200 }));

		render(<Harness />);

		expect(screen.getByTestId("repo-width")).toHaveTextContent("200");
	});

	it("removes stale older-version keys on mount", async () => {
		localStorage.setItem(LEGACY_KEY, JSON.stringify({ repository: 200 }));
		localStorage.setItem(
			"corvix.table.columnWidths.v1",
			JSON.stringify({ repository: 210 }),
		);
		localStorage.setItem("corvix.unrelated.key", "keep-me");

		render(<Harness />);

		await waitFor(() => {
			expect(localStorage.getItem(LEGACY_KEY)).toBeNull();
			expect(localStorage.getItem("corvix.table.columnWidths.v1")).toBeNull();
		});
		expect(localStorage.getItem("corvix.unrelated.key")).toBe("keep-me");
	});

	it("resets every column width to its default", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		await user.pointer([
			{
				target: screen.getByRole("button", { name: "start" }),
				keys: "[MouseLeft>]",
			},
		]);
		globalThis.window.dispatchEvent(
			new MouseEvent("mousemove", { clientX: 150 }),
		);
		await waitFor(() => {
			expect(screen.getByTestId("repo-width")).toHaveTextContent("235");
		});
		globalThis.window.dispatchEvent(new MouseEvent("mouseup"));

		await user.click(screen.getByRole("button", { name: "reset all" }));

		expect(screen.getByTestId("repo-width")).toHaveTextContent("185");
		expect(screen.getByTestId("score-width")).toHaveTextContent("75");
		await waitFor(() => {
			const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
			expect(stored.repository).toBe(185);
		});
	});
});
