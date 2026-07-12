import { render } from "@testing-library/svelte";
import type { Component } from "svelte";
import { authContext, routerContext, themeContext } from "../lib/context";
import type { AuthStore } from "../lib/auth.svelte";
import type { Router } from "../lib/router.svelte";
import type { ThemeStore } from "../lib/theme.svelte";

interface Stores {
	router?: Router;
	theme?: ThemeStore;
	auth?: AuthStore;
}

/**
 * Renders a context-dependent component with injected store instances, mirroring
 * how `App.svelte` provides them via `setContext` — used for components that
 * call `routerContext.get()` / `themeContext.get()` / `authContext.get()`.
 */
export function renderWithStores<Props extends Record<string, unknown>>(
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	component: Component<any>,
	props: Props,
	stores: Stores = {},
) {
	const context = new Map<symbol, unknown>();
	if (stores.router) context.set(routerContext.key, stores.router);
	if (stores.theme) context.set(themeContext.key, stores.theme);
	if (stores.auth) context.set(authContext.key, stores.auth);
	return render(component, { props, context });
}
