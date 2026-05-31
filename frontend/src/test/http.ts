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

/** The subset of `Response` fields the API layer actually reads in tests. */
interface ResponseStub {
	ok: boolean;
	status?: number;
	json?: () => Promise<unknown>;
}

/**
 * Builds a minimal `Response` stub for mocking `fetch`. Only the fields the API
 * layer reads are provided; the double assertion widens the partial literal to
 * `Response` in one place so individual tests don't repeat a bare `as Response`
 * cast (which the type checker requires but which the linter flags as
 * redundant).
 */
export function mockResponse(init: ResponseStub): Response {
	return init as unknown as Response;
}
