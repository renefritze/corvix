import { beforeEach, describe, expect, it } from "vitest";
import { GroupCollapseStore } from "./groupCollapse.svelte";

describe("GroupCollapseStore", () => {
	beforeEach(() => sessionStorage.clear());

	it("toggles collapsed state per group", () => {
		const store = new GroupCollapseStore();
		store.setDashboard("overview");
		expect(store.isCollapsed("org/repo-a")).toBe(false);
		store.toggle("org/repo-a");
		expect(store.isCollapsed("org/repo-a")).toBe(true);
		store.toggle("org/repo-a");
		expect(store.isCollapsed("org/repo-a")).toBe(false);
	});

	it("persists collapsed groups to sessionStorage per dashboard", () => {
		const store = new GroupCollapseStore();
		store.setDashboard("overview");
		store.toggle("org/repo-a");

		const reloaded = new GroupCollapseStore();
		reloaded.setDashboard("overview");
		expect(reloaded.isCollapsed("org/repo-a")).toBe(true);

		reloaded.setDashboard("triage");
		expect(reloaded.isCollapsed("org/repo-a")).toBe(false);
	});

	it("ignores a repeated setDashboard for the same name", () => {
		const store = new GroupCollapseStore();
		store.setDashboard("overview");
		store.toggle("g");
		store.setDashboard("overview");
		expect(store.isCollapsed("g")).toBe(true);
	});

	it("recovers from malformed storage", () => {
		sessionStorage.setItem("corvix.groups.collapsed.overview", "not json");
		const store = new GroupCollapseStore();
		store.setDashboard("overview");
		expect(store.isCollapsed("anything")).toBe(false);
	});
});
