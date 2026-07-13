import { render, screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import RowContextMenu from "./RowContextMenu.svelte";

describe("RowContextMenu", () => {
	it("renders a menu positioned by the x/y props", () => {
		render(RowContextMenu, {
			props: { x: 120, y: 40, onCreateRule: vi.fn() },
		});
		const menu = screen.getByRole("menu");
		expect(menu).toHaveStyle({ left: "120px", top: "40px" });
	});

	it("fires onCreateRule from the create-ignore-rule menu item", async () => {
		const onCreateRule = vi.fn();
		render(RowContextMenu, { props: { x: 0, y: 0, onCreateRule } });
		await userEvent.click(
			screen.getByRole("menuitem", { name: "Create ignore rule..." }),
		);
		expect(onCreateRule).toHaveBeenCalledTimes(1);
	});
});
