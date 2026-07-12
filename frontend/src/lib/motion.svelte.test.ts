import { describe, expect, it } from "vitest";
import { prefersReducedMotion } from "./motion.svelte";

describe("prefersReducedMotion", () => {
	it("returns a boolean, false under the mocked matchMedia", () => {
		const value = prefersReducedMotion();
		expect(typeof value).toBe("boolean");
		expect(value).toBe(false);
	});
});
