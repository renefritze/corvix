import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { Router } from "./router.svelte";

describe("Router", () => {
	beforeEach(() => history.pushState({}, "", "/"));
	afterEach(() => history.pushState({}, "", "/"));

	it("reads the initial location into pathname/search", () => {
		history.pushState({}, "", "/dashboards/team?reason=a");
		const router = new Router();
		expect(router.pathname).toBe("/dashboards/team");
		expect(router.search).toBe("?reason=a");
		expect(router.relativeUrl).toBe("/dashboards/team?reason=a");
		router.destroy();
	});

	it("matches the root route", () => {
		const router = new Router();
		expect(router.route).toEqual({ name: undefined, matched: true });
		router.destroy();
	});

	it("matches a decoded dashboard route", () => {
		history.pushState({}, "", "/dashboards/my%20team");
		const router = new Router();
		expect(router.route).toEqual({ name: "my team", matched: true });
		router.destroy();
	});

	it("matches a dashboard route with a trailing slash", () => {
		history.pushState({}, "", "/dashboards/overview/");
		const router = new Router();
		expect(router.route).toEqual({ name: "overview", matched: true });
		router.destroy();
	});

	it("falls back to the raw segment when decoding fails", () => {
		const router = new Router();
		router.navigate("/dashboards/%E0%A4%A");
		expect(router.route.matched).toBe(true);
		expect(router.route.name).toBe("%E0%A4%A");
		router.destroy();
	});

	it("reports an unmatched route for unknown paths", () => {
		history.pushState({}, "", "/nope/here");
		const router = new Router();
		expect(router.route).toEqual({ name: undefined, matched: false });
		router.destroy();
	});

	it("exposes the query as URLSearchParams", () => {
		history.pushState({}, "", "/?a=1&b=2");
		const router = new Router();
		expect(router.query.get("a")).toBe("1");
		expect(router.query.get("b")).toBe("2");
		router.destroy();
	});

	it("navigates by pushing state and syncing", () => {
		const router = new Router();
		router.navigate("/dashboards/x?q=1");
		expect(router.pathname).toBe("/dashboards/x");
		expect(router.search).toBe("?q=1");
		expect(globalThis.location.pathname).toBe("/dashboards/x");
		router.destroy();
	});

	it("navigates with replace using replaceState", () => {
		const router = new Router();
		const before = history.length;
		router.navigate("/replaced", true);
		expect(router.pathname).toBe("/replaced");
		expect(history).toHaveLength(before);
		router.destroy();
	});

	it("merges query updates, removing empty and null values", () => {
		history.pushState({}, "", "/dash?keep=1&drop=x&blank=y");
		const router = new Router();
		router.updateQuery({ drop: null, blank: "", added: "z" });
		expect(router.query.get("keep")).toBe("1");
		expect(router.query.get("drop")).toBeNull();
		expect(router.query.get("blank")).toBeNull();
		expect(router.query.get("added")).toBe("z");
		router.destroy();
	});

	it("produces a bare path when the query becomes empty", () => {
		history.pushState({}, "", "/dash?only=1");
		const router = new Router();
		router.updateQuery({ only: null });
		expect(router.search).toBe("");
		expect(router.relativeUrl).toBe("/dash");
		router.destroy();
	});

	it("is a no-op when the resulting URL is unchanged", () => {
		history.pushState({}, "", "/dash?a=1");
		const router = new Router();
		const before = router.relativeUrl;
		router.updateQuery({ a: "1" });
		expect(router.relativeUrl).toBe(before);
		router.destroy();
	});

	it("syncs from location on popstate", () => {
		const router = new Router();
		history.pushState({}, "", "/dashboards/back?q=2");
		globalThis.dispatchEvent(new PopStateEvent("popstate"));
		expect(router.pathname).toBe("/dashboards/back");
		expect(router.search).toBe("?q=2");
		router.destroy();
	});

	it("stops listening after destroy", () => {
		const router = new Router();
		router.destroy();
		router.destroy(); // idempotent
		history.pushState({}, "", "/after-destroy");
		globalThis.dispatchEvent(new PopStateEvent("popstate"));
		expect(router.pathname).toBe("/");
	});
});
