import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { root } from "../test/runes.svelte";
import { KeyboardStore, type KeyboardOptions } from "./keyboard.svelte";

describe("KeyboardStore", () => {
	let dispose: (() => void) | undefined;

	function makeOptions(): { [K in keyof KeyboardOptions]: Mock<() => void> } {
		return {
			onRefresh: vi.fn<() => void>(),
			onFocusFilters: vi.fn<() => void>(),
			onDismissFocused: vi.fn<() => void>(),
			onToggleShortcuts: vi.fn<() => void>(),
			onCommandPalette: vi.fn<() => void>(),
			onFocusSearch: vi.fn<() => void>(),
		};
	}

	function make(options: KeyboardOptions) {
		const { value, dispose: d } = root(() => {
			const s = new KeyboardStore(options);
			s.bind();
			return s;
		});
		dispose = d;
		return value;
	}

	function press(
		key: string,
		init: KeyboardEventInit = {},
		target: EventTarget = document,
	): KeyboardEvent {
		const event = new KeyboardEvent("keydown", {
			key,
			bubbles: true,
			cancelable: true,
			...init,
		});
		target.dispatchEvent(event);
		return event;
	}

	function buildTable(): { rows: HTMLTableRowElement[]; link: HTMLAnchorElement } {
		document.body.innerHTML = `
			<input aria-label="search" />
			<table>
				<tbody>
					<tr data-thread-id="1" tabindex="0" id="row-1">
						<td data-label="Title"><a href="#a">Row 1</a></td>
					</tr>
					<tr data-thread-id="2" tabindex="0" id="row-2">
						<td data-label="Title"><a href="#b">Row 2</a></td>
					</tr>
				</tbody>
			</table>
		`;
		const rows = Array.from(
			document.querySelectorAll<HTMLTableRowElement>("tr[data-thread-id]"),
		);
		const link = document.querySelector<HTMLAnchorElement>(
			"#row-1 a",
		) as HTMLAnchorElement;
		return { rows, link };
	}

	beforeEach(() => {
		document.body.innerHTML = "";
	});

	afterEach(() => {
		dispose?.();
		dispose = undefined;
		document.body.innerHTML = "";
	});

	it("invokes the right callback for r/f/d/?// keys", () => {
		const opts = makeOptions();
		make(opts);

		press("r");
		expect(opts.onRefresh).toHaveBeenCalledTimes(1);

		press("f");
		expect(opts.onFocusFilters).toHaveBeenCalledTimes(1);

		press("d");
		expect(opts.onDismissFocused).toHaveBeenCalledTimes(1);

		press("?");
		expect(opts.onToggleShortcuts).toHaveBeenCalledTimes(1);

		press("/");
		expect(opts.onFocusSearch).toHaveBeenCalledTimes(1);
	});

	it("uppercase key variants still trigger (R)", () => {
		const opts = makeOptions();
		make(opts);
		press("R");
		expect(opts.onRefresh).toHaveBeenCalledTimes(1);
	});

	it("prevents default for handled shortcut keys", () => {
		const opts = makeOptions();
		make(opts);
		const event = press("r");
		expect(event.defaultPrevented).toBe(true);
	});

	it("opens the command palette on Cmd/Ctrl+K", () => {
		const opts = makeOptions();
		make(opts);

		const meta = press("k", { metaKey: true });
		expect(opts.onCommandPalette).toHaveBeenCalledTimes(1);
		expect(meta.defaultPrevented).toBe(true);

		press("K", { ctrlKey: true });
		expect(opts.onCommandPalette).toHaveBeenCalledTimes(2);
	});

	it("opens the command palette even while typing in an input", () => {
		const opts = makeOptions();
		make(opts);
		const input = document.createElement("input");
		document.body.append(input);

		press("k", { ctrlKey: true }, input);
		expect(opts.onCommandPalette).toHaveBeenCalledTimes(1);
	});

	it("suppresses plain shortcuts while typing in an input", () => {
		const opts = makeOptions();
		make(opts);
		const input = document.createElement("input");
		document.body.append(input);

		press("r", {}, input);
		press("f", {}, input);
		press("/", {}, input);
		expect(opts.onRefresh).not.toHaveBeenCalled();
		expect(opts.onFocusFilters).not.toHaveBeenCalled();
		expect(opts.onFocusSearch).not.toHaveBeenCalled();
	});

	it("ignores plain shortcuts when a modifier is held", () => {
		const opts = makeOptions();
		make(opts);
		press("r", { altKey: true });
		expect(opts.onRefresh).not.toHaveBeenCalled();
	});

	it("blurs the active element on Escape", () => {
		const opts = makeOptions();
		make(opts);
		const input = document.createElement("input");
		document.body.append(input);
		input.focus();
		expect(document.activeElement).toBe(input);

		press("Escape", {}, input);
		expect(document.activeElement).not.toBe(input);
	});

	it("moves focus between thread rows with j and k", () => {
		const opts = makeOptions();
		make(opts);
		const { rows } = buildTable();

		// No row focused yet: j focuses the first row.
		press("j");
		expect(document.activeElement).toBe(rows[0]);

		press("j");
		expect(document.activeElement).toBe(rows[1]);

		press("k");
		expect(document.activeElement).toBe(rows[0]);
	});

	it("k from no selection focuses the last row", () => {
		const opts = makeOptions();
		make(opts);
		const { rows } = buildTable();

		press("k");
		expect(document.activeElement).toBe(rows[rows.length - 1]);
	});

	it("j/k are no-ops when there are no rows", () => {
		const opts = makeOptions();
		make(opts);
		expect(() => press("j")).not.toThrow();
		expect(() => press("k")).not.toThrow();
	});

	it("Enter clicks the focused row's title link", () => {
		const opts = makeOptions();
		make(opts);
		const { rows, link } = buildTable();
		const clickSpy = vi.spyOn(link, "click");
		rows[0].focus();

		press("Enter");
		expect(clickSpy).toHaveBeenCalledTimes(1);
	});

	it("Enter is a no-op when no row is focused", () => {
		const opts = makeOptions();
		make(opts);
		buildTable();
		expect(() => press("Enter")).not.toThrow();
	});

	it("removes the keydown listener on dispose", () => {
		const opts = makeOptions();
		make(opts);
		dispose?.();
		dispose = undefined;

		press("r");
		expect(opts.onRefresh).not.toHaveBeenCalled();
	});
});
