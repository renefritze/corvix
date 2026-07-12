<script lang="ts">
	import type { Snippet } from "svelte";
	import { DEFAULT_UNAUTHORIZED_MESSAGE } from "../api";
	import { authContext } from "../lib/context";
	import CenteredNotice from "./CenteredNotice.svelte";

	let { children }: { children: Snippet } = $props();
	const auth = authContext.get();
</script>

{#if auth.status === "authenticated"}
	{@render children()}
{:else}
	<div class="app-shell" data-testid="app-shell">
		<main>
			<CenteredNotice
				variant="error"
				role="alert"
				title="Sign in required"
				body={auth.message ?? DEFAULT_UNAUTHORIZED_MESSAGE}
			>
				<button type="button" onclick={() => auth.reset()}>Try again</button>
			</CenteredNotice>
		</main>
	</div>
{/if}

<style>
	.app-shell {
		min-height: 100dvh;
		max-width: 1234px;
		margin-inline: auto;
	}
</style>
