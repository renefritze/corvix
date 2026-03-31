import type { DashboardSummary } from "../types";

interface ToolbarProps {
	dashboardNames: string[];
	currentDashboard: string | null;
	onDashboardChange: (name: string) => void;
	onRefresh: () => void;
	refreshing: boolean;
	summary: DashboardSummary | null;
}

export function Toolbar({
	dashboardNames,
	currentDashboard,
	onDashboardChange,
	onRefresh,
	refreshing,
	summary,
}: ToolbarProps) {
	return (
		<div class="toolbar-row">
			<span class="app-name">Corvix</span>
			{summary && (
				<span class="inline-stats">
					{summary.unread_items + summary.read_items} notifications ·{" "}
					{summary.unread_items} unread · {summary.repository_count} repos
				</span>
			)}
			<div class="toolbar-right">
				{dashboardNames.length > 1 && (
					<select
						value={currentDashboard ?? ""}
						onChange={(e) =>
							onDashboardChange((e.target as HTMLSelectElement).value)
						}
						aria-label="Select dashboard"
					>
						{dashboardNames.map((name) => (
							<option key={name} value={name}>
								{name}
							</option>
						))}
					</select>
				)}
				<button
					type="button"
					class={`refresh-btn${refreshing ? " refreshing" : ""}`}
					onClick={onRefresh}
					aria-label="Refresh"
					disabled={refreshing}
				>
					{refreshing ? "↻ Refreshing" : "↻ Refresh"}
				</button>
			</div>
		</div>
	);
}
