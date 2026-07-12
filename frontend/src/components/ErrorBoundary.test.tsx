import { render, screen } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { ErrorBoundary } from "./ErrorBoundary";

function Bomb({ shouldThrow }: { readonly shouldThrow: boolean }) {
	if (shouldThrow) {
		throw new Error("render failed");
	}
	return <div>safe content</div>;
}

describe("ErrorBoundary", () => {
	beforeEach(() => {
		vi.spyOn(console, "error").mockReturnValue(undefined);
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("renders children when no error occurs", () => {
		render(
			<ErrorBoundary>
				<Bomb shouldThrow={false} />
			</ErrorBoundary>,
		);
		expect(screen.getByText("safe content")).toBeInTheDocument();
	});

	it("shows fallback when a child throws during render", () => {
		render(
			<ErrorBoundary>
				<Bomb shouldThrow={true} />
			</ErrorBoundary>,
		);
		expect(screen.getByText("Something went wrong")).toBeInTheDocument();
		expect(screen.getByText("render failed")).toBeInTheDocument();
		expect(
			screen.getByRole("button", { name: "Try again" }),
		).toBeInTheDocument();
	});

	it("resets error state when Try again is clicked", async () => {
		const user = userEvent.setup();
		let shouldThrow = true;

		function ControlledBomb() {
			return <Bomb shouldThrow={shouldThrow} />;
		}

		render(
			<ErrorBoundary>
				<ControlledBomb />
			</ErrorBoundary>,
		);
		expect(screen.getByText("Something went wrong")).toBeInTheDocument();

		shouldThrow = false;
		await user.click(screen.getByRole("button", { name: "Try again" }));

		expect(screen.getByText("safe content")).toBeInTheDocument();
	});

	it("calls onRetry when Try again is clicked", async () => {
		const onRetry = vi.fn();
		const user = userEvent.setup();
		render(
			<ErrorBoundary onRetry={onRetry}>
				<Bomb shouldThrow={true} />
			</ErrorBoundary>,
		);

		await user.click(screen.getByRole("button", { name: "Try again" }));
		expect(onRetry).toHaveBeenCalledTimes(1);
	});

	it("handles non-Error thrown values gracefully without crashing", () => {
		function NonErrorBomb() {
			const thrown: unknown = { code: 404 };
			throw thrown;
		}
		render(
			<ErrorBoundary>
				<NonErrorBomb />
			</ErrorBoundary>,
		);
		expect(screen.getByText("Something went wrong")).toBeInTheDocument();
		expect(screen.getByText('{"code":404}')).toBeInTheDocument();
	});
});
