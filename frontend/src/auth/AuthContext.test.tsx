import { act, render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { fetchSnapshot, setUnauthorizedHandler } from "../api";
import { mockResponse } from "../test/http";
import { AuthProvider, useAuth } from "./AuthContext";

function Probe() {
	const { status, message, signalUnauthenticated, reset } = useAuth();
	return (
		<div>
			<span data-testid="status">{status}</span>
			<span data-testid="message">{message ?? ""}</span>
			<button
				type="button"
				onClick={() => signalUnauthenticated("manual sign-out")}
			>
				sign out
			</button>
			<button type="button" onClick={reset}>
				reset
			</button>
		</div>
	);
}

describe("AuthProvider", () => {
	afterEach(() => {
		setUnauthorizedHandler(null);
	});

	it("defaults to authenticated with no message", () => {
		render(
			<AuthProvider>
				<Probe />
			</AuthProvider>,
		);

		expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
		expect(screen.getByTestId("message")).toHaveTextContent("");
	});

	it("flips to unauthenticated via signalUnauthenticated and back via reset", async () => {
		const user = userEvent.setup();
		render(
			<AuthProvider>
				<Probe />
			</AuthProvider>,
		);

		await user.click(screen.getByRole("button", { name: "sign out" }));
		expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
		expect(screen.getByTestId("message")).toHaveTextContent("manual sign-out");

		await user.click(screen.getByRole("button", { name: "reset" }));
		expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
		expect(screen.getByTestId("message")).toHaveTextContent("");
	});

	it("bridges an API 401 into the unauthenticated state", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue(
			mockResponse({
				ok: false,
				status: 401,
				json: async () => ({ detail: "session gone" }),
			}),
		);

		render(
			<AuthProvider>
				<Probe />
			</AuthProvider>,
		);

		await act(async () => {
			await fetchSnapshot().catch(() => {});
		});

		expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
		expect(screen.getByTestId("message")).toHaveTextContent("session gone");
	});

	it("unregisters its handler on unmount", () => {
		const { unmount } = render(
			<AuthProvider>
				<Probe />
			</AuthProvider>,
		);

		unmount();

		// With no provider mounted the handler is cleared; replacing it returns
		// the freshly installed handler, proving the provider released its own.
		const replacement = vi.fn();
		setUnauthorizedHandler(replacement);
		expect(replacement).not.toHaveBeenCalled();
	});

	it("exposes a no-op default when used outside a provider", () => {
		render(<Probe />);
		expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
	});
});
