import { render, screen } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";
import { describe, expect, it } from "vitest";
import CenteredNotice from "./CenteredNotice.svelte";

describe("CenteredNotice", () => {
	it("renders title and body via their data-testids with the default testid", () => {
		render(CenteredNotice, { props: { title: "Hello", body: "World" } });
		const notice = screen.getByTestId("empty-state");
		expect(notice).toBeInTheDocument();
		expect(screen.getByTestId("empty-title")).toHaveTextContent("Hello");
		expect(screen.getByTestId("empty-body")).toHaveTextContent("World");
		expect(notice).not.toHaveClass("error");
	});

	it("applies the error variant class", () => {
		render(CenteredNotice, {
			props: { title: "Oops", body: "Broke", variant: "error" },
		});
		expect(screen.getByTestId("empty-state")).toHaveClass("error");
	});

	it("honours a custom testid and role", () => {
		render(CenteredNotice, {
			props: { title: "T", body: "B", testid: "custom-notice", role: "alert" },
		});
		const notice = screen.getByTestId("custom-notice");
		expect(notice).toBeInTheDocument();
		expect(notice).toHaveAttribute("role", "alert");
	});

	it("renders no actions container when no children are supplied", () => {
		const { container } = render(CenteredNotice, {
			props: { title: "T", body: "B" },
		});
		expect(container.querySelector(".actions")).toBeNull();
	});

	it("renders children inside the actions container", () => {
		const children = createRawSnippet(() => ({
			render: () => `<button type="button">Do it</button>`,
		}));
		const { container } = render(CenteredNotice, {
			props: { title: "T", body: "B", children },
		});
		const actions = container.querySelector(".actions");
		expect(actions).not.toBeNull();
		expect(screen.getByRole("button", { name: "Do it" })).toBeInTheDocument();
	});
});
