import type { NotifPermission } from "../hooks/useBrowserNotifications";
import type { DashboardSummary } from "../types";

interface ToolbarProps {
	readonly dashboardNames: string[];
	readonly currentDashboard: string | null;
	readonly onDashboardChange: (name: string) => void;
	readonly onRefresh: () => void;
	readonly refreshing: boolean;
	readonly summary: DashboardSummary | null;
	readonly shortcutsOpen: boolean;
	readonly onToggleShortcuts: () => void;
	// Notification controls
	readonly notifSupported: boolean;
	readonly notifActive: boolean;
	readonly notifPermission: NotifPermission;
	readonly onEnableNotifications: () => void;
	readonly onDisableNotifications: () => void;
}

function NotifButton({
	supported,
	active,
	permission,
	onEnable,
	onDisable,
}: {
	readonly supported: boolean;
	readonly active: boolean;
	readonly permission: NotifPermission;
	readonly onEnable: () => void;
	readonly onDisable: () => void;
}) {
	if (!supported) return null;

	if (permission === "denied") {
		return (
			<span
				class="notif-btn notif-denied"
				title="Notifications blocked by browser"
			>
				Notifs blocked
			</span>
		);
	}

	if (active) {
		return (
			<button
				type="button"
				class="notif-btn notif-active"
				onClick={onDisable}
				title="Browser notifications enabled — click to disable"
				aria-label="Disable browser notifications"
			>
				Notifs on
			</button>
		);
	}

	return (
		<button
			type="button"
			class="notif-btn"
			onClick={onEnable}
			title={
				permission === "default"
					? "Click to enable browser notifications"
					: "Enable browser notifications"
			}
			aria-label="Enable browser notifications"
		>
			Notifs off
		</button>
	);
}

export function Toolbar({
	dashboardNames,
	currentDashboard,
	onDashboardChange,
	onRefresh,
	refreshing,
	summary,
	shortcutsOpen,
	onToggleShortcuts,
	notifSupported,
	notifActive,
	notifPermission,
	onEnableNotifications,
	onDisableNotifications,
}: ToolbarProps) {
	return (
		<div class="toolbar-row">
			<span class="app-brand">
				<img
					class="app-brand-icon"
					src="/assets/favicon.svg"
					alt=""
					aria-hidden="true"
				/>
				<span class="app-name">Corvix</span>
			</span>
			{summary && (
				<span class="inline-stats">
					{summary.unread_items + summary.read_items} notifications ·{" "}
					{summary.unread_items} unread · {summary.repository_count} repos
				</span>
			)}
			<div class="toolbar-right">
				<button
					type="button"
					onClick={onToggleShortcuts}
					aria-expanded={shortcutsOpen}
					aria-controls="shortcuts-panel"
				>
					? Shortcuts
				</button>
				<NotifButton
					supported={notifSupported}
					active={notifActive}
					permission={notifPermission}
					onEnable={onEnableNotifications}
					onDisable={onDisableNotifications}
				/>
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
