import { render, screen } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";
import App from "./App.svelte";

describe("App", () => {
	it("renders the Corvix brand", () => {
		render(App);
		expect(screen.getByTestId("app-name")).toHaveTextContent("Corvix");
	});
});
