import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { Router } from "./router.svelte";
import { SearchStore } from "./search.svelte";
import { makeItem } from "../test/fixtures";

function make(path = "/") {
	history.pushState({}, "", path);
	const router = new Router();
	return { router, store: new SearchStore(router) };
}

describe("SearchStore", () => {
	beforeEach(() => history.pushState({}, "", "/"));
	afterEach(() => history.pushState({}, "", "/"));

	it("defaults to an empty query", () => {
		const { store } = make("/");
		expect(store.query).toBe("");
	});

	it("reads the query from the q param", () => {
		const { store } = make("/?q=api");
		expect(store.query).toBe("api");
	});

	it("writes the query to the URL", () => {
		const { router, store } = make("/");
		store.setQuery("review");
		expect(router.query.get("q")).toBe("review");
		expect(store.query).toBe("review");
	});

	it("clears the query", () => {
		const { router, store } = make("/?q=review");
		store.clear();
		expect(router.query.get("q")).toBeNull();
		expect(store.query).toBe("");
	});

	it("matches everything when the query is empty or whitespace", () => {
		const { store } = make("/?q=%20%20");
		expect(store.matches(makeItem())).toBe(true);
	});

	it("matches case-insensitively across title, repo, reason and type", () => {
		const { store: byTitle } = make("/?q=REVIEW");
		expect(byTitle.matches(makeItem({ subject_title: "Review API" }))).toBe(true);

		const { store: byRepo } = make("/?q=repo-a");
		expect(byRepo.matches(makeItem({ repository: "org/repo-a" }))).toBe(true);

		const { store: byReason } = make("/?q=mention");
		expect(byReason.matches(makeItem({ reason: "mention" }))).toBe(true);

		const { store: byType } = make("/?q=pullrequest");
		expect(byType.matches(makeItem({ subject_type: "PullRequest" }))).toBe(true);
	});

	it("returns false when nothing matches", () => {
		const { store } = make("/?q=zzzznope");
		expect(
			store.matches(
				makeItem({
					subject_title: "Review API",
					repository: "org/repo-a",
					reason: "mention",
					subject_type: "PullRequest",
				}),
			),
		).toBe(false);
	});
});
