import type { NotifPermission } from "../hooks/useBrowserNotifications";
import type { DashboardSummary } from "../types";
import styles from "./Toolbar.module.css";

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
				class={styles.notifDenied}
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
				class={[styles.notifBtn, styles.notifActive].join(" ")}
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
			class={styles.notifBtn}
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
		<div class={styles.toolbarRow}>
			<span class={styles.appBrand}>
				<img
					class={styles.appBrandIcon}
					src="/assets/favicon.svg"
					alt=""
					aria-hidden="true"
				/>
				<span class={styles.appName} data-testid="app-name">Corvix</span>
			</span>
			{summary && (
				<span class={styles.inlineStats}>
					{summary.unread_items + summary.read_items} notifications ·{" "}
					{summary.unread_items} unread · {summary.repository_count} repos
				</span>
			)}
			<div class={styles.toolbarRight}>
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
					class={[styles.refreshBtn, refreshing ? styles.refreshing : ""].filter(Boolean).join(" ")}
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
