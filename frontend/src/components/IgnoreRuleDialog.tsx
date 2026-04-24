import { useEffect, useState } from "preact/hooks";
import type { DashboardItem, RuleSnippetsPayload } from "../types";

interface IgnoreRuleDialogProps {
	readonly open: boolean;
	readonly item: DashboardItem | null;
	readonly dashboardName: string | null;
	readonly snippets: RuleSnippetsPayload | null;
	readonly loading: boolean;
	readonly error: string | null;
	readonly onClose: () => void;
}

export function IgnoreRuleDialog({
	open,
	item,
	dashboardName,
	snippets,
	loading,
	error,
	onClose,
}: IgnoreRuleDialogProps) {
	const [copyStatus, setCopyStatus] = useState<string | null>(null);

	useEffect(() => {
		if (!open || !item) {
			setCopyStatus(null);
			return;
		}
		setCopyStatus(null);
	}, [open, item]);

	if (!open || !item) {
		return null;
	}
	const dashboardContextSnippet =
		snippets?.dashboard_ignore_rule_with_context_snippet ?? null;
	const globalContextSnippet =
		snippets?.global_exclude_rule_with_context_snippet ?? null;

	async function copyText(value: string, label: string) {
		try {
			await navigator.clipboard.writeText(value);
			setCopyStatus(`${label} copied`);
		} catch {
			setCopyStatus(`Failed to copy ${label.toLowerCase()}`);
		}
	}

	return (
		<dialog class="ignore-rule-dialog" aria-label="Ignore rule snippets" open>
			<div class="ignore-rule-header">
				<h2>Create ignore rule</h2>
				<button
					type="button"
					onClick={onClose}
					aria-label="Close ignore rule dialog"
				>
					✕
				</button>
			</div>
			<p class="ignore-rule-subtitle">
				{`Notification: ${item.subject_title}`}
			</p>
			{loading && <p class="ignore-rule-status">Loading snippets...</p>}
			{error && <p class="ignore-rule-status error">{error}</p>}
			{copyStatus && !error && <p class="ignore-rule-status">{copyStatus}</p>}
			{snippets && !loading && !error && (
				<div class="ignore-rule-content">
					<section class="snippet-card">
						<h3>Dashboard ignore rule</h3>
						<p>
							Paste under{" "}
							<code>{`dashboards: - name: ${dashboardName ?? snippets.dashboard_name} -> ignore_rules:`}</code>
						</p>
						<textarea
							readOnly
							value={snippets.dashboard_ignore_rule_snippet}
							rows={dashboardContextSnippet ? 8 : 6}
						/>
						<div class="snippet-actions">
							<button
								type="button"
								onClick={() =>
									void copyText(
										snippets.dashboard_ignore_rule_snippet,
										"Dashboard snippet",
									)
								}
							>
								Copy
							</button>
							{dashboardContextSnippet && (
								<button
									type="button"
									onClick={() =>
										void copyText(
											dashboardContextSnippet,
											"Dashboard context snippet",
										)
									}
								>
									Copy context-aware variant
								</button>
							)}
						</div>
					</section>
					<section class="snippet-card">
						<h3>Global exclude rule</h3>
						<p>
							Paste under <code>rules.global</code>
						</p>
						<textarea
							readOnly
							value={snippets.global_exclude_rule_snippet}
							rows={globalContextSnippet ? 9 : 7}
						/>
						<div class="snippet-actions">
							<button
								type="button"
								onClick={() =>
									void copyText(
										snippets.global_exclude_rule_snippet,
										"Global snippet",
									)
								}
							>
								Copy
							</button>
							{globalContextSnippet && (
								<button
									type="button"
									onClick={() =>
										void copyText(
											globalContextSnippet,
											"Global context snippet",
										)
									}
								>
									Copy context-aware variant
								</button>
							)}
						</div>
					</section>
				</div>
			)}
		</dialog>
	);
}
