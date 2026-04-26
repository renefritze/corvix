import { fireEvent, render, screen, waitFor } from "@testing-library/preact";
import { makeItem } from "../test/fixtures";
import { IgnoreRuleDialog } from "./IgnoreRuleDialog";

describe("IgnoreRuleDialog", () => {
	it("renders both snippets and copies the dashboard snippet", async () => {
		const writeText = vi
			.spyOn(globalThis.navigator.clipboard, "writeText")
			.mockResolvedValue(undefined);

		render(
			<IgnoreRuleDialog
				open
				item={makeItem({ subject_title: "Target" })}
				dashboardName="overview"
				snippets={{
					dashboard_name: "overview",
					dashboard_ignore_rule_snippet:
						'- repository_in: ["org/repo-a"]\n  reason_in: ["mention"]\n  subject_type_in: ["PullRequest"]',
					global_exclude_rule_snippet:
						'- name: ignore-org-repo-a-mention-pullrequest\n  match:\n    repository_in: ["org/repo-a"]\n    reason_in: ["mention"]\n    subject_type_in: ["PullRequest"]\n  exclude_from_dashboards: true',
					dashboard_ignore_rule_with_context_snippet: null,
					global_exclude_rule_with_context_snippet: null,
					has_context: false,
				}}
				loading={false}
				error={null}
				onClose={vi.fn()}
			/>,
		);

		expect(
			screen.getByRole("heading", { name: "Dashboard ignore rule" }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("heading", { name: "Global exclude rule" }),
		).toBeInTheDocument();

		fireEvent.click(screen.getAllByRole("button", { name: "Copy" })[0]);
		await waitFor(() => {
			expect(writeText).toHaveBeenCalledWith(
				expect.stringContaining('repository_in: ["org/repo-a"]'),
			);
		});
	});

	it("resets copy status when reopened for another notification", async () => {
		const writeText = vi
			.spyOn(globalThis.navigator.clipboard, "writeText")
			.mockResolvedValue(undefined);
		const { rerender } = render(
			<IgnoreRuleDialog
				open
				item={makeItem({ thread_id: "one", subject_title: "Target one" })}
				dashboardName="overview"
				snippets={{
					dashboard_name: "overview",
					dashboard_ignore_rule_snippet: '- repository_in: ["org/repo-a"]',
					global_exclude_rule_snippet:
						"- name: ignore-org-repo-a-mention-pullrequest",
					dashboard_ignore_rule_with_context_snippet: null,
					global_exclude_rule_with_context_snippet: null,
					has_context: false,
				}}
				loading={false}
				error={null}
				onClose={vi.fn()}
			/>,
		);

		fireEvent.click(screen.getAllByRole("button", { name: "Copy" })[0]);
		await waitFor(() => {
			expect(screen.getByText("Dashboard snippet copied")).toBeInTheDocument();
		});

		rerender(
			<IgnoreRuleDialog
				open={false}
				item={null}
				dashboardName="overview"
				snippets={null}
				loading={false}
				error={null}
				onClose={vi.fn()}
			/>,
		);
		rerender(
			<IgnoreRuleDialog
				open
				item={makeItem({ thread_id: "two", subject_title: "Target two" })}
				dashboardName="overview"
				snippets={{
					dashboard_name: "overview",
					dashboard_ignore_rule_snippet: '- repository_in: ["org/repo-a"]',
					global_exclude_rule_snippet:
						"- name: ignore-org-repo-a-mention-pullrequest",
					dashboard_ignore_rule_with_context_snippet: null,
					global_exclude_rule_with_context_snippet: null,
					has_context: false,
				}}
				loading={false}
				error={null}
				onClose={vi.fn()}
			/>,
		);

		expect(
			screen.queryByText("Dashboard snippet copied"),
		).not.toBeInTheDocument();
		expect(writeText).toHaveBeenCalledTimes(1);
	});

	it("shows context snippets and reports copy failures", async () => {
		vi.spyOn(globalThis.navigator.clipboard, "writeText").mockRejectedValue(
			new Error("no clipboard"),
		);

		render(
			<IgnoreRuleDialog
				open
				item={makeItem({ subject_title: "Target" })}
				dashboardName="overview"
				snippets={{
					dashboard_name: "overview",
					dashboard_ignore_rule_snippet: '- repository_in: ["org/repo-a"]',
					global_exclude_rule_snippet:
						"- name: ignore-org-repo-a-mention-pullrequest",
					dashboard_ignore_rule_with_context_snippet:
						'- repository_in: ["org/repo-a"]\n  context:\n    - path: "github.pr_state.draft"',
					global_exclude_rule_with_context_snippet:
						'- name: ignore-org-repo-a-mention-pullrequest\n  match:\n    context:\n      - path: "github.pr_state.draft"',
					has_context: true,
				}}
				loading={false}
				error={null}
				onClose={vi.fn()}
			/>,
		);

		const contextButtons = screen.getAllByRole("button", {
			name: "Copy context-aware variant",
		});
		fireEvent.click(contextButtons[0]);
		await waitFor(() => {
			expect(
				screen.getByText("Failed to copy dashboard context snippet"),
			).toBeInTheDocument();
		});

		fireEvent.click(contextButtons[1]);
		await waitFor(() => {
			expect(
				screen.getByText("Failed to copy global context snippet"),
			).toBeInTheDocument();
		});
	});
});
