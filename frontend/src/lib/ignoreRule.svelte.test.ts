import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import { makeItem } from "../test/fixtures";
import { flushSync, root } from "../test/runes.svelte";
import type { RuleSnippetsPayload } from "../types";
import { IgnoreRuleStore } from "./ignoreRule.svelte";

const SNIPPETS: RuleSnippetsPayload = {
	dashboard_name: "overview",
	dashboard_ignore_rule_snippet: "- repository_in: [org/repo-a]",
	global_exclude_rule_snippet: "- name: ignore",
	dashboard_ignore_rule_with_context_snippet: null,
	global_exclude_rule_with_context_snippet: null,
	has_context: false,
};

describe("IgnoreRuleStore", () => {
	let dispose: (() => void) | undefined;

	function make(getDashboard: () => string | null = () => "overview") {
		const { value, dispose: d } = root(() => {
			const s = new IgnoreRuleStore(getDashboard);
			s.bind();
			return s;
		});
		dispose = d;
		return value;
	}

	afterEach(() => {
		dispose?.();
		dispose = undefined;
		vi.restoreAllMocks();
	});

	it("opens the context menu at the requested position", () => {
		const store = make();
		store.requestRule(makeItem(), { x: 10, y: 20 });
		expect(store.menu).toEqual({ item: expect.anything(), x: 10, y: 20 });
	});

	it("opening the dialog clears the menu and sets the dialog item", () => {
		const store = make();
		const item = makeItem({ thread_id: "item-42" });
		store.requestRule(item, { x: 1, y: 2 });
		store.openDialog(item);
		expect(store.menu).toBeNull();
		expect(store.dialogItem?.thread_id).toBe("item-42");
	});

	it("closeDialog resets dialog/snippet/error/loading state", () => {
		const store = make();
		store.openDialog(makeItem());
		store.closeDialog();
		expect(store.dialogItem).toBeNull();
		expect(store.snippets).toBeNull();
		expect(store.error).toBeNull();
		expect(store.loading).toBe(false);
	});

	it("dismisses the menu on an outside click", () => {
		const store = make();
		store.requestRule(makeItem(), { x: 10, y: 20 });
		flushSync();
		globalThis.dispatchEvent(new MouseEvent("click"));
		flushSync();
		expect(store.menu).toBeNull();
	});

	it("dismisses the menu on Escape", () => {
		const store = make();
		store.requestRule(makeItem(), { x: 10, y: 20 });
		flushSync();
		globalThis.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
		flushSync();
		expect(store.menu).toBeNull();
	});

	it("ignores non-Escape keys while the menu is open", () => {
		const store = make();
		store.requestRule(makeItem(), { x: 10, y: 20 });
		flushSync();
		globalThis.dispatchEvent(new KeyboardEvent("keydown", { key: "a" }));
		flushSync();
		expect(store.menu).not.toBeNull();
	});

	it("loads snippets when the dialog opens", async () => {
		const spy = vi
			.spyOn(api, "fetchRuleSnippets")
			.mockResolvedValue(SNIPPETS);
		const store = make();
		store.openDialog(makeItem({ thread_id: "item-42" }));
		flushSync();

		expect(store.loading).toBe(true);
		await vi.waitFor(() => expect(store.snippets).toEqual(SNIPPETS));
		expect(store.loading).toBe(false);
		expect(store.error).toBeNull();
		expect(spy).toHaveBeenCalledWith("primary", "item-42", "overview");
	});

	it("passes undefined dashboard when getDashboard returns null", async () => {
		const spy = vi
			.spyOn(api, "fetchRuleSnippets")
			.mockResolvedValue(SNIPPETS);
		const store = make(() => null);
		store.openDialog(makeItem({ thread_id: "item-42" }));
		flushSync();
		await vi.waitFor(() => expect(store.snippets).toEqual(SNIPPETS));
		expect(spy).toHaveBeenCalledWith("primary", "item-42", undefined);
	});

	it("surfaces a snippet fetch error", async () => {
		vi.spyOn(api, "fetchRuleSnippets").mockRejectedValue(
			new Error("Rule snippets fetch failed (500)"),
		);
		const store = make();
		store.openDialog(makeItem());
		flushSync();

		await vi.waitFor(() =>
			expect(store.error).toBe("Rule snippets fetch failed (500)"),
		);
		expect(store.loading).toBe(false);
		expect(store.snippets).toBeNull();
	});

	it("falls back to a generic message for a non-Error rejection", async () => {
		vi.spyOn(api, "fetchRuleSnippets").mockRejectedValue("boom");
		const store = make();
		store.openDialog(makeItem());
		flushSync();
		await vi.waitFor(() =>
			expect(store.error).toBe("Failed to load rule snippets"),
		);
	});

	it("cancels a stale in-flight fetch when the dialog closes", async () => {
		let resolve!: (payload: RuleSnippetsPayload) => void;
		vi.spyOn(api, "fetchRuleSnippets").mockImplementation(
			() => new Promise((r) => (resolve = r)),
		);
		const store = make();
		store.openDialog(makeItem());
		flushSync();
		expect(store.loading).toBe(true);

		// Close before the fetch resolves; the cleanup marks it cancelled.
		store.closeDialog();
		flushSync();

		resolve(SNIPPETS);
		await Promise.resolve();
		await Promise.resolve();

		// The stale result must not repopulate the closed dialog.
		expect(store.snippets).toBeNull();
		expect(store.loading).toBe(false);
	});
});
