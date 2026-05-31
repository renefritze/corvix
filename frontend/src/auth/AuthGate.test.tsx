import { render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { setUnauthorizedHandler } from "../api";
import { AuthGate } from "./AuthGate";
import { AuthProvider, useAuth } from "./AuthContext";

function SignOutButton() {
	const { signalUnauthenticated } = useAuth();
	return (
		<button type="button" onClick={() => signalUnauthenticated("please sign in")}>
			trigger
		</button>
	);
}

describe("AuthGate", () => {
	afterEach(() => {
		setUnauthorizedHandler(null);
	});

	it("renders children while authenticated", () => {
		render(
			<AuthProvider>
				<AuthGate>
					<p>protected content</p>
				</AuthGate>
			</AuthProvider>,
		);

		expect(screen.getByText("protected content")).toBeInTheDocument();
		expect(screen.queryByText("Sign in required")).not.toBeInTheDocument();
	});

	it("shows the login UI with the message once unauthenticated", async () => {
		const user = userEvent.setup();
		render(
			<AuthProvider>
				<SignOutButton />
				<AuthGate>
					<p>protected content</p>
				</AuthGate>
			</AuthProvider>,
		);

		await user.click(screen.getByRole("button", { name: "trigger" }));

		expect(screen.getByText("Sign in required")).toBeInTheDocument();
		expect(screen.getByText("please sign in")).toBeInTheDocument();
		expect(screen.queryByText("protected content")).not.toBeInTheDocument();
		expect(screen.getByRole("alert")).toBeInTheDocument();
	});

	it("returns to the children when Try again is clicked", async () => {
		const user = userEvent.setup();
		render(
			<AuthProvider>
				<SignOutButton />
				<AuthGate>
					<p>protected content</p>
				</AuthGate>
			</AuthProvider>,
		);

		await user.click(screen.getByRole("button", { name: "trigger" }));
		expect(screen.queryByText("protected content")).not.toBeInTheDocument();

		await user.click(screen.getByRole("button", { name: "Try again" }));
		expect(screen.getByText("protected content")).toBeInTheDocument();
	});

	it("falls back to a default message when none is provided", async () => {
		const user = userEvent.setup();
		function ForceLogout() {
			const { signalUnauthenticated } = useAuth();
			return (
				<button type="button" onClick={() => signalUnauthenticated()}>
					logout
				</button>
			);
		}
		render(
			<AuthProvider>
				<ForceLogout />
				<AuthGate>
					<p>protected content</p>
				</AuthGate>
			</AuthProvider>,
		);

		await user.click(screen.getByRole("button", { name: "logout" }));

		expect(
			screen.getByText("Your session has expired or you are not signed in."),
		).toBeInTheDocument();
	});
});
