import { render, screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeItem } from "../test/fixtures";
import type { RuleSnippetsPayload } from "../types";
import IgnoreRuleDialog from "./IgnoreRuleDialog.svelte";

function makeSnippets(
	overrides: Partial<RuleSnippetsPayload> = {},
): RuleSnippetsPayload {
	return {
		dashboard_name: "overview",
		dashboard_ignore_rule_snippet: '- repository_in: ["org/repo-a"]',
		dashboard_ignore_rule_with_context_snippet: null,
		global_exclude_rule_snippet: "- name: ignore-org-repo-a-mention",
		global_exclude_rule_with_context_snippet: null,
		has_context: false,
		...overrides,
	};
}

function renderDialog(overrides: Record<string, unknown> = {}) {
	const props = {
		item: makeItem({ subject_title: "Target" }),
		dashboardName: "overview",
		snippets: makeSnippets() as RuleSnippetsPayload | null,
		loading: false,
		error: null as string | null,
		onClose: vi.fn(),
		...overrides,
	};
	render(IgnoreRuleDialog, { props });
	return props;
}

describe("IgnoreRuleDialog", () => {
	it("renders the dialog with heading and subtitle", () => {
		renderDialog();
		expect(screen.getByRole("dialog", { name: "Ignore rule snippets" })).toBeInTheDocument();
		expect(
			screen.getByRole("heading", { name: "Create ignore rule" }),
		).toBeInTheDocument();
		expect(screen.getByText("Notification: Target")).toBeInTheDocument();
	});

	it("shows a loading status and no snippets while loading", () => {
		renderDialog({ loading: true, snippets: null });
		expect(screen.getByText("Loading snippets...")).toBeInTheDocument();
		expect(screen.queryByRole("heading", { name: "Dashboard ignore rule" })).toBeNull();
	});

	it("shows the error text and no snippets on error", () => {
		renderDialog({ error: "boom", snippets: makeSnippets() });
		expect(screen.getByText("boom")).toBeInTheDocument();
		expect(screen.queryByRole("heading", { name: "Dashboard ignore rule" })).toBeNull();
	});

	it("renders both snippet sections with their textarea values", () => {
		renderDialog({
			snippets: makeSnippets({
				dashboard_ignore_rule_snippet: "DASH",
				global_exclude_rule_snippet: "GLOBAL",
			}),
		});
		expect(
			screen.getByRole("heading", { name: "Dashboard ignore rule" }),
		).toBeInTheDocument();
		expect(
			screen.getByRole("heading", { name: "Global exclude rule" }),
		).toBeInTheDocument();
		const textareas = document.querySelectorAll("textarea");
		expect(textareas).toHaveLength(2);
		expect((textareas[0] as HTMLTextAreaElement).value).toBe("DASH");
		expect((textareas[1] as HTMLTextAreaElement).value).toBe("GLOBAL");
	});

	it("copies the dashboard snippet and reports copy status", async () => {
		const writeText = vi
			.spyOn(globalThis.navigator.clipboard, "writeText")
			.mockResolvedValue(undefined);
		renderDialog({
			snippets: makeSnippets({ dashboard_ignore_rule_snippet: "DASH-SNIP" }),
		});
		await userEvent.click(screen.getAllByRole("button", { name: "Copy" })[0]);
		expect(writeText).toHaveBeenCalledWith("DASH-SNIP");
		expect(await screen.findByText("Dashboard snippet copied")).toBeInTheDocument();
	});

	it("renders context-aware variant buttons and copies them", async () => {
		const writeText = vi
			.spyOn(globalThis.navigator.clipboard, "writeText")
			.mockResolvedValue(undefined);
		renderDialog({
			snippets: makeSnippets({
				dashboard_ignore_rule_with_context_snippet: "DASH-CTX",
				global_exclude_rule_with_context_snippet: "GLOBAL-CTX",
				has_context: true,
			}),
		});
		const contextButtons = screen.getAllByRole("button", {
			name: "Copy context-aware variant",
		});
		expect(contextButtons).toHaveLength(2);
		await userEvent.click(contextButtons[0]);
		expect(writeText).toHaveBeenCalledWith("DASH-CTX");
		await userEvent.click(contextButtons[1]);
		expect(writeText).toHaveBeenCalledWith("GLOBAL-CTX");
	});

	it("reports a failure when the clipboard write rejects", async () => {
		vi.spyOn(globalThis.navigator.clipboard, "writeText").mockRejectedValue(
			new Error("no clipboard"),
		);
		renderDialog();
		await userEvent.click(screen.getAllByRole("button", { name: "Copy" })[0]);
		expect(
			await screen.findByText("Failed to copy dashboard snippet"),
		).toBeInTheDocument();
	});

	it("calls onClose from the close button", async () => {
		const props = renderDialog();
		await userEvent.click(
			screen.getByRole("button", { name: "Close ignore rule dialog" }),
		);
		expect(props.onClose).toHaveBeenCalledTimes(1);
	});
});
