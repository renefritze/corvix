<script lang="ts">
	import { onDestroy } from "svelte";
	import AuthGate from "./components/AuthGate.svelte";
	import CenteredNotice from "./components/CenteredNotice.svelte";
	import Dashboard from "./components/Dashboard.svelte";
	import NotFound from "./components/NotFound.svelte";
	import { AuthStore } from "./lib/auth.svelte";
	import { authContext, routerContext, themeContext } from "./lib/context";
	import { Router } from "./lib/router.svelte";
	import { ThemeStore } from "./lib/theme.svelte";

	const router = routerContext.set(new Router());
	const theme = themeContext.set(new ThemeStore());
	const auth = authContext.set(new AuthStore());

	onDestroy(() => {
		router.destroy();
		theme.destroy();
		auth.destroy();
	});
</script>

<svelte:boundary>
	<AuthGate>
		{#if router.route.matched}
			<Dashboard />
		{:else}
			<NotFound url={router.relativeUrl} />
		{/if}
	</AuthGate>

	{#snippet failed(error, reset)}
		<div class="app-shell" data-testid="app-shell">
			<CenteredNotice
				variant="error"
				role="alert"
				title="Something went wrong"
				body={error instanceof Error ? error.message : String(error)}
			>
				<button type="button" onclick={reset}>Try again</button>
			</CenteredNotice>
		</div>
	{/snippet}
</svelte:boundary>

<style>
	.app-shell {
		min-height: 100dvh;
		max-width: 1234px;
		margin-inline: auto;
	}
</style>
