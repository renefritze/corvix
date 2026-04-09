import {
	dismissNotification,
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

		await expect(dismissNotification("thread 1")).rejects.toThrow(
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

		await expect(dismissNotification("thread-2")).rejects.toThrow(
			"Dismiss failed (400)",
		);
	});

	it("markNotificationRead sends keepalive POST", async () => {
		const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
		} as Response);

		await expect(markNotificationRead("thread/3")).resolves.toBeUndefined();
		expect(fetchMock).toHaveBeenCalledWith(
			"/api/notifications/thread%2F3/mark-read",
			{
				method: "POST",
				keepalive: true,
			},
		);
	});
});
