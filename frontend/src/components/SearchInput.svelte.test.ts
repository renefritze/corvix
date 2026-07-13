import { render, screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import SearchInput from "./SearchInput.svelte";

describe("SearchInput", () => {
	it("renders the labelled search input with the current value", () => {
		render(SearchInput, { props: { value: "hello", onChange: vi.fn() } });
		const input = screen.getByLabelText("Search notifications") as HTMLInputElement;
		expect(input).toBeInTheDocument();
		expect(input).toHaveValue("hello");
		expect(input.hasAttribute("data-search-input")).toBe(true);
	});

	it("calls onChange with the typed value", async () => {
		const onChange = vi.fn();
		render(SearchInput, { props: { value: "", onChange } });
		await userEvent.type(screen.getByLabelText("Search notifications"), "ab");
		// The value prop stays "" (controlled by the parent), so the uncontrolled
		// DOM input accumulates characters and reports the running value each time.
		expect(onChange).toHaveBeenCalledTimes(2);
		expect(onChange).toHaveBeenNthCalledWith(1, "a");
		expect(onChange).toHaveBeenNthCalledWith(2, "ab");
	});
});
