import { flushSync } from "svelte";

/**
 * Runs `fn` inside an `$effect.root` so stores that register `$effect`s in
 * `bind()` can be exercised from plain `.test.ts` files. Returns the value `fn`
 * produced plus a `dispose` that tears the root (and its effects) down.
 * Pending effects flush synchronously via {@link flushSync}.
 */
export function root<T>(fn: () => T): { value: T; dispose: () => void } {
	let value!: T;
	const dispose = $effect.root(() => {
		value = fn();
	});
	flushSync();
	return { value, dispose };
}

export { flushSync };
