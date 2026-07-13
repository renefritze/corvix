/**
 * Global `prefers-reduced-motion` kill-switch for Svelte JS transitions (CSS
 * transitions are separately neutralized in app.css). Reactive so a runtime
 * preference change flips motion off/on without a reload.
 *
 * The media listener is wired at module load and only ever mutates `reduced`
 * from its (async) change handler — never from within a derived/template — so
 * reading `prefersReducedMotion()` inside a `$derived` is safe.
 */
const MEDIA_QUERY = "(prefers-reduced-motion: reduce)";
const media = globalThis.matchMedia?.(MEDIA_QUERY);

let reduced = $state(media?.matches ?? false);

media?.addEventListener("change", (event) => {
	reduced = event.matches;
});

export function prefersReducedMotion(): boolean {
	return reduced;
}
