import { screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Router } from "../lib/router.svelte";
import { renderWithStores } from "../test/renderWithStores";

import NotFound from "./NotFound.svelte";

describe("NotFound", () => {
	it("renders the 404 message including the offending url", () => {
		const router = new Router();
		renderWithStores(NotFound, { url: "/nope" }, { router });
		expect(screen.getByText("Page not found")).toBeInTheDocument();
		expect(screen.getByText("No page matches /nope.")).toBeInTheDocument();
	});

	it("falls back to a generic body when no url is provided", () => {
		const router = new Router();
		renderWithStores(NotFound, {}, { router });
		expect(screen.getByText("This page doesn't exist.")).toBeInTheDocument();
	});

	it("navigates back to the default dashboard via the back button", async () => {
		const router = new Router();
		const navigate = vi.spyOn(router, "navigate");
		renderWithStores(NotFound, { url: "/totally/unknown" }, { router });
		await userEvent.click(
			screen.getByRole("button", { name: "Back to dashboard" }),
		);
		expect(navigate).toHaveBeenCalledWith("/", true);
	});
});
