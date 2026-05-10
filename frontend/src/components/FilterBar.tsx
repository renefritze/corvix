import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import type { DashboardItem, FilterState } from "../types";

interface FilterBarProps {
	readonly filters: FilterState;
	readonly includeRead: boolean;
	readonly items: DashboardItem[];
	readonly onFilterChange: <K extends keyof FilterState>(
		key: K,
		value: FilterState[K],
	) => void;
	readonly onClearFilters: () => void;
	readonly generatedAt: string | null;
	readonly filterBarRef?: { current: HTMLSelectElement | null };
}

export function FilterBar({
	filters,
	includeRead,
	items,
	onFilterChange,
	onClearFilters,
	generatedAt,
	filterBarRef,
}: FilterBarProps) {
	const reasonPickerRef = useRef<HTMLDivElement | null>(null);
	const reasonListId = "reason-filter-options";
	const [reasonMenuOpen, setReasonMenuOpen] = useState(false);

	const reasons = Array.from(new Set(items.map((i) => i.reason))).sort((a, b) =>
		a.localeCompare(b),
	);
	const missingReasons = Array.from(
		new Set(filters.reason.filter((reason) => !reasons.includes(reason))),
	);
	const repositories = Array.from(new Set(items.map((i) => i.repository))).sort(
		(a, b) => a.localeCompare(b),
	);
	const selectedRepositoryMissing =
		filters.repository !== "" && !repositories.includes(filters.repository);
	const missingFilterLabel =
		filters.unread === "unread"
			? "no unread notifications"
			: "no matching notifications";
	const selectedRepositoryLabel = `${filters.repository} (${missingFilterLabel})`;
	const selectedReasonSet = useMemo(
		() => new Set(filters.reason),
		[filters.reason],
	);
	const reasonOptions = useMemo(
		() => [
			...missingReasons.map((reason) => ({
				reason,
				label: `${reason} (${missingFilterLabel})`,
				missing: true,
			})),
			...reasons.map((reason) => ({
				reason,
				label: reason,
				missing: false,
			})),
		],
		[missingReasons, missingFilterLabel, reasons],
	);

	useEffect(() => {
		if (!reasonMenuOpen) return;

		const handleClickAway = (event: MouseEvent) => {
			if (!(event.target instanceof Node)) return;
			if (reasonPickerRef.current?.contains(event.target)) return;
			setReasonMenuOpen(false);
		};

		const handleEscape = (event: KeyboardEvent) => {
			if (event.key === "Escape") {
				setReasonMenuOpen(false);
			}
		};

		document.addEventListener("mousedown", handleClickAway);
		document.addEventListener("keydown", handleEscape);
		return () => {
			document.removeEventListener("mousedown", handleClickAway);
			document.removeEventListener("keydown", handleEscape);
		};
	}, [reasonMenuOpen]);

	function toggleReason(reason: string) {
		if (selectedReasonSet.has(reason)) {
			onFilterChange(
				"reason",
				filters.reason.filter((value) => value !== reason),
			);
			return;
		}
		onFilterChange("reason", [...filters.reason, reason]);
	}

	function removeReason(reason: string) {
		onFilterChange(
			"reason",
			filters.reason.filter((value) => value !== reason),
		);
	}

	return (
		<div class="filter-row">
			<select
				ref={filterBarRef}
				value={filters.unread}
				onChange={(e) =>
					onFilterChange(
						"unread",
						(e.target as HTMLSelectElement).value as FilterState["unread"],
					)
				}
				aria-label="Unread state filter"
			>
				<option value="all" disabled={!includeRead}>
					{includeRead ? "All" : "🔒 All (disabled by dashboard)"}
				</option>
				<option value="unread">Unread only</option>
				<option value="read" disabled={!includeRead}>
					{includeRead ? "Read only" : "🔒 Read only (disabled by dashboard)"}
				</option>
			</select>
			<div class="reason-picker" ref={reasonPickerRef}>
				<button
					type="button"
					class={`reason-picker-trigger${reasonMenuOpen ? " open" : ""}`}
					aria-label="Reason filter"
					aria-expanded={reasonMenuOpen}
					aria-controls={reasonListId}
					onClick={() => setReasonMenuOpen((open) => !open)}
				>
					{filters.reason.length === 0 && (
						<span class="reason-picker-placeholder">All reasons</span>
					)}
					{filters.reason.length > 0 && filters.reason.length <= 2 && (
						<span class="reason-chip-list">
							{filters.reason.map((reason) => (
								<span class="reason-chip" key={reason}>
									<span class="reason-chip-text">{reason}</span>
									<button
										type="button"
										class="reason-chip-remove"
										aria-label={`Remove ${reason} reason filter`}
										onClick={(event) => {
											event.preventDefault();
											event.stopPropagation();
											removeReason(reason);
										}}
									>
										×
									</button>
								</span>
							))}
						</span>
					)}
					{filters.reason.length > 2 && (
						<span class="reason-picker-summary">
							{filters.reason.length} reasons
						</span>
					)}
					<span class="reason-picker-caret" aria-hidden="true">
						▾
					</span>
				</button>
				{reasonMenuOpen && (
					<div id={reasonListId} class="reason-picker-menu" role="group">
						{reasonOptions.map((option) => (
							<button
								type="button"
								class={[
									"reason-option",
									selectedReasonSet.has(option.reason) ? "selected" : "",
									option.missing ? "missing" : "",
								]
									.filter(Boolean)
									.join(" ")}
								onClick={() => toggleReason(option.reason)}
								key={option.reason}
							>
								<span class="reason-option-check" aria-hidden="true">
									{selectedReasonSet.has(option.reason) ? "✓" : ""}
								</span>
								<span class="reason-option-label">{option.label}</span>
							</button>
						))}
					</div>
				)}
			</div>
			<select
				value={filters.repository}
				onChange={(e) =>
					onFilterChange("repository", (e.target as HTMLSelectElement).value)
				}
				aria-label="Repository filter"
			>
				<option value="">All repositories</option>
				{selectedRepositoryMissing && (
					<option value={filters.repository}>{selectedRepositoryLabel}</option>
				)}
				{repositories.map((r) => (
					<option key={r} value={r}>
						{r}
					</option>
				))}
			</select>
			<button type="button" onClick={onClearFilters}>
				Clear
			</button>
			{generatedAt && (
				<span class="snapshot-time">
					Snapshot: {new Date(generatedAt).toLocaleTimeString()}
				</span>
			)}
		</div>
	);
}
