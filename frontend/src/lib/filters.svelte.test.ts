import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { FiltersStore } from "./filters.svelte";
import { Router } from "./router.svelte";

function make(path = "/") {
	history.pushState({}, "", path);
	const router = new Router();
	return { router, store: new FiltersStore(router) };
}

describe("FiltersStore", () => {
	beforeEach(() => history.pushState({}, "", "/"));
	afterEach(() => history.pushState({}, "", "/"));

	it("defaults when the query is empty", () => {
		const { store } = make("/");
		expect(store.filters).toEqual({ unread: "all", reason: [], repository: "" });
	});

	it("reads filter state from the URL query", () => {
		const { store } = make(
			"/?unread=read&reason=mention,subscribed&repository=org/repo",
		);
		expect(store.filters).toEqual({
			unread: "read",
			reason: ["mention", "subscribed"],
			repository: "org/repo",
		});
	});

	it("ignores an invalid unread value", () => {
		const { store } = make("/?unread=bogus");
		expect(store.filters.unread).toBe("all");
	});

	it("drops empty reason segments", () => {
		const { store } = make("/?reason=,mention,");
		expect(store.filters.reason).toEqual(["mention"]);
	});

	it("writes filters back to the URL, omitting defaults", () => {
		const { router, store } = make("/");
		store.setFilter("reason", ["subscribed"]);
		expect(router.query.get("reason")).toBe("subscribed");
		expect(store.filters.reason).toEqual(["subscribed"]);

		store.setFilter("unread", "read");
		expect(router.query.get("unread")).toBe("read");

		store.setFilter("repository", "org/repo");
		expect(router.query.get("repository")).toBe("org/repo");
	});

	it("removes a filter set back to its default value", () => {
		const { router, store } = make("/?unread=read");
		store.setFilter("unread", "all");
		expect(router.query.get("unread")).toBeNull();
	});

	it("clears every filter", () => {
		const { router, store } = make(
			"/?unread=read&reason=mention&repository=org/repo",
		);
		store.clearFilters();
		expect(router.search).toBe("");
		expect(store.filters).toEqual({ unread: "all", reason: [], repository: "" });
	});
});
