import {
	fireEvent,
	render,
	screen,
	waitFor,
	within,
} from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { App } from "./app";
import { makeItem, makeSnapshot } from "./test/fixtures";

type FetchInput = string | URL | Request;

function setPath(path: string): void {
	globalThis.history.pushState({}, "", path);
}

function requestUrl(input: FetchInput): string {
	if (typeof input === "string") {
		return input;
	}
	if (input instanceof URL) {
		return input.toString();
	}
	return input.url;
}

describe("App", () => {
	it("loads snapshot, filters items, and switches dashboards", async () => {
		setPath("/");
		const overview = makeSnapshot({
			name: "overview",
			groups: [
				{
					name: "group-a",
					items: [
						makeItem({
							thread_id: "1",
							reason: "mention",
							subject_title: "One",
						}),
						makeItem({
							thread_id: "2",
							reason: "subscribed",
							subject_title: "Two",
						}),
					],
				},
			],
			total_items: 2,
			summary: {
				unread_items: 2,
				read_items: 0,
				group_count: 1,
				repository_count: 1,
				reason_count: 2,
			},
			dashboard_names: ["overview", "triage"],
		});

		const triage = makeSnapshot({
			name: "triage",
			groups: [
				{
					name: "group-b",
					items: [makeItem({ thread_id: "3", subject_title: "Three" })],
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

		const fetchMock = vi
			.spyOn(globalThis, "fetch")
			.mockImplementation(async (input: FetchInput, init?: RequestInit) => {
				if (init?.method === "POST") {
					return { ok: true } as Response;
				}
				const url = requestUrl(input);
				const payload = url.includes("dashboard=triage") ? triage : overview;
				return {
					ok: true,
					json: async () => payload,
				} as Response;
			});

		render(<App />);

		await waitFor(() => {
			expect(screen.getByRole("link", { name: "One" })).toBeInTheDocument();
		});
		expect(fetchMock).toHaveBeenCalledWith("/api/snapshot");

		const user = userEvent.setup();
		await user.click(screen.getByLabelText("Reason filter"));
		await user.click(screen.getByRole("button", { name: "subscribed" }));
		expect(screen.getByRole("link", { name: "Two" })).toBeInTheDocument();
		expect(screen.queryByRole("link", { name: "One" })).not.toBeInTheDocument();
		await user.click(
			screen.getByRole("button", {
				name: "Remove subscribed reason filter",
			}),
		);

		await user.selectOptions(
			screen.getByLabelText("Select dashboard"),
			"triage",
		);
		await waitFor(() => {
			expect(screen.getByRole("link", { name: "Three" })).toBeInTheDocument();
		});
		expect(globalThis.location.pathname).toBe("/dashboards/triage");
	});

	it("lets users clear missing reason filters after switching dashboards", async () => {
		setPath("/");
		const overview = makeSnapshot({
			name: "overview",
			groups: [
				{
					name: "group-a",
					items: [
						makeItem({
							thread_id: "1",
							reason: "mention",
							subject_title: "One",
						}),
						makeItem({
							thread_id: "2",
							reason: "subscribed",
							subject_title: "Two",
						}),
					],
				},
			],
			total_items: 2,
			dashboard_names: ["overview", "triage"],
		});

		const triage = makeSnapshot({
			name: "triage",
			groups: [
				{
					name: "group-b",
					items: [
						makeItem({
							thread_id: "3",
							reason: "review_requested",
							subject_title: "Three",
						}),
					],
				},
			],
			total_items: 1,
			dashboard_names: ["overview", "triage"],
		});

		vi.spyOn(globalThis, "fetch").mockImplementation(
			async (input: FetchInput, init?: RequestInit) => {
				if (init?.method === "POST") {
					return { ok: true } as Response;
				}
				const url = requestUrl(input);
				const payload = url.includes("dashboard=triage") ? triage : overview;
				return {
					ok: true,
					json: async () => payload,
				} as Response;
			},
		);

		render(<App />);

		await waitFor(() => {
			expect(screen.getByRole("link", { name: "One" })).toBeInTheDocument();
		});

		const user = userEvent.setup();
		await user.click(screen.getByLabelText("Reason filter"));
		await user.click(screen.getByRole("button", { name: "subscribed" }));
		expect(screen.getByRole("link", { name: "Two" })).toBeInTheDocument();
		expect(screen.queryByRole("link", { name: "One" })).not.toBeInTheDocument();

		await user.selectOptions(
			screen.getByLabelText("Select dashboard"),
			"triage",
		);

		await waitFor(() => {
			expect(
				screen.getByText("No notifications match the current filters."),
			).toBeInTheDocument();
		});

		await user.click(screen.getByLabelText("Reason filter"));
		expect(
			screen.getByRole("button", {
				name: "subscribed (no matching notifications)",
			}),
		).toBeInTheDocument();

		await user.click(
			screen.getByRole("button", {
				name: "subscribed (no matching notifications)",
			}),
		);

		await waitFor(() => {
			expect(screen.getByRole("link", { name: "Three" })).toBeInTheDocument();
		});
	});

	it("shows error state when snapshot fetch fails", async () => {
		setPath("/");
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: false,
			status: 500,
		});

		render(<App />);

		await waitFor(() => {
			expect(screen.getByText("Failed to load")).toBeInTheDocument();
		});
		expect(screen.getByText("Snapshot fetch failed: 500")).toBeInTheDocument();
	});

	it("shows all-clear empty state when dashboard has no items", async () => {
		setPath("/");
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () =>
				makeSnapshot({
					groups: [{ name: "empty", items: [] }],
					total_items: 0,
					summary: {
						unread_items: 0,
						read_items: 0,
						group_count: 1,
						repository_count: 0,
						reason_count: 0,
					},
				}),
		});

		render(<App />);

		await waitFor(() => {
			expect(screen.getByText("All clear")).toBeInTheDocument();
		});
	});

	it("shows loading skeleton before first snapshot resolves", async () => {
		setPath("/");
		let resolveFetch: ((value: Response) => void) | null = null;
		vi.spyOn(globalThis, "fetch").mockImplementation(
			() =>
				new Promise((resolve) => {
					resolveFetch = resolve;
				}),
		);

		render(<App />);
		expect(
			screen.getByRole("table", { name: "Loading notifications" }),
		).toBeInTheDocument();

		resolveFetch?.({
			ok: true,
			json: async () => makeSnapshot(),
		});

		await waitFor(() => {
			expect(
				screen.getByRole("table", { name: "Notifications" }),
			).toBeInTheDocument();
		});
	});

	it("shows toast when mark-read fails from row link", async () => {
		setPath("/");
		const snapshot = makeSnapshot({
			groups: [
				{
					name: "group-a",
					items: [makeItem({ thread_id: "item-1", subject_title: "Open me" })],
				},
			],
			total_items: 1,
			dashboard_names: ["overview"],
		});
		vi.spyOn(globalThis, "fetch").mockImplementation(
			async (_input: FetchInput, init?: RequestInit) => {
				if (init?.method === "POST") {
					return { ok: false, status: 500 } as Response;
				}
				return {
					ok: true,
					json: async () => snapshot,
				} as Response;
			},
		);

		const user = userEvent.setup();
		render(<App />);

		await waitFor(() => {
			expect(screen.getByRole("link", { name: "Open me" })).toBeInTheDocument();
		});
		await user.click(screen.getByRole("link", { name: "Open me" }));

		await waitFor(() => {
			expect(screen.getByRole("alert")).toHaveTextContent(
				"Mark read failed: 500",
			);
		});

		await user.click(screen.getByRole("button", { name: "✕" }));
		expect(screen.queryByRole("alert")).not.toBeInTheDocument();
	});

	it("falls back to default dashboard when URL dashboard is unknown", async () => {
		setPath("/dashboards/unknown");
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () =>
				makeSnapshot({ dashboard_names: ["overview", "triage"] }),
		});

		render(<App />);

		await waitFor(() => {
			expect(screen.getByLabelText("Select dashboard")).toHaveValue("overview");
		});
		await waitFor(() => {
			expect(globalThis.location.pathname).toBe("/dashboards/overview");
		});
	});

	it("locks unread filter to unread-only when dashboard excludes read", async () => {
		setPath("/");
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () =>
				makeSnapshot({
					include_read: false,
					groups: [
						{
							name: "group-a",
							items: [
								makeItem({
									thread_id: "1",
									subject_title: "Unread",
									unread: true,
								}),
								makeItem({
									thread_id: "2",
									subject_title: "Read",
									unread: false,
								}),
							],
						},
					],
					summary: {
						unread_items: 1,
						read_items: 1,
						group_count: 1,
						repository_count: 1,
						reason_count: 1,
					},
				}),
		});

		render(<App />);

		await waitFor(() => {
			expect(screen.getByRole("link", { name: "Unread" })).toBeInTheDocument();
		});
		expect(
			screen.queryByRole("link", { name: "Read" }),
		).not.toBeInTheDocument();

		const unreadFilter = screen.getByLabelText("Unread state filter");
		expect(unreadFilter).toHaveValue("unread");
		expect(
			within(unreadFilter).getByRole("option", { name: /All/ }),
		).toBeDisabled();
		expect(
			within(unreadFilter).getByRole("option", { name: /Read only/ }),
		).toBeDisabled();

		fireEvent.change(unreadFilter, { target: { value: "read" } });
		expect(unreadFilter).toHaveValue("unread");
	});

	it("uses ascending sort direction when dashboard descending is false", async () => {
		setPath("/");
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () =>
				makeSnapshot({
					sort_by: "score",
					descending: false,
					groups: [{ name: "g", items: [makeItem({ thread_id: "1" })] }],
				}),
		});

		render(<App />);

		await waitFor(() => {
			expect(
				screen.getByRole("link", { name: "Review API changes" }),
			).toBeVisible();
		});
		expect(
			screen.getByRole("columnheader", { name: /Score/ }),
		).toBeInTheDocument();
	});

	it("toggles shortcuts panel and enables browser notifications", async () => {
		setPath("/");
		const requestPermission = vi.fn(async () => "granted");
		class NotificationMock {
			static permission: NotificationPermission = "default";
			static requestPermission = requestPermission;
			addEventListener() {}
			close() {}
		}
		Object.defineProperty(globalThis, "Notification", {
			value: NotificationMock,
			writable: true,
		});

		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () =>
				makeSnapshot({
					notifications_config: {
						browser_tab: {
							enabled: true,
							max_per_cycle: 2,
							cooldown_seconds: 10,
						},
					},
				}),
		});

		const user = userEvent.setup();
		render(<App />);

		await waitFor(() => {
			expect(screen.getByRole("button", { name: /shortcuts/i })).toBeVisible();
		});

		await user.click(screen.getByRole("button", { name: /shortcuts/i }));
		expect(
			screen.getByRole("dialog", { name: "Keyboard shortcuts" }),
		).toBeVisible();

		await user.click(screen.getByRole("button", { name: /shortcuts/i }));
		expect(
			screen.queryByRole("dialog", { name: "Keyboard shortcuts" }),
		).not.toBeInTheDocument();

		await user.click(
			screen.getByRole("button", { name: "Enable browser notifications" }),
		);
		expect(requestPermission).toHaveBeenCalledTimes(1);
	});

	it("restores default dashboard on popstate to unknown dashboard", async () => {
		setPath("/dashboards/overview");
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () =>
				makeSnapshot({
					dashboard_names: ["overview", "triage"],
					groups: [
						{
							name: "group-a",
							items: [makeItem({ subject_title: "Known" })],
						},
					],
				}),
		});

		render(<App />);

		await waitFor(() => {
			expect(screen.getByRole("link", { name: "Known" })).toBeVisible();
		});

		setPath("/dashboards/does-not-exist");
		globalThis.dispatchEvent(new PopStateEvent("popstate"));

		await waitFor(() => {
			expect(globalThis.location.pathname).toBe("/dashboards/overview");
		});
	});

	it("shows explicit repo empty state after reading the last unread item", async () => {
		setPath("/");
		const firstSnapshot = makeSnapshot({
			include_read: false,
			groups: [
				{
					name: "org/repo-a",
					items: [
						makeItem({
							thread_id: "1",
							subject_title: "Last unread",
							repository: "org/repo-a",
							unread: true,
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
			dashboard_names: ["overview"],
		});
		const secondSnapshot = makeSnapshot({
			include_read: false,
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
		});

		let getCount = 0;
		vi.spyOn(globalThis, "fetch").mockImplementation(
			async (_input: FetchInput, init?: RequestInit) => {
				if (init?.method === "POST") {
					return { ok: true } as Response;
				}
				getCount += 1;
				return {
					ok: true,
					json: async () => (getCount === 1 ? firstSnapshot : secondSnapshot),
				} as Response;
			},
		);

		const user = userEvent.setup();
		render(<App />);

		await waitFor(() => {
			expect(
				screen.getByRole("link", { name: "Last unread" }),
			).toBeInTheDocument();
		});

		await user.selectOptions(
			screen.getByLabelText("Repository filter"),
			"org/repo-a",
		);
		await user.click(screen.getByRole("link", { name: "Last unread" }));

		await waitFor(() => {
			expect(
				screen.getByText("No unread notifications in org/repo-a"),
			).toBeInTheDocument();
		});

		const repositoryFilter = screen.getByLabelText("Repository filter");
		expect(repositoryFilter).toHaveValue("org/repo-a");
		expect(
			within(repositoryFilter).getByRole("option", {
				name: "org/repo-a (no unread notifications)",
			}),
		).toBeInTheDocument();
	});

	it("shows poller warning banner when poller status is error", async () => {
		setPath("/");
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () =>
				makeSnapshot({
					poller: {
						status: "error",
						last_poll_time: "2026-04-09T10:00:00Z",
						last_error: "Something failed",
						last_error_time: "2026-04-09T10:00:00Z",
						stale: false,
					},
					groups: [{ name: "g", items: [makeItem()] }],
				}),
		});

		render(<App />);

		await waitFor(() => {
			expect(screen.getByRole("alert", { name: undefined })).toHaveTextContent(
				"Something failed",
			);
		});
		expect(
			screen.getByRole("alert").classList.contains("poller-warning--error"),
		).toBe(true);
	});

	it("shows poller warning banner when poller is ok but stale", async () => {
		setPath("/");
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () =>
				makeSnapshot({
					poller: {
						status: "ok",
						last_poll_time: null,
						last_error: null,
						last_error_time: null,
						stale: true,
					},
					groups: [{ name: "g", items: [makeItem()] }],
				}),
		});

		render(<App />);

		await waitFor(() => {
			expect(screen.getByRole("status")).toHaveTextContent("Data may be stale");
		});
		expect(
			screen.getByRole("status").classList.contains("poller-warning--stale"),
		).toBe(true);
	});

	it("opens ignore-rule dialog from row context menu and loads both snippets", async () => {
		setPath("/");
		const snapshot = makeSnapshot({
			groups: [
				{
					name: "group-a",
					items: [
						makeItem({
							thread_id: "item-42",
							subject_title: "Rule target",
							repository: "org/repo-a",
							reason: "mention",
							subject_type: "PullRequest",
						}),
					],
				},
			],
			total_items: 1,
			dashboard_names: ["overview"],
		});
		vi.spyOn(globalThis, "fetch").mockImplementation(
			async (input: FetchInput, init?: RequestInit) => {
				if (init?.method === "POST") {
					return { ok: true } as Response;
				}
				const url = requestUrl(input);
				if (url.includes("/rule-snippets")) {
					return {
						ok: true,
						json: async () => ({
							dashboard_name: "overview",
							dashboard_ignore_rule_snippet:
								'- repository_in: ["org/repo-a"]\n  reason_in: ["mention"]\n  subject_type_in: ["PullRequest"]',
							global_exclude_rule_snippet:
								'- name: ignore-org-repo-a-mention-pullrequest\n  match:\n    repository_in: ["org/repo-a"]\n    reason_in: ["mention"]\n    subject_type_in: ["PullRequest"]\n  exclude_from_dashboards: true',
							dashboard_ignore_rule_with_context_snippet: null,
							global_exclude_rule_with_context_snippet: null,
							has_context: false,
						}),
					} as Response;
				}
				return {
					ok: true,
					json: async () => snapshot,
				} as Response;
			},
		);

		render(<App />);
		const user = userEvent.setup();

		await waitFor(() => {
			expect(
				screen.getByRole("link", { name: "Rule target" }),
			).toBeInTheDocument();
		});

		const row = screen.getByRole("link", { name: "Rule target" }).closest("tr");
		expect(row).not.toBeNull();
		fireEvent.contextMenu(row as Element);

		await user.click(
			screen.getByRole("menuitem", { name: "Create ignore rule..." }),
		);

		await waitFor(() => {
			expect(
				screen.getByRole("heading", { name: "Dashboard ignore rule" }),
			).toBeInTheDocument();
		});
		expect(
			screen.getByRole("heading", { name: "Global exclude rule" }),
		).toBeInTheDocument();
		expect(screen.getAllByDisplayValue(/repository_in/)).toHaveLength(2);
	});

	it("keeps encoded dashboard paths stable when the current path already matches", async () => {
		setPath("/dashboards/Triage%20Board");
		const pushState = vi.spyOn(globalThis.history, "pushState");
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () =>
				makeSnapshot({
					name: "Triage Board",
					dashboard_names: ["Triage Board"],
					groups: [
						{ name: "g", items: [makeItem({ subject_title: "Encoded" })] },
					],
				}),
		});

		render(<App />);

		await waitFor(() => {
			expect(screen.getByRole("link", { name: "Encoded" })).toBeInTheDocument();
		});
		expect(globalThis.location.pathname).toBe("/dashboards/Triage%20Board");
		expect(pushState).not.toHaveBeenCalled();
	});

	it("closes the row context menu on escape and outside click", async () => {
		setPath("/");
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () =>
				makeSnapshot({
					groups: [
						{ name: "g", items: [makeItem({ subject_title: "Menu target" })] },
					],
				}),
		});

		render(<App />);

		await waitFor(() => {
			expect(
				screen.getByRole("link", { name: "Menu target" }),
			).toBeInTheDocument();
		});

		const row = screen.getByRole("link", { name: "Menu target" }).closest("tr");
		expect(row).not.toBeNull();
		fireEvent.contextMenu(row as Element);
		expect(screen.getByRole("menu")).toBeInTheDocument();

		globalThis.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
		await waitFor(() => {
			expect(screen.queryByRole("menu")).not.toBeInTheDocument();
		});

		fireEvent.contextMenu(row as Element);
		expect(screen.getByRole("menu")).toBeInTheDocument();
		globalThis.dispatchEvent(new MouseEvent("click"));
		await waitFor(() => {
			expect(screen.queryByRole("menu")).not.toBeInTheDocument();
		});
	});

	it("shows ignore-rule loading and error states when snippet fetch fails", async () => {
		setPath("/");
		let rejectSnippets: ((reason?: unknown) => void) | null = null;
		vi.spyOn(globalThis, "fetch").mockImplementation(
			async (input: FetchInput, init?: RequestInit) => {
				if (init?.method === "POST") {
					return { ok: true } as Response;
				}
				const url = requestUrl(input);
				if (url.includes("/rule-snippets")) {
					return {
						ok: true,
						json: () =>
							new Promise((_, reject) => {
								rejectSnippets = reject;
							}),
					} as Response;
				}
				return {
					ok: true,
					json: async () =>
						makeSnapshot({
							groups: [
								{
									name: "g",
									items: [makeItem({ subject_title: "Rule target" })],
								},
							],
						}),
				} as Response;
			},
		);

		const user = userEvent.setup();
		render(<App />);

		await waitFor(() => {
			expect(
				screen.getByRole("link", { name: "Rule target" }),
			).toBeInTheDocument();
		});

		const row = screen.getByRole("link", { name: "Rule target" }).closest("tr");
		expect(row).not.toBeNull();
		fireEvent.contextMenu(row as Element);
		await user.click(
			screen.getByRole("menuitem", { name: "Create ignore rule..." }),
		);

		await waitFor(() => {
			expect(screen.getByText("Loading snippets...")).toBeInTheDocument();
		});
		rejectSnippets?.(new Error("snippet boom"));

		await waitFor(() => {
			expect(screen.getByText("snippet boom")).toBeInTheDocument();
		});
	});
});
