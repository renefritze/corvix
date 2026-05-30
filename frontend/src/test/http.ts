export type FetchInput = string | URL | Request;

/** Normalizes the various `fetch` input shapes to a comparable URL string. */
export function requestUrl(input: FetchInput): string {
	if (typeof input === "string") return input;
	if (input instanceof URL) return input.toString();
	return input.url;
}

/** Pushes a path onto history so components can read it from the location. */
export function setPath(path: string): void {
	globalThis.history.pushState({}, "", path);
}
