/**
 * Sort state with the URL query string as the source of truth, ported from
 * `useSort.ts`. An explicit `sort`/`dir` query overrides the dashboard's
 * configured order, which is supplied lazily via seed getters so it can track a
 * changing snapshot.
 */
import type { Router } from "./router.svelte";
import type { SortColumn, SortDirection } from "../types";

const SORT_COLUMNS: ReadonlySet<SortColumn> = new Set([
	"subject_title",
	"repository",
	"subject_type",
	"reason",
	"updated_at",
	"score",
]);

function readColumnFromUrl(router: Router): SortColumn | undefined {
	const sort = router.query.get("sort");
	return SORT_COLUMNS.has(sort as SortColumn)
		? (sort as SortColumn)
		: undefined;
}

function readDirectionFromUrl(router: Router): SortDirection | undefined {
	const dir = router.query.get("dir");
	return dir === "asc" || dir === "desc" ? dir : undefined;
}

export class SortStore {
	readonly #router: Router;
	readonly #seedColumn: () => SortColumn;
	readonly #seedDir: () => SortDirection;

	constructor(
		router: Router,
		seedColumn: () => SortColumn = () => "score",
		seedDir: () => SortDirection = () => "desc",
	) {
		this.#router = router;
		this.#seedColumn = seedColumn;
		this.#seedDir = seedDir;
	}

	get sortColumn(): SortColumn {
		return readColumnFromUrl(this.#router) ?? this.#seedColumn();
	}

	get sortDirection(): SortDirection {
		return readDirectionFromUrl(this.#router) ?? this.#seedDir();
	}

	handleSort = (col: SortColumn): void => {
		const toggled = this.sortDirection === "asc" ? "desc" : "asc";
		const nextDir = col === this.sortColumn ? toggled : "desc";
		this.#router.updateQuery({ sort: col, dir: nextDir });
	};
}
