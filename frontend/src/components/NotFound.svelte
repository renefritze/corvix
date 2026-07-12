<script lang="ts">
	import { routerContext } from "../lib/context";
	import CenteredNotice from "./CenteredNotice.svelte";

	let { url }: { url?: string } = $props();
	const router = routerContext.get();
</script>

<CenteredNotice
	variant="error"
	title="Page not found"
	body={url ? `No page matches ${url}.` : "This page doesn't exist."}
>
	<button type="button" onclick={() => router.navigate("/", true)}>
		Back to dashboard
	</button>
</CenteredNotice>
