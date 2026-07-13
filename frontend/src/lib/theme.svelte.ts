/**
 * Theme store: light / dark / system with the resolved theme mirrored onto
 * `documentElement.dataset.theme` (the inline bootstrap in index.html sets the
 * initial value before paint). The explicit preference persists to
 * `localStorage["corvix.theme"]`; "system" removes the key so the bootstrap
 * falls back to `prefers-color-scheme`.
 */

export type ThemePreference = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "corvix.theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

function readStoredPreference(): ThemePreference {
	try {
		const stored = globalThis.localStorage?.getItem(STORAGE_KEY);
		if (stored === "light" || stored === "dark") return stored;
	} catch {
		// localStorage may be unavailable; fall back to system.
	}
	return "system";
}

function systemPrefersDark(): boolean {
	return globalThis.matchMedia?.(DARK_QUERY).matches ?? false;
}

export class ThemeStore {
	preference = $state<ThemePreference>("system");
	#systemDark = $state(false);
	#cleanup: (() => void) | null = null;

	constructor() {
		this.preference = readStoredPreference();
		this.#systemDark = systemPrefersDark();

		const media = globalThis.matchMedia?.(DARK_QUERY);
		if (media) {
			const onChange = (event: MediaQueryListEvent) => {
				this.#systemDark = event.matches;
				this.#apply();
			};
			media.addEventListener("change", onChange);
			this.#cleanup = () => media.removeEventListener("change", onChange);
		}
		this.#apply();
	}

	get resolved(): ResolvedTheme {
		if (this.preference === "system") {
			return this.#systemDark ? "dark" : "light";
		}
		return this.preference;
	}

	#apply(): void {
		if (globalThis.document !== undefined) {
			globalThis.document.documentElement.dataset.theme = this.resolved;
		}
	}

	setPreference(preference: ThemePreference): void {
		this.preference = preference;
		try {
			if (preference === "system") {
				globalThis.localStorage?.removeItem(STORAGE_KEY);
			} else {
				globalThis.localStorage?.setItem(STORAGE_KEY, preference);
			}
		} catch {
			// Ignore storage write failures.
		}
		this.#apply();
	}

	/** Toggle between the two concrete themes (used by the toolbar toggle). */
	toggle(): void {
		this.setPreference(this.resolved === "dark" ? "light" : "dark");
	}

	/** Cycle system → light → dark → system (used by the command palette). */
	cycle(): void {
		const order: ThemePreference[] = ["system", "light", "dark"];
		const next = order[(order.indexOf(this.preference) + 1) % order.length];
		this.setPreference(next);
	}

	destroy(): void {
		this.#cleanup?.();
		this.#cleanup = null;
	}
}
