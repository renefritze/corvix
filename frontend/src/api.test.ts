import { afterEach, describe, expect, it, vi } from "vitest";
import {
	UnauthorizedError,
	dismissNotification,
	fetchRuleSnippets,
	fetchSnapshot,
	markNotificationRead,
	setUnauthorizedHandler,
	snapshotEventsUrl,
} from "./api";
import { makeSnapshot } from "./test/fixtures";
import { mockResponse } from "./test/http";

describe("api", () => {
	it("fetchSnapshot returns payload and encodes the dashboard query", async () => {
		const payload = makeSnapshot({ name: "triage" });
		const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
			mockResponse({
				ok: true,
				json: async () => payload,
			}),
		);

		await expect(fetchSnapshot("my board")).resolves.toEqual(payload);
		expect(fetchMock).toHaveBeenCalledWith(
			"/api/v1/snapshot?dashboard=my%20board",
		);
	});

	it("fetchSnapshot omits the query string without a dashboard", async () => {
		const payload = makeSnapshot();
		const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
			mockResponse({
				ok: true,
				json: async () => payload,
			}),
		);

		await expect(fetchSnapshot()).resolves.toEqual(payload);
		expect(fetchMock).toHaveBeenCalledWith("/api/v1/snapshot");
	});

	it("fetchSnapshot throws a generic error on non-OK responses", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue(
			mockResponse({
				ok: false,
				status: 500,
			}),
		);

		await expect(fetchSnapshot()).rejects.toThrow("Snapshot fetch failed: 500");
	});

	it("snapshotEventsUrl builds the SSE url with and without a dashboard", () => {
		expect(snapshotEventsUrl()).toBe("/api/v1/events");
		expect(snapshotEventsUrl("my board")).toBe(
			"/api/v1/events?dashboard=my%20board",
		);
	});

	it("dismissNotification encodes ids and resolves on success", async () => {
		const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
			mockResponse({ ok: true }),
		);

		await expect(
			dismissNotification("primary", "thread/1"),
		).resolves.toBeUndefined();
		expect(fetchMock).toHaveBeenCalledWith(
			"/api/v1/notifications/primary/thread%2F1/dismiss",
			{ method: "POST" },
		);
	});

	it("dismissNotification surfaces detail from a JSON error response", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue(
			mockResponse({
				ok: false,
				status: 422,
				json: async () => ({ detail: "cannot dismiss" }),
			}),
		);

		await expect(dismissNotification("primary", "thread 1")).rejects.toThrow(
			"Dismiss failed (422): cannot dismiss",
		);
	});

	it("dismissNotification falls back to status when body is not JSON", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue(
			mockResponse({
				ok: false,
				status: 400,
				json: async () => {
					throw new Error("bad json");
				},
			}),
		);

		await expect(dismissNotification("primary", "thread-2")).rejects.toThrow(
			"Dismiss failed (400)",
		);
	});

	it("ignores a non-string detail field and falls back to status", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue(
			mockResponse({
				ok: false,
				status: 418,
				json: async () => ({ detail: 123 }),
			}),
		);

		await expect(dismissNotification("primary", "thread-3")).rejects.toThrow(
			"Dismiss failed (418)",
		);
	});

	it("markNotificationRead sends a keepalive POST", async () => {
		const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
			mockResponse({ ok: true }),
		);

		await expect(
			markNotificationRead("primary", "thread/3"),
		).resolves.toBeUndefined();
		expect(fetchMock).toHaveBeenCalledWith(
			"/api/v1/notifications/primary/thread%2F3/mark-read",
			{ method: "POST", keepalive: true },
		);
	});

	it("markNotificationRead throws a generic error on failure", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue(
			mockResponse({ ok: false, status: 500 }),
		);

		await expect(markNotificationRead("primary", "t")).rejects.toThrow(
			"Mark read failed: 500",
		);
	});

	it("fetchRuleSnippets includes the dashboard query and returns payload", async () => {
		const payload = {
			dashboard_name: "overview",
			dashboard_ignore_rule_snippet: '- repository_in: ["org/repo-a"]',
			global_exclude_rule_snippet:
				"- name: ignore-org-repo-a-mention-pullrequest",
			dashboard_ignore_rule_with_context_snippet: null,
			global_exclude_rule_with_context_snippet: null,
			has_context: false,
		};
		const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
			mockResponse({
				ok: true,
				json: async () => payload,
			}),
		);

		await expect(
			fetchRuleSnippets("primary", "thread/4", "my board"),
		).resolves.toEqual(payload);
		expect(fetchMock).toHaveBeenCalledWith(
			"/api/v1/notifications/primary/thread%2F4/rule-snippets?dashboard=my%20board",
		);
	});

	it("fetchRuleSnippets omits the query without a dashboard", async () => {
		const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
			mockResponse({
				ok: true,
				json: async () => ({}),
			}),
		);

		await fetchRuleSnippets("primary", "thread-6");
		expect(fetchMock).toHaveBeenCalledWith(
			"/api/v1/notifications/primary/thread-6/rule-snippets",
		);
	});

	it("fetchRuleSnippets surfaces detail from a JSON error response", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue(
			mockResponse({
				ok: false,
				status: 404,
				json: async () => ({ detail: "Notification not found" }),
			}),
		);

		await expect(fetchRuleSnippets("primary", "missing")).rejects.toThrow(
			"Rule snippets fetch failed (404): Notification not found",
		);
	});

	it("fetchRuleSnippets falls back to status when error body is not JSON", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue(
			mockResponse({
				ok: false,
				status: 503,
				json: async () => {
					throw new Error("bad json");
				},
			}),
		);

		await expect(fetchRuleSnippets("primary", "thread-5")).rejects.toThrow(
			"Rule snippets fetch failed (503)",
		);
	});

	describe("auth handling", () => {
		afterEach(() => {
			setUnauthorizedHandler(null);
		});

		it("throws UnauthorizedError on a 401 snapshot fetch", async () => {
			vi.spyOn(globalThis, "fetch").mockResolvedValue(
				mockResponse({
					ok: false,
					status: 401,
					json: async () => ({ detail: "token expired" }),
				}),
			);

			await expect(fetchSnapshot()).rejects.toBeInstanceOf(UnauthorizedError);
		});

		it("carries status and detail message on a 403 UnauthorizedError", async () => {
			vi.spyOn(globalThis, "fetch").mockResolvedValue(
				mockResponse({
					ok: false,
					status: 403,
					json: async () => ({ detail: "forbidden" }),
				}),
			);

			const error = await dismissNotification("primary", "thread-1").then(
				() => null,
				(err: unknown) => err,
			);
			expect(error).toBeInstanceOf(UnauthorizedError);
			expect((error as UnauthorizedError).status).toBe(403);
			expect((error as UnauthorizedError).message).toBe("forbidden");
		});

		it("uses a default message when the 401 body has no detail", async () => {
			vi.spyOn(globalThis, "fetch").mockResolvedValue(
				mockResponse({
					ok: false,
					status: 401,
					json: async () => {
						throw new Error("bad json");
					},
				}),
			);

			await expect(
				markNotificationRead("primary", "thread-1"),
			).rejects.toThrow("Your session has expired or you are not signed in.");
		});

		it("notifies the registered handler on a 401 and supports unsubscribe", async () => {
			vi.spyOn(globalThis, "fetch").mockResolvedValue(
				mockResponse({
					ok: false,
					status: 401,
					json: async () => ({ detail: "nope" }),
				}),
			);

			const handler = vi.fn();
			const unsubscribe = setUnauthorizedHandler(handler);

			await expect(fetchSnapshot()).rejects.toBeInstanceOf(UnauthorizedError);
			expect(handler).toHaveBeenCalledTimes(1);
			expect(handler.mock.calls[0][0]).toBeInstanceOf(UnauthorizedError);

			unsubscribe();
			await expect(fetchSnapshot()).rejects.toBeInstanceOf(UnauthorizedError);
			expect(handler).toHaveBeenCalledTimes(1);
		});

		it("unsubscribe only clears the handler while it is still active", async () => {
			vi.spyOn(globalThis, "fetch").mockResolvedValue(
				mockResponse({
					ok: false,
					status: 401,
					json: async () => ({ detail: "nope" }),
				}),
			);

			const first = vi.fn();
			const second = vi.fn();
			const unsubscribeFirst = setUnauthorizedHandler(first);
			setUnauthorizedHandler(second);

			// `first` is no longer the active handler, so its unsubscribe is a no-op.
			unsubscribeFirst();

			await expect(fetchSnapshot()).rejects.toBeInstanceOf(UnauthorizedError);
			expect(first).not.toHaveBeenCalled();
			expect(second).toHaveBeenCalledTimes(1);
		});

		it("does not treat non-auth errors as UnauthorizedError", async () => {
			vi.spyOn(globalThis, "fetch").mockResolvedValue(
				mockResponse({
					ok: false,
					status: 500,
				}),
			);

			const handler = vi.fn();
			setUnauthorizedHandler(handler);

			await expect(fetchSnapshot()).rejects.toThrow(
				"Snapshot fetch failed: 500",
			);
			await expect(fetchSnapshot()).rejects.not.toBeInstanceOf(
				UnauthorizedError,
			);
			expect(handler).not.toHaveBeenCalled();
		});
	});
});
