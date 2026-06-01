import { fireEvent, render, screen, waitFor } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { useColumnResize } from "./useColumnResize";

const STORAGE_KEY = "corvix.table.columnWidths.v2";
const LEGACY_KEY = "corvix.table.columnWidths";

type User = ReturnType<typeof userEvent.setup>;

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

function beginResize(user: User) {
	return user.pointer([
		{
			target: screen.getByRole("button", { name: "start" }),
			keys: "[MouseLeft>]",
		},
	]);
}

function moveMouse(clientX: number) {
	globalThis.window.dispatchEvent(new MouseEvent("mousemove", { clientX }));
}

function releaseMouse() {
	globalThis.window.dispatchEvent(new MouseEvent("mouseup"));
}

function repoWidth() {
	return screen.getByTestId("repo-width");
}

function storedWidths() {
	return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
}

describe("useColumnResize", () => {
	it("resizes and resets column width", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		expect(repoWidth()).toHaveTextContent("185");
		await beginResize(user);
		moveMouse(150);
		await waitFor(() => {
			expect(repoWidth()).toHaveTextContent("235");
		});

		releaseMouse();
		await user.click(screen.getByRole("button", { name: "reset" }));
		expect(repoWidth()).toHaveTextContent("185");
	});

	it("falls back from invalid storage and clamps at minimum width", async () => {
		localStorage.setItem(LEGACY_KEY, "{broken");
		render(<Harness />);
		expect(repoWidth()).toHaveTextContent("185");

		fireEvent.mouseDown(screen.getByRole("button", { name: "start" }));
		moveMouse(-10_000);
		await waitFor(() => {
			expect(repoWidth()).toHaveTextContent("120");
		});
	});

	it("clamps too-small stored widths from localStorage", () => {
		localStorage.setItem(LEGACY_KEY, JSON.stringify({ repository: 10 }));

		render(<Harness />);

		expect(repoWidth()).toHaveTextContent("120");
	});

	it("normalizes partially invalid stored widths", () => {
		localStorage.setItem(
			LEGACY_KEY,
			JSON.stringify({
				repository: "nope",
				subject_type: 20,
				reason: 210,
				score: null,
				updated_at: 90,
			}),
		);

		render(<Harness />);

		expect(repoWidth()).toHaveTextContent("185");
	});

	it("removes resize listeners on unmount", async () => {
		const user = userEvent.setup();
		const { unmount } = render(<Harness />);

		await beginResize(user);
		unmount();

		expect(document.body.classList.contains("col-resizing")).toBe(false);
	});

	it("ignores mousemove events before resizing starts", () => {
		render(<Harness />);

		moveMouse(999);

		expect(repoWidth()).toHaveTextContent("185");
	});

	it("does not change width when the pointer does not move", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		await beginResize(user);
		moveMouse(100);

		await waitFor(() => {
			expect(repoWidth()).toHaveTextContent("185");
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

		await beginResize(user);
		expect(() => moveMouse(150)).not.toThrow();

		await waitFor(() => {
			expect(repoWidth()).toHaveTextContent("235");
		});
	});

	it("falls back to defaults when localStorage access throws on init", () => {
		vi.spyOn(globalThis.window.localStorage, "getItem").mockImplementation(
			() => {
				throw new Error("SecurityError");
			},
		);

		render(<Harness />);

		expect(repoWidth()).toHaveTextContent("185");
	});

	it("persists widths under the versioned storage key", async () => {
		const user = userEvent.setup();
		render(<Harness />);

		await beginResize(user);
		moveMouse(150);

		await waitFor(() => {
			expect(storedWidths().repository).toBe(235);
		});
	});

	it("migrates widths from the legacy unversioned key and removes it", async () => {
		localStorage.setItem(LEGACY_KEY, JSON.stringify({ repository: 240 }));

		render(<Harness />);

		expect(repoWidth()).toHaveTextContent("240");
		await waitFor(() => {
			expect(localStorage.getItem(LEGACY_KEY)).toBeNull();
		});
		expect(storedWidths().repository).toBe(240);
	});

	it("prefers the current versioned key over the legacy key", () => {
		localStorage.setItem(LEGACY_KEY, JSON.stringify({ repository: 240 }));
		localStorage.setItem(STORAGE_KEY, JSON.stringify({ repository: 200 }));

		render(<Harness />);

		expect(repoWidth()).toHaveTextContent("200");
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

		await beginResize(user);
		moveMouse(150);
		await waitFor(() => {
			expect(repoWidth()).toHaveTextContent("235");
		});
		releaseMouse();

		await user.click(screen.getByRole("button", { name: "reset all" }));

		expect(repoWidth()).toHaveTextContent("185");
		expect(screen.getByTestId("score-width")).toHaveTextContent("75");
		await waitFor(() => {
			expect(storedWidths().repository).toBe(185);
		});
	});
});
