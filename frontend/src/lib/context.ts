/**
 * Typed `setContext`/`getContext` accessors for the store instances created in
 * `App.svelte`. Each store gets its own Symbol key so components depend only on
 * what they use, and tests can inject isolated instances via
 * `test/renderWithStores.ts`.
 */
import { getContext, setContext } from "svelte";
import type { AuthStore } from "./auth.svelte";
import type { Router } from "./router.svelte";
import type { ThemeStore } from "./theme.svelte";

function defineContext<T>(name: string) {
	const key = Symbol(name);
	return {
		set: (value: T): T => setContext(key, value),
		get: (): T => getContext(key) as T,
	};
}

export const routerContext = defineContext<Router>("corvix.router");
export const themeContext = defineContext<ThemeStore>("corvix.theme");
export const authContext = defineContext<AuthStore>("corvix.auth");
