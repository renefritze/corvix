import { render, screen, waitFor } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { makeItem } from "../test/fixtures";
import type { RuleSnippetsPayload } from "../types";
import { useIgnoreRuleDialog } from "./useIgnoreRuleDialog";

// Lets pending effects (e.g. the window click/keydown listeners) flush before
// we dispatch the events they listen for.
function flushEffects(): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, 0));
}

const SNIPPETS: RuleSnippetsPayload = {
	dashboard_name: "overview",
	dashboard_ignore_rule_snippet: "- repository_in: [org/repo-a]",
	global_exclude_rule_snippet: "- name: ignore",
	dashboard_ignore_rule_with_context_snippet: null,
	global_exclude_rule_with_context_snippet: null,
	has_context: false,
};

function Harness({ dashboard }: { dashboard: string | null }) {
	const {
		menu,
		dialogItem,
		snippets,
		loading,
		error,
		requestRule,
		openDialog,
		closeDialog,
	} = useIgnoreRuleDialog(dashboard);
	const item = makeItem({ thread_id: "item-42" });
	return (
		<div>
			<div data-testid="menu">{menu ? `${menu.x},${menu.y}` : "none"}</div>
			<div data-testid="dialog">{dialogItem ? dialogItem.thread_id : "none"}</div>
			<div data-testid="loading">{String(loading)}</div>
			<div data-testid="error">{error ?? "none"}</div>
			<div data-testid="snippets">
				{snippets ? snippets.dashboard_ignore_rule_snippet : "none"}
			</div>
			<button
				type="button"
				onClick={() => requestRule(item, { x: 10, y: 20 })}
			>
				request
			</button>
			<button type="button" onClick={() => openDialog(item)}>
				open
			</button>
			<button type="button" onClick={closeDialog}>
				close
			</button>
		</div>
	);
}

function renderHarness(dashboard: string | null = "overview") {
	const user = userEvent.setup();
	render(<Harness dashboard={dashboard} />);
	return user;
}

function mockSnippetFetch(response: Partial<Response>) {
	return vi.spyOn(globalThis, "fetch").mockResolvedValue(response as Response);
}

// Opens the context menu, then dismisses it via the given window event and
// asserts the menu is gone.
async function expectMenuDismissedBy(
	user: ReturnType<typeof userEvent.setup>,
	event: Event,
) {
	await user.click(screen.getByRole("button", { name: "request" }));
	expect(screen.getByTestId("menu")).toHaveTextContent("10,20");
	await flushEffects();
	globalThis.dispatchEvent(event);
	await waitFor(() =>
		expect(screen.getByTestId("menu")).toHaveTextContent("none"),
	);
}

describe("useIgnoreRuleDialog", () => {
	it("opens the context menu at the requested position", async () => {
		const user = renderHarness();
		await user.click(screen.getByRole("button", { name: "request" }));
		expect(screen.getByTestId("menu")).toHaveTextContent("10,20");
	});

	it("closes the menu on outside click and on Escape", async () => {
		const user = renderHarness();
		await expectMenuDismissedBy(user, new MouseEvent("click"));
		await expectMenuDismissedBy(
			user,
			new KeyboardEvent("keydown", { key: "Escape" }),
		);
	});

	it("loads snippets when the dialog opens and clears the menu", async () => {
		const fetchMock = mockSnippetFetch({
			ok: true,
			json: async () => SNIPPETS,
		});
		const user = renderHarness();
		await user.click(screen.getByRole("button", { name: "request" }));
		await user.click(screen.getByRole("button", { name: "open" }));

		expect(screen.getByTestId("menu")).toHaveTextContent("none");
		expect(screen.getByTestId("dialog")).toHaveTextContent("item-42");
		await waitFor(() =>
			expect(screen.getByTestId("snippets")).toHaveTextContent(
				"repository_in",
			),
		);
		expect(screen.getByTestId("loading")).toHaveTextContent("false");
		expect(fetchMock).toHaveBeenCalledWith(
			"/api/v1/notifications/primary/item-42/rule-snippets?dashboard=overview",
		);
	});

	it("surfaces a snippet fetch error", async () => {
		mockSnippetFetch({ ok: false, status: 500, json: async () => ({}) });
		const user = renderHarness();
		await user.click(screen.getByRole("button", { name: "open" }));

		await waitFor(() =>
			expect(screen.getByTestId("error")).toHaveTextContent(
				"Rule snippets fetch failed (500)",
			),
		);
	});

	it("resets dialog state on close", async () => {
		mockSnippetFetch({ ok: true, json: async () => SNIPPETS });
		const user = renderHarness();
		await user.click(screen.getByRole("button", { name: "open" }));
		await waitFor(() =>
			expect(screen.getByTestId("snippets")).toHaveTextContent(
				"repository_in",
			),
		);

		await user.click(screen.getByRole("button", { name: "close" }));
		expect(screen.getByTestId("dialog")).toHaveTextContent("none");
		expect(screen.getByTestId("snippets")).toHaveTextContent("none");
		expect(screen.getByTestId("error")).toHaveTextContent("none");
		expect(screen.getByTestId("loading")).toHaveTextContent("false");
	});
});
