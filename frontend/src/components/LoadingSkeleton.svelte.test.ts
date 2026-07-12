import { render, screen } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";
import LoadingSkeleton from "./LoadingSkeleton.svelte";

describe("LoadingSkeleton", () => {
	it("renders a labelled table placeholder with exactly nine body rows", () => {
		render(LoadingSkeleton);
		expect(
			screen.getByRole("table", { name: "Loading notifications" }),
		).toBeInTheDocument();
		expect(document.querySelectorAll("tbody tr")).toHaveLength(9);
	});
});
