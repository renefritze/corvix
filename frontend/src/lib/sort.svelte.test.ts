import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { Router } from "./router.svelte";
import { SortStore } from "./sort.svelte";
import type { SortColumn, SortDirection } from "../types";

function make(
	path = "/",
	seedColumn?: () => SortColumn,
	seedDir?: () => SortDirection,
) {
	history.pushState({}, "", path);
	const router = new Router();
	return { router, store: new SortStore(router, seedColumn, seedDir) };
}

describe("SortStore", () => {
	beforeEach(() => history.pushState({}, "", "/"));
	afterEach(() => history.pushState({}, "", "/"));

	it("seeds from the built-in defaults", () => {
		const { store } = make("/");
		expect(store.sortColumn).toBe("score");
		expect(store.sortDirection).toBe("desc");
	});

	it("seeds from supplied seed getters", () => {
		const { store } = make(
			"/",
			() => "updated_at",
			() => "asc",
		);
		expect(store.sortColumn).toBe("updated_at");
		expect(store.sortDirection).toBe("asc");
	});

	it("reads sort/dir from the URL, overriding seeds", () => {
		const { store } = make("/?sort=reason&dir=asc");
		expect(store.sortColumn).toBe("reason");
		expect(store.sortDirection).toBe("asc");
	});

	it("falls back to seeds when the URL values are invalid", () => {
		const { store } = make("/?sort=bogus&dir=sideways");
		expect(store.sortColumn).toBe("score");
		expect(store.sortDirection).toBe("desc");
	});

	it("defaults to desc when sorting a new column", () => {
		const { router, store } = make("/");
		store.handleSort("repository");
		expect(router.query.get("sort")).toBe("repository");
		expect(router.query.get("dir")).toBe("desc");
		expect(store.sortColumn).toBe("repository");
		expect(store.sortDirection).toBe("desc");
	});

	it("toggles direction when re-sorting the active column", () => {
		const { router, store } = make("/?sort=score&dir=desc");
		store.handleSort("score");
		expect(router.query.get("dir")).toBe("asc");
		store.handleSort("score");
		expect(router.query.get("dir")).toBe("desc");
	});

	it("resets to desc when switching to a different column", () => {
		const { router, store } = make("/?sort=score&dir=asc");
		store.handleSort("repository");
		expect(router.query.get("sort")).toBe("repository");
		expect(router.query.get("dir")).toBe("desc");
	});
});
