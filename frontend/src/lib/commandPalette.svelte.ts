/**
 * Command palette (new in the rewrite): open/close state and the fuzzy query.
 * The command list is assembled by the Dashboard and passed to the
 * CommandPalette component; this store only owns UI state plus the fuzzy match
 * helper so both the store and component can share one implementation.
 */

export interface Command {
	id: string;
	label: string;
	hint?: string;
	run: () => void;
}

/**
 * Simple subsequence fuzzy match: every character of `query` must appear in
 * `text` in order (case-insensitive). Empty query matches everything.
 */
export function fuzzyMatch(text: string, query: string): boolean {
	const needle = query.trim().toLowerCase();
	if (!needle) return true;
	const haystack = text.toLowerCase();
	let i = 0;
	for (const char of haystack) {
		if (char === needle[i]) {
			i++;
			if (i === needle.length) return true;
		}
	}
	return i === needle.length;
}

export class CommandPaletteStore {
	open = $state(false);
	query = $state("");

	openPalette = (): void => {
		this.query = "";
		this.open = true;
	};

	close = (): void => {
		this.open = false;
	};

	toggle = (): void => {
		if (this.open) {
			this.close();
		} else {
			this.openPalette();
		}
	};

	filter(commands: Command[]): Command[] {
		return commands.filter((command) => fuzzyMatch(command.label, this.query));
	}
}
