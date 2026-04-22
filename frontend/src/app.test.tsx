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
		await user.selectOptions(
			screen.getByLabelText("Reason filter"),
			"subscribed",
		);
		expect(screen.getByRole("link", { name: "Two" })).toBeInTheDocument();
		expect(screen.queryByRole("link", { name: "One" })).not.toBeInTheDocument();
		await user.selectOptions(screen.getByLabelText("Reason filter"), "");

		await user.selectOptions(
			screen.getByLabelText("Select dashboard"),
			"triage",
		);
		await waitFor(() => {
			expect(screen.getByRole("link", { name: "Three" })).toBeInTheDocument();
		});
		expect(globalThis.location.pathname).toBe("/dashboards/triage");
	});

	it("shows error state when snapshot fetch fails", async () => {
		setPath("/");
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: false,
			status: 500,
		} as Response);

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
		} as Response);

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
		} as Response);

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
		} as Response);

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
		} as Response);

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
		} as Response);

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
		} as Response);

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
		} as Response);

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
});
