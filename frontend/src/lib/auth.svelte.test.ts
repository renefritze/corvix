import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import { AuthStore } from "./auth.svelte";
import { mockResponse } from "../test/http";

function mock401(detail = "session gone") {
	vi.spyOn(globalThis, "fetch").mockResolvedValue(
		mockResponse({
			ok: false,
			status: 401,
			json: async () => ({ detail }),
		}),
	);
}

describe("AuthStore", () => {
	let store: AuthStore | undefined;

	afterEach(() => {
		store?.destroy();
		store = undefined;
		api.setUnauthorizedHandler(null);
	});

	it("starts authenticated with no message", () => {
		store = new AuthStore();
		expect(store.status).toBe("authenticated");
		expect(store.message).toBeNull();
	});

	it("flips to unauthenticated via signalUnauthenticated and back via reset", () => {
		store = new AuthStore();
		store.signalUnauthenticated("manual sign-out");
		expect(store.status).toBe("unauthenticated");
		expect(store.message).toBe("manual sign-out");

		store.reset();
		expect(store.status).toBe("authenticated");
		expect(store.message).toBeNull();
	});

	it("defaults the message to null when signalled without one", () => {
		store = new AuthStore();
		store.signalUnauthenticated();
		expect(store.status).toBe("unauthenticated");
		expect(store.message).toBeNull();
	});

	it("bridges an API 401 into the unauthenticated state", async () => {
		mock401("session gone");
		store = new AuthStore();
		await api.fetchSnapshot().catch(() => {});
		expect(store.status).toBe("unauthenticated");
		expect(store.message).toBe("session gone");
	});

	it("unregisters its handler on destroy", async () => {
		store = new AuthStore();
		store.destroy();
		store = undefined;

		mock401();
		const survivor = new AuthStore();
		// The destroyed store's handler is gone; the new store owns it now.
		await api.fetchSnapshot().catch(() => {});
		expect(survivor.status).toBe("unauthenticated");
		survivor.destroy();
	});
});
