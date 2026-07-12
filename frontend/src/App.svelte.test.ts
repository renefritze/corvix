import { render, screen, waitFor, within } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { makeItem, makeSnapshot } from "./test/fixtures";
import { type FetchInput, requestUrl } from "./test/http";
import App from "./App.svelte";
import type { SnapshotPayload } from "./types";

// A 3-item dataset across two repository groups with an unread mix and more than
// one dashboard so the dashboard selector renders. Mirrors the legacy
// app.test.tsx dataset while driving the Svelte 5 app end to end.
function overviewSnapshot(): SnapshotPayload {
	return makeSnapshot({
		name: "overview",
		sort_by: "score",
		descending: true,
		groups: [
			{
				name: "org/repo-a",
				items: [
					makeItem({
						thread_id: "1",
						subject_title: "One",
						repository: "org/repo-a",
						reason: "mention",
						unread: true,
						score: 90,
					}),
					makeItem({
						thread_id: "2",
						subject_title: "Two",
						repository: "org/repo-a",
						reason: "subscribed",
						unread: false,
						score: 70,
					}),
				],
			},
			{
				name: "org/repo-b",
				items: [
					makeItem({
						thread_id: "3",
						subject_title: "Three",
						repository: "org/repo-b",
						reason: "review_requested",
						unread: true,
						score: 50,
					}),
				],
			},
		],
		total_items: 3,
		summary: {
			unread_items: 2,
			read_items: 1,
			group_count: 2,
			repository_count: 2,
			reason_count: 3,
		},
		dashboard_names: ["overview", "triage"],
	});
}

function triageSnapshot(): SnapshotPayload {
	return makeSnapshot({
		name: "triage",
		groups: [
			{
				name: "org/repo-b",
				items: [
					makeItem({
						thread_id: "9",
						subject_title: "Triaged",
						repository: "org/repo-b",
						reason: "mention",
					}),
				],
			},
		],
		total_items: 1,
		summary: {
			unread_items: 1,
			read_items: 0,
			group_count: 1,
			repository_count: 1,
			reason_count: 1,
		},
		dashboard_names: ["overview", "triage"],
	});
}

/** Installs a fetch mock that serves the overview/triage snapshots and OK-s any
 * side-effect POST (dismiss / mark-read / rule-snippets). */
function installFetch(
	getSnapshot: (url: string) => SnapshotPayload = () => overviewSnapshot(),
) {
	const mock = vi.fn((input: FetchInput) => {
		const url = requestUrl(input);
		if (url.includes("/api/v1/snapshot")) {
			return Promise.resolve(
				mockOk(async () => getSnapshot(url)),
			);
		}
		return Promise.resolve(mockOk(async () => ({})));
	});
	globalThis.fetch = mock as unknown as typeof fetch;
	return mock;
}

function mockOk(json: () => Promise<unknown>): Response {
	return { ok: true, json } as unknown as Response;
}

function rowCount(): number {
	return document.querySelectorAll("tr[data-thread-id]").length;
}

function groupHeaderCount(): number {
	return document.querySelectorAll('[data-testid="group-header-row"]').length;
}

async function renderLoaded() {
	render(App);
	await screen.findByText("Corvix");
	await waitFor(() => expect(rowCount()).toBeGreaterThan(0));
}

beforeEach(() => {
	history.pushState({}, "", "/");
	// jsdom lacks the Web Animations API that Svelte's `fly` transition (used by
	// UndoToast) relies on; provide a no-op that resolves immediately so the
	// transition completes instead of throwing inside the error boundary.
	if (typeof Element.prototype.animate !== "function") {
		Element.prototype.animate = function () {
			const anim: Record<string, unknown> = {
				onfinish: null,
				oncancel: null,
				cancel() {},
				play() {},
				pause() {},
				finish() {},
				finished: Promise.resolve(),
				currentTime: 0,
				playState: "finished",
				addEventListener(type: string, cb: () => void) {
					if (type === "finish") anim._finish = cb;
				},
				removeEventListener() {},
			};
			// Svelte's WAAPI-based transitions remove the node once the animation
			// finishes; fire that callback so outro transitions actually complete.
			setTimeout(() => {
				(anim.onfinish as (() => void) | null)?.();
				(anim._finish as (() => void) | undefined)?.();
			}, 0);
			return anim as unknown as Animation;
		};
	}
});

afterEach(() => {
	history.pushState({}, "", "/");
	vi.restoreAllMocks();
});

describe("App integration", () => {
	it("renders the app shell and brand", async () => {
		installFetch();
		render(App);
		await screen.findByText("Corvix");
		expect(document.querySelector('[data-testid="app-shell"]')).not.toBeNull();
		expect(screen.getByTestId("app-name")).toHaveTextContent("Corvix");
	});

	it("loads the snapshot into the notifications table", async () => {
		installFetch();
		await renderLoaded();
		const table = await screen.findByRole("table", { name: "Notifications" });
		expect(table).toBeInTheDocument();
		await waitFor(() => expect(rowCount()).toBe(3));
		expect(groupHeaderCount()).toBe(2);
		expect(screen.getByRole("link", { name: "One" })).toBeInTheDocument();
		expect(screen.getByRole("link", { name: "Three" })).toBeInTheDocument();
	});

	it("switches dashboards and refetches with a ?dashboard= query", async () => {
		const mock = installFetch((url) =>
			url.includes("dashboard=triage") ? triageSnapshot() : overviewSnapshot(),
		);
		await renderLoaded();
		await screen.findByRole("link", { name: "One" });

		const user = userEvent.setup();
		await user.selectOptions(
			screen.getByLabelText("Select dashboard"),
			"triage",
		);

		await waitFor(() =>
			expect(screen.getByRole("link", { name: "Triaged" })).toBeInTheDocument(),
		);
		expect(
			mock.mock.calls.some((call) =>
				requestUrl(call[0] as FetchInput).includes("dashboard=triage"),
			),
		).toBe(true);
		expect(globalThis.location.pathname).toBe("/dashboards/triage");
	});

	it("filters by reason and restores when the chip is removed", async () => {
		installFetch();
		await renderLoaded();
		const user = userEvent.setup();

		await user.click(screen.getByLabelText("Reason filter"));
		await user.click(screen.getByRole("button", { name: "subscribed" }));

		await waitFor(() => expect(rowCount()).toBe(1));
		expect(screen.getByRole("link", { name: "Two" })).toBeInTheDocument();
		expect(screen.queryByRole("link", { name: "One" })).not.toBeInTheDocument();

		await user.click(
			screen.getByRole("button", { name: "Remove subscribed reason filter" }),
		);
		await waitFor(() => expect(rowCount()).toBe(3));
	});

	it("dismisses a row, shows the undo toast, and restores on undo", async () => {
		installFetch();
		await renderLoaded();
		const user = userEvent.setup();

		await user.click(screen.getByLabelText("Dismiss One"));

		await waitFor(() =>
			expect(screen.queryByRole("link", { name: "One" })).not.toBeInTheDocument(),
		);
		const toast = await screen.findByTestId("undo-toast");
		expect(toast).toHaveTextContent("1 notification dismissing");

		await user.click(within(toast).getByRole("button", { name: "Undo" }));
		await waitFor(() =>
			expect(screen.getByRole("link", { name: "One" })).toBeInTheDocument(),
		);
	});

	it("shows the all-clear empty state when the dashboard is empty", async () => {
		installFetch(() =>
			makeSnapshot({
				groups: [],
				total_items: 0,
				summary: {
					unread_items: 0,
					read_items: 0,
					group_count: 0,
					repository_count: 0,
					reason_count: 0,
				},
				dashboard_names: ["overview"],
			}),
		);
		render(App);
		await screen.findByText("Corvix");
		expect(await screen.findByText("All clear")).toBeInTheDocument();
	});

	it("shows the failed-to-load error state when the snapshot fetch fails", async () => {
		globalThis.fetch = vi.fn((input: FetchInput) => {
			const url = requestUrl(input);
			if (url.includes("/api/v1/snapshot")) {
				return Promise.resolve({
					ok: false,
					status: 500,
					json: async () => ({}),
				} as unknown as Response);
			}
			return Promise.resolve(mockOk(async () => ({})));
		}) as unknown as typeof fetch;

		render(App);
		await screen.findByText("Corvix");
		expect(await screen.findByText("Failed to load")).toBeInTheDocument();
		expect(
			screen.getByText("Snapshot fetch failed: 500"),
		).toBeInTheDocument();
	});

	it("toggles the document theme via the theme toggle button", async () => {
		installFetch();
		await renderLoaded();
		const user = userEvent.setup();

		const before = document.documentElement.dataset.theme;
		await user.click(
			screen.getByRole("button", { name: /Switch to (light|dark) theme/ }),
		);
		await waitFor(() =>
			expect(document.documentElement.dataset.theme).not.toBe(before),
		);
	});

	it("opens the command palette from the toolbar button and closes on Escape", async () => {
		installFetch();
		await renderLoaded();
		const user = userEvent.setup();

		await user.click(screen.getByLabelText("Open command palette"));
		const dialog = await screen.findByRole("dialog", {
			name: "Command palette",
		});
		expect(dialog).toBeInTheDocument();
		expect(
			within(dialog).getByText("Refresh notifications"),
		).toBeInTheDocument();

		await user.keyboard("{Escape}");
		await waitFor(() =>
			expect(
				screen.queryByRole("dialog", { name: "Command palette" }),
			).not.toBeInTheDocument(),
		);
	});

	it("opens the command palette with Ctrl+K", async () => {
		installFetch();
		await renderLoaded();
		const user = userEvent.setup();

		await user.keyboard("{Control>}k{/Control}");
		expect(
			await screen.findByRole("dialog", { name: "Command palette" }),
		).toBeInTheDocument();
	});

	it("refetches the snapshot when pressing 'r'", async () => {
		const mock = installFetch();
		await renderLoaded();
		const snapshotCalls = () =>
			mock.mock.calls.filter((call) =>
				requestUrl(call[0] as FetchInput).includes("/api/v1/snapshot"),
			).length;
		const before = snapshotCalls();

		const user = userEvent.setup();
		await user.keyboard("r");

		await waitFor(() => expect(snapshotCalls()).toBeGreaterThan(before));
	});

	it("toggles the keyboard shortcuts panel with '?'", async () => {
		installFetch();
		await renderLoaded();
		const user = userEvent.setup();

		await user.keyboard("?");
		expect(
			await screen.findByRole("dialog", { name: "Keyboard shortcuts" }),
		).toBeInTheDocument();
		expect(document.querySelector("#shortcuts-panel")).not.toBeNull();

		await user.keyboard("?");
		await waitFor(() =>
			expect(
				screen.queryByRole("dialog", { name: "Keyboard shortcuts" }),
			).not.toBeInTheDocument(),
		);
	});

	it("renders the in-SPA 404 view for an unknown route", async () => {
		installFetch();
		history.pushState({}, "", "/nope/x");
		render(App);
		expect(await screen.findByText("Page not found")).toBeInTheDocument();
		expect(screen.queryByLabelText("Select dashboard")).not.toBeInTheDocument();
	});

	it("marks a row read on title click and refetches the snapshot", async () => {
		const mock = vi.fn((input: FetchInput, init?: RequestInit) => {
			const url = requestUrl(input);
			if (init?.method === "POST") {
				return Promise.resolve(mockOk(async () => ({})));
			}
			if (url.includes("/api/v1/snapshot")) {
				return Promise.resolve(mockOk(async () => overviewSnapshot()));
			}
			return Promise.resolve(mockOk(async () => ({})));
		});
		globalThis.fetch = mock as unknown as typeof fetch;
		await renderLoaded();
		const user = userEvent.setup();

		await user.click(screen.getByRole("link", { name: "One" }));

		await waitFor(() =>
			expect(
				mock.mock.calls.some((call) =>
					requestUrl(call[0] as FetchInput).includes("/1/mark-read"),
				),
			).toBe(true),
		);
	});

	it("surfaces a toast when mark-read fails and dismisses it", async () => {
		globalThis.fetch = vi.fn((input: FetchInput, init?: RequestInit) => {
			const url = requestUrl(input);
			if (init?.method === "POST") {
				return Promise.resolve({
					ok: false,
					status: 500,
					json: async () => ({}),
				} as unknown as Response);
			}
			if (url.includes("/api/v1/snapshot")) {
				return Promise.resolve(mockOk(async () => overviewSnapshot()));
			}
			return Promise.resolve(mockOk(async () => ({})));
		}) as unknown as typeof fetch;
		await renderLoaded();
		const user = userEvent.setup();

		await user.click(screen.getByRole("link", { name: "One" }));
		const alert = await screen.findByRole("alert");
		expect(alert).toHaveTextContent("Mark read failed: 500");

		await user.click(screen.getByRole("button", { name: "Dismiss error" }));
		await waitFor(() =>
			expect(screen.queryByRole("alert")).not.toBeInTheDocument(),
		);
	});

	it("marks a whole group read from the group header action", async () => {
		const mock = vi.fn((input: FetchInput, init?: RequestInit) => {
			const url = requestUrl(input);
			if (init?.method === "POST") {
				return Promise.resolve(mockOk(async () => ({})));
			}
			if (url.includes("/api/v1/snapshot")) {
				return Promise.resolve(mockOk(async () => overviewSnapshot()));
			}
			return Promise.resolve(mockOk(async () => ({})));
		});
		globalThis.fetch = mock as unknown as typeof fetch;
		await renderLoaded();
		const user = userEvent.setup();

		await user.click(
			screen.getByRole("button", {
				name: /Mark all visible unread notifications in org\/repo-a as read/,
			}),
		);

		await waitFor(() =>
			expect(
				mock.mock.calls.some((call) =>
					requestUrl(call[0] as FetchInput).includes("/1/mark-read"),
				),
			).toBe(true),
		);
	});

	it("filters via free-text search and clears it", async () => {
		installFetch();
		await renderLoaded();
		const user = userEvent.setup();

		await user.type(screen.getByLabelText("Search notifications"), "Three");
		await waitFor(() => expect(rowCount()).toBe(1));
		expect(screen.getByRole("link", { name: "Three" })).toBeInTheDocument();

		await user.clear(screen.getByLabelText("Search notifications"));
		await waitFor(() => expect(rowCount()).toBe(3));
	});

	it("filters by repository and unread state via the select controls", async () => {
		installFetch();
		await renderLoaded();
		const user = userEvent.setup();

		await user.selectOptions(
			screen.getByLabelText("Repository filter"),
			"org/repo-b",
		);
		await waitFor(() => expect(rowCount()).toBe(1));
		expect(screen.getByRole("link", { name: "Three" })).toBeInTheDocument();

		await user.selectOptions(
			screen.getByLabelText("Repository filter"),
			"All repositories",
		);
		await waitFor(() => expect(rowCount()).toBe(3));

		await user.selectOptions(
			screen.getByLabelText("Unread state filter"),
			"read",
		);
		await waitFor(() => expect(rowCount()).toBe(1));
		expect(screen.getByRole("link", { name: "Two" })).toBeInTheDocument();
	});

	it("clears all active filters from the Clear button", async () => {
		installFetch();
		await renderLoaded();
		const user = userEvent.setup();

		await user.type(screen.getByLabelText("Search notifications"), "One");
		await waitFor(() => expect(rowCount()).toBe(1));
		await user.click(screen.getByRole("button", { name: "Clear" }));
		await waitFor(() => expect(rowCount()).toBe(3));
	});

	it("runs a command from the command palette and filters the command list", async () => {
		installFetch();
		await renderLoaded();
		const user = userEvent.setup();

		await user.click(screen.getByLabelText("Open command palette"));
		const dialog = await screen.findByRole("dialog", {
			name: "Command palette",
		});

		// Fuzzy-filter the command list.
		await user.type(
			within(dialog).getByLabelText("Command palette search"),
			"refresh",
		);
		await waitFor(() =>
			expect(
				within(dialog).getByText("Refresh notifications"),
			).toBeInTheDocument(),
		);

		const before = document.documentElement.dataset.theme;
		await user.clear(within(dialog).getByLabelText("Command palette search"));
		await user.click(
			within(dialog).getByText("Toggle light / dark theme"),
		);

		// Command runs (theme flips) and the palette closes.
		await waitFor(() =>
			expect(document.documentElement.dataset.theme).not.toBe(before),
		);
		expect(
			screen.queryByRole("dialog", { name: "Command palette" }),
		).not.toBeInTheDocument();
	});

	it("sorts the table when a column header is clicked", async () => {
		installFetch();
		await renderLoaded();
		const user = userEvent.setup();

		const scoreHeader = screen
			.getByRole("columnheader", { name: /Score/ })
			.querySelector("button.nt-th-button") as HTMLButtonElement;
		await user.click(scoreHeader);

		await waitFor(() =>
			expect(globalThis.location.search).toContain("sort"),
		);
	});

	it("focuses a row with 'j' then dismisses it with 'd'", async () => {
		installFetch();
		await renderLoaded();
		const user = userEvent.setup();

		await user.keyboard("j");
		await waitFor(() =>
			expect(
				document.activeElement?.matches("tr[data-thread-id]"),
			).toBe(true),
		);

		await user.keyboard("d");
		const toast = await screen.findByTestId("undo-toast");
		expect(toast).toHaveTextContent("1 notification dismissing");
		await user.click(within(toast).getByRole("button", { name: "Undo" }));
	});

	it("focuses filters with 'f' and the search box with '/'", async () => {
		installFetch();
		await renderLoaded();
		const user = userEvent.setup();

		await user.keyboard("f");
		await waitFor(() =>
			expect(
				document.activeElement?.hasAttribute("data-filter-focus"),
			).toBe(true),
		);
		// Blur the select so the next shortcut is not swallowed as typing.
		(document.activeElement as HTMLElement).blur();

		await user.keyboard("/");
		await waitFor(() =>
			expect(
				document.activeElement?.hasAttribute("data-search-input"),
			).toBe(true),
		);
	});

	it("opens the ignore-rule dialog from the row context menu", async () => {
		const snippets = {
			dashboard_name: "overview",
			dashboard_ignore_rule_snippet: "- repository_in: [org/repo-a]",
			global_exclude_rule_snippet: "- name: ignore-rule",
			dashboard_ignore_rule_with_context_snippet: null,
			global_exclude_rule_with_context_snippet: null,
			has_context: false,
		};
		globalThis.fetch = vi.fn((input: FetchInput) => {
			const url = requestUrl(input);
			if (url.includes("/rule-snippets")) {
				return Promise.resolve(mockOk(async () => snippets));
			}
			if (url.includes("/api/v1/snapshot")) {
				return Promise.resolve(mockOk(async () => overviewSnapshot()));
			}
			return Promise.resolve(mockOk(async () => ({})));
		}) as unknown as typeof fetch;
		await renderLoaded();
		const user = userEvent.setup();

		const row = screen.getByRole("link", { name: "One" }).closest("tr");
		row?.dispatchEvent(
			new MouseEvent("contextmenu", { bubbles: true, clientX: 5, clientY: 6 }),
		);
		await user.click(
			await screen.findByRole("menuitem", { name: "Create ignore rule..." }),
		);

		expect(
			await screen.findByRole("heading", { name: "Create ignore rule" }),
		).toBeInTheDocument();
		await waitFor(() =>
			expect(
				screen.getByRole("heading", { name: "Dashboard ignore rule" }),
			).toBeInTheDocument(),
		);
	});

	it("collapses and expands a repository group from its header", async () => {
		installFetch();
		await renderLoaded();
		const user = userEvent.setup();

		await user.click(
			screen.getByRole("button", { name: "Collapse org/repo-a" }),
		);
		await waitFor(() => expect(rowCount()).toBe(1));
		expect(screen.queryByRole("link", { name: "One" })).not.toBeInTheDocument();

		await user.click(
			screen.getByRole("button", { name: "Expand org/repo-a" }),
		);
		await waitFor(() => expect(rowCount()).toBe(3));
	});

	it("shows the poller warning banner when the poller reports an error", async () => {
		installFetch(() =>
			makeSnapshot({
				groups: [{ name: "org/repo-a", items: [makeItem()] }],
				total_items: 1,
				dashboard_names: ["overview"],
				poller: {
					status: "error",
					last_poll_time: "2026-04-09T10:00:00Z",
					last_error: "Poller exploded",
					last_error_time: "2026-04-09T10:00:00Z",
					stale: false,
					account_errors: [],
				},
			}),
		);
		await renderLoaded();
		await waitFor(() =>
			expect(screen.getByText(/Poller exploded/)).toBeInTheDocument(),
		);
	});

	it("renders the top-level error boundary when the snapshot is malformed", async () => {
		// A snapshot whose `groups` is not an array makes the `allItems` derived
		// throw during render; the error propagates to App's <svelte:boundary>.
		globalThis.fetch = vi.fn((input: FetchInput) => {
			const url = requestUrl(input);
			if (url.includes("/api/v1/snapshot")) {
				return Promise.resolve(
					mockOk(async () =>
						makeSnapshot({
							groups: null as unknown as SnapshotPayload["groups"],
							dashboard_names: ["overview"],
						}),
					),
				);
			}
			return Promise.resolve(mockOk(async () => ({})));
		}) as unknown as typeof fetch;

		render(App);
		expect(
			await screen.findByText("Something went wrong"),
		).toBeInTheDocument();
	});
});
