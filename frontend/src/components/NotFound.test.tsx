import { render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { Router } from "preact-router";
import { setPath } from "../test/http";
import { NotFound } from "./NotFound";

// A mounted Router keeps preact-router's route() wired to history; NotFound is
// rendered as the matched (default) child so its back-link can navigate.
function Mounted({ url }: { readonly url?: string }) {
	return (
		<Router>
			<NotFoundRoute default url={url} />
		</Router>
	);
}

// Thin wrapper so the extra router-only `default` prop stays off NotFound.
function NotFoundRoute({
	url,
}: { readonly url?: string; readonly default?: boolean }) {
	return <NotFound url={url} />;
}

describe("NotFound", () => {
	it("renders the 404 message and the offending url", () => {
		render(<NotFound url="/nope" />);

		expect(screen.getByText("Page not found")).toBeInTheDocument();
		expect(screen.getByText("No page matches /nope.")).toBeInTheDocument();
	});

	it("navigates back to the default dashboard via the link", async () => {
		setPath("/totally/unknown");
		const user = userEvent.setup();
		render(<Mounted url="/totally/unknown" />);

		await user.click(screen.getByRole("button", { name: "Back to dashboard" }));

		expect(globalThis.location.pathname).toBe("/");
	});
});
