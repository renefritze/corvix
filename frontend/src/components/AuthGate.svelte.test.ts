import { screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { createRawSnippet } from "svelte";
import { afterEach, describe, expect, it } from "vitest";
import { AuthStore } from "../lib/auth.svelte";
import { renderWithStores } from "../test/renderWithStores";
import { root } from "../test/runes.svelte";
import AuthGate from "./AuthGate.svelte";

let dispose: (() => void) | undefined;

afterEach(() => {
	dispose?.();
	dispose = undefined;
});

function makeAuth() {
	const { value, dispose: d } = root(() => new AuthStore());
	dispose = d;
	return value;
}

const children = createRawSnippet(() => ({
	render: () => "<span>kids</span>",
}));

describe("AuthGate", () => {
	it("renders children when authenticated", () => {
		const auth = makeAuth();
		renderWithStores(AuthGate, { children }, { auth });
		expect(screen.getByText("kids")).toBeInTheDocument();
		expect(screen.queryByText("Sign in required")).toBeNull();
	});

	it("shows the sign-in notice when unauthenticated", () => {
		const auth = makeAuth();
		auth.signalUnauthenticated("please sign in");
		renderWithStores(AuthGate, { children }, { auth });
		expect(screen.getByText("Sign in required")).toBeInTheDocument();
		expect(screen.getByText("please sign in")).toBeInTheDocument();
		expect(screen.queryByText("kids")).toBeNull();
	});

	it("falls back to the default message when none is provided", () => {
		const auth = makeAuth();
		auth.signalUnauthenticated();
		renderWithStores(AuthGate, { children }, { auth });
		expect(screen.getByText("Sign in required")).toBeInTheDocument();
		expect(screen.getByRole("alert")).toBeInTheDocument();
	});

	it("resets auth when Try again is clicked", async () => {
		const auth = makeAuth();
		auth.signalUnauthenticated("nope");
		renderWithStores(AuthGate, { children }, { auth });
		await userEvent.click(screen.getByRole("button", { name: "Try again" }));
		expect(auth.status).toBe("authenticated");
	});
});
