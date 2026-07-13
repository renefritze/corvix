import { render, screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { prefersReducedMotion } from "../lib/motion.svelte";
import ErrorToast from "./ErrorToast.svelte";

vi.mock("../lib/motion.svelte", () => ({
	prefersReducedMotion: vi.fn(() => false),
}));

// ErrorToast's root element uses Svelte's `fly` transition, which relies on the
// Web Animations API that jsdom lacks; provide a no-op that resolves immediately
// so the intro transition completes instead of throwing.
beforeAll(() => {
	if (typeof Element.prototype.animate !== "function") {
		Element.prototype.animate = function () {
			return {
				cancel: () => {},
				finished: Promise.resolve(),
				onfinish: null,
				play: () => {},
				pause: () => {},
				currentTime: 0,
				playState: "finished",
				addEventListener: () => {},
				removeEventListener: () => {},
			} as unknown as Animation;
		};
	}
});

describe("ErrorToast", () => {
	it("renders the message inside an alert", () => {
		render(ErrorToast, {
			props: { message: "Something failed", onDismiss: vi.fn() },
		});
		const alert = screen.getByRole("alert");
		expect(alert).toHaveTextContent("Something failed");
	});

	it("fires onDismiss from the dismiss button", async () => {
		const onDismiss = vi.fn();
		render(ErrorToast, { props: { message: "boom", onDismiss } });
		await userEvent.click(screen.getByRole("button", { name: "Dismiss error" }));
		expect(onDismiss).toHaveBeenCalledTimes(1);
	});

	it("renders without animation when reduced motion is preferred", () => {
		vi.mocked(prefersReducedMotion).mockReturnValue(true);
		render(ErrorToast, { props: { message: "quiet", onDismiss: vi.fn() } });
		expect(screen.getByRole("alert")).toHaveTextContent("quiet");
	});
});
