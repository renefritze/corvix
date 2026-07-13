import { render, screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeItem } from "../test/fixtures";
import TableRow from "./TableRow.svelte";

function renderRow(overrides = {}, handlers: Record<string, unknown> = {}) {
	return render(TableRow, {
		props: {
			item: makeItem(overrides),
			onDismiss: vi.fn(),
			onOpenTarget: vi.fn(),
			onRequestIgnoreRule: vi.fn(),
			isPendingDismissal: false,
			...handlers,
		},
	});
}

describe("TableRow", () => {
	it("renders the key fields with the e2e DOM contract", () => {
		renderRow();
		const row = document.querySelector("tr[data-thread-id]");
		expect(row).not.toBeNull();
		expect(row?.getAttribute("data-account-id")).toBe("primary");
		expect(
			row?.querySelector("td[data-label='Title'] a")?.textContent,
		).toBe("Review API changes");
		expect(
			row?.querySelector("td[data-label='Repository'] span")?.textContent,
		).toBe("org/repo-a");
		expect(row?.querySelector("td[data-label='Reason']")?.textContent?.trim()).toBe(
			"mention",
		);
		expect(
			row?.querySelector("td[data-label='Score'] span")?.textContent,
		).toBe("90.0");
	});

	it("marks read on title click when unread", async () => {
		const onOpenTarget = vi.fn();
		renderRow({ unread: true }, { onOpenTarget });
		await userEvent.click(screen.getByRole("link", { name: "Review API changes" }));
		expect(onOpenTarget).toHaveBeenCalledWith("primary", "thread-1");
	});

	it("does not mark read on title click when already read", async () => {
		const onOpenTarget = vi.fn();
		renderRow({ unread: false }, { onOpenTarget });
		await userEvent.click(screen.getByRole("link", { name: "Review API changes" }));
		expect(onOpenTarget).not.toHaveBeenCalled();
	});

	it("dismisses via the labelled dismiss button", async () => {
		const onDismiss = vi.fn();
		renderRow({}, { onDismiss });
		await userEvent.click(screen.getByLabelText("Dismiss Review API changes"));
		expect(onDismiss).toHaveBeenCalledWith("primary", "thread-1");
	});

	it("requests an ignore rule on right-click", async () => {
		const onRequestIgnoreRule = vi.fn();
		renderRow({}, { onRequestIgnoreRule });
		const row = document.querySelector("tr[data-thread-id]") as HTMLElement;
		row.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, clientX: 5, clientY: 6 }));
		expect(onRequestIgnoreRule).toHaveBeenCalled();
	});

	it("renders a plain title when there is no web_url", () => {
		renderRow({ web_url: null });
		expect(screen.queryByRole("link")).toBeNull();
		expect(screen.getByText("Review API changes")).toBeInTheDocument();
	});
});
