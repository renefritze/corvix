import {
	dismissNotification,
	fetchRuleSnippets,
	fetchSnapshot,
	markNotificationRead,
} from "./api";
import { makeSnapshot } from "./test/fixtures";

describe("api", () => {
	it("fetchSnapshot returns payload", async () => {
		const payload = makeSnapshot({ name: "triage" });
		const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => payload,
		} as Response);

		await expect(fetchSnapshot("triage")).resolves.toEqual(payload);
		expect(fetchMock).toHaveBeenCalledWith("/api/snapshot?dashboard=triage");
	});

	it("fetchSnapshot throws on non-OK responses", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: false,
			status: 500,
		} as Response);

		await expect(fetchSnapshot()).rejects.toThrow("Snapshot fetch failed: 500");
	});

	it("dismissNotification surfaces detail from JSON response", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: false,
			status: 422,
			json: async () => ({ detail: "cannot dismiss" }),
		} as Response);

		await expect(dismissNotification("primary", "thread 1")).rejects.toThrow(
			"Dismiss failed (422): cannot dismiss",
		);
	});

	it("dismissNotification falls back to status when body is not JSON", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: false,
			status: 400,
			json: async () => {
				throw new Error("bad json");
			},
		} as Response);

		await expect(dismissNotification("primary", "thread-2")).rejects.toThrow(
			"Dismiss failed (400)",
		);
	});

	it("markNotificationRead sends keepalive POST", async () => {
		const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
		} as Response);

		await expect(
			markNotificationRead("primary", "thread/3"),
		).resolves.toBeUndefined();
		expect(fetchMock).toHaveBeenCalledWith(
			"/api/notifications/primary/thread%2F3/mark-read",
			{
				method: "POST",
				keepalive: true,
			},
		);
	});

	it("fetchRuleSnippets includes dashboard query and returns payload", async () => {
		const payload = {
			dashboard_name: "overview",
			dashboard_ignore_rule_snippet: '- repository_in: ["org/repo-a"]',
			global_exclude_rule_snippet:
				"- name: ignore-org-repo-a-mention-pullrequest",
			dashboard_ignore_rule_with_context_snippet: null,
			global_exclude_rule_with_context_snippet: null,
			has_context: false,
		};
		const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => payload,
		} as Response);

		await expect(
			fetchRuleSnippets("primary", "thread/4", "my board"),
		).resolves.toEqual(payload);
		expect(fetchMock).toHaveBeenCalledWith(
			"/api/notifications/primary/thread%2F4/rule-snippets?dashboard=my%20board",
		);
	});

	it("fetchRuleSnippets surfaces detail from JSON error response", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: false,
			status: 404,
			json: async () => ({ detail: "Notification not found" }),
		} as Response);

		await expect(fetchRuleSnippets("primary", "missing")).rejects.toThrow(
			"Rule snippets fetch failed (404): Notification not found",
		);
	});

	it("fetchRuleSnippets falls back to status when error body is not JSON", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: false,
			status: 503,
			json: async () => {
				throw new Error("bad json");
			},
		} as Response);

		await expect(fetchRuleSnippets("primary", "thread-5")).rejects.toThrow(
			"Rule snippets fetch failed (503)",
		);
	});
});
