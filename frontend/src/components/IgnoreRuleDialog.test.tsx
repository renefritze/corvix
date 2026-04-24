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
					context: {},
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
});
