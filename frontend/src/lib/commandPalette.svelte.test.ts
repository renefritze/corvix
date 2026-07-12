import { describe, expect, it } from "vitest";
import {
	type Command,
	CommandPaletteStore,
	fuzzyMatch,
} from "./commandPalette.svelte";

function command(id: string, label: string): Command {
	return { id, label, run: () => {} };
}

describe("fuzzyMatch", () => {
	it("matches everything for an empty or whitespace query", () => {
		expect(fuzzyMatch("anything", "")).toBe(true);
		expect(fuzzyMatch("anything", "   ")).toBe(true);
	});

	it("matches an in-order subsequence case-insensitively", () => {
		expect(fuzzyMatch("Toggle Theme", "tgh")).toBe(true);
		expect(fuzzyMatch("Toggle Theme", "THEME")).toBe(true);
		expect(fuzzyMatch("Toggle Theme", "toggle theme")).toBe(true);
	});

	it("rejects characters that are out of order or absent", () => {
		expect(fuzzyMatch("Toggle Theme", "hh")).toBe(false);
		expect(fuzzyMatch("Toggle Theme", "xyz")).toBe(false);
		// characters present but not in order
		expect(fuzzyMatch("abc", "ca")).toBe(false);
	});
});

describe("CommandPaletteStore", () => {
	it("starts closed with an empty query", () => {
		const store = new CommandPaletteStore();
		expect(store.open).toBe(false);
		expect(store.query).toBe("");
	});

	it("openPalette resets the query and opens", () => {
		const store = new CommandPaletteStore();
		store.query = "stale";
		store.openPalette();
		expect(store.open).toBe(true);
		expect(store.query).toBe("");
	});

	it("close closes the palette", () => {
		const store = new CommandPaletteStore();
		store.openPalette();
		store.close();
		expect(store.open).toBe(false);
	});

	it("toggle opens when closed and closes when open", () => {
		const store = new CommandPaletteStore();
		store.query = "leftover";
		store.toggle();
		expect(store.open).toBe(true);
		// opening via toggle resets the query
		expect(store.query).toBe("");
		store.toggle();
		expect(store.open).toBe(false);
	});

	it("filter narrows commands using the fuzzy query", () => {
		const store = new CommandPaletteStore();
		const commands = [
			command("theme", "Toggle Theme"),
			command("refresh", "Refresh Snapshot"),
			command("dismiss", "Dismiss All"),
		];

		store.query = "";
		expect(store.filter(commands)).toHaveLength(3);

		store.query = "refresh";
		expect(store.filter(commands).map((c) => c.id)).toEqual(["refresh"]);

		store.query = "zz";
		expect(store.filter(commands)).toHaveLength(0);
	});
});
