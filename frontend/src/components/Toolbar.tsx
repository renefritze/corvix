import type { NotifPermission } from "../hooks/useBrowserNotifications";
import type { DashboardSummary } from "../types";

interface ToolbarProps {
	dashboardNames: string[];
	currentDashboard: string | null;
	onDashboardChange: (name: string) => void;
	onRefresh: () => void;
	refreshing: boolean;
	summary: DashboardSummary | null;
	shortcutsOpen: boolean;
	onToggleShortcuts: () => void;
	// Notification controls
	notifSupported: boolean;
	notifActive: boolean;
	notifPermission: NotifPermission;
	onEnableNotifications: () => void;
	onDisableNotifications: () => void;
}

function NotifButton({
	supported,
	active,
	permission,
	onEnable,
	onDisable,
}: {
	supported: boolean;
	active: boolean;
	permission: NotifPermission;
	onEnable: () => void;
	onDisable: () => void;
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
			<span class="app-name">Corvix</span>
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
