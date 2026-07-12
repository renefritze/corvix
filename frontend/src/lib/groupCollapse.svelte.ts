/**
 * Collapsible groups (new in the rewrite): tracks collapsed group names per
 * dashboard, backed by sessionStorage so the state survives a soft reload but
 * not a new session. Keyed `corvix.groups.collapsed.<dashboard>`.
 */

const STORAGE_PREFIX = "corvix.groups.collapsed.";

function storageKey(dashboard: string | null): string {
	return `${STORAGE_PREFIX}${dashboard ?? ""}`;
}

function loadCollapsed(dashboard: string | null): Set<string> {
	try {
		const raw = globalThis.sessionStorage?.getItem(storageKey(dashboard));
		if (!raw) return new Set();
		const parsed = JSON.parse(raw) as unknown;
		if (Array.isArray(parsed)) {
			return new Set(parsed.filter((v): v is string => typeof v === "string"));
		}
	} catch {
		// Ignore malformed/unavailable storage.
	}
	return new Set();
}

export class GroupCollapseStore {
	// Reassigned on every mutation so reads stay reactive.
	#collapsed = $state<Set<string>>(new Set());
	#dashboard: string | null = null;

	/** Point the store at a dashboard, loading its persisted collapsed set. */
	setDashboard(dashboard: string | null): void {
		if (dashboard === this.#dashboard) return;
		this.#dashboard = dashboard;
		this.#collapsed = loadCollapsed(dashboard);
	}

	isCollapsed(name: string): boolean {
		return this.#collapsed.has(name);
	}

	toggle = (name: string): void => {
		const next = new Set(this.#collapsed);
		if (next.has(name)) {
			next.delete(name);
		} else {
			next.add(name);
		}
		this.#collapsed = next;
		this.#persist();
	};

	#persist(): void {
		try {
			globalThis.sessionStorage?.setItem(
				storageKey(this.#dashboard),
				JSON.stringify([...this.#collapsed]),
			);
		} catch {
			// Ignore storage write failures.
		}
	}
}
