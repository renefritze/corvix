import { screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { ThemeStore } from "../lib/theme.svelte";
import { renderWithStores } from "../test/renderWithStores";
import { root } from "../test/runes.svelte";
import ThemeToggle from "./ThemeToggle.svelte";

describe("ThemeToggle", () => {
	let dispose: (() => void) | undefined;
	afterEach(() => {
		dispose?.();
		dispose = undefined;
	});

	function makeTheme() {
		const { value, dispose: d } = root(() => new ThemeStore());
		dispose = d;
		return value;
	}

	it("toggles the theme on click", async () => {
		const theme = makeTheme();
		theme.setPreference("dark");
		renderWithStores(ThemeToggle, {}, { theme });
		expect(screen.getByRole("button", { name: /Switch to light theme/ })).toBeInTheDocument();
		await userEvent.click(screen.getByRole("button"));
		expect(theme.resolved).toBe("light");
	});
});
