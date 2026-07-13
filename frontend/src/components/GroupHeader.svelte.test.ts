import { render, screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import GroupHeader from "./GroupHeader.svelte";

function renderHeader(overrides: Record<string, unknown> = {}) {
	return render(GroupHeader, {
		props: {
			name: "org/repo-a",
			total: 3,
			unreadCount: 2,
			readCount: 1,
			isMarkingRead: false,
			isDismissingGroup: false,
			collapsed: false,
			colspan: 8,
			onToggleCollapse: vi.fn(),
			onMarkAllRead: vi.fn(),
			onRemoveRead: vi.fn(),
			...overrides,
		},
	});
}

describe("GroupHeader", () => {
	it("renders a group header row with the name, count and colspan", () => {
		renderHeader();
		const row = screen.getByTestId("group-header-row");
		expect(row).toBeInTheDocument();
		expect(row.querySelector("td")).toHaveAttribute("colspan", "8");
		expect(row).toHaveTextContent("org/repo-a");
		expect(row).toHaveTextContent("(3)");
	});

	it("toggles collapse via the title button and reflects aria-expanded", async () => {
		const onToggleCollapse = vi.fn();
		renderHeader({ collapsed: false, onToggleCollapse });
		const title = screen.getByRole("button", { name: "Collapse org/repo-a" });
		expect(title).toHaveAttribute("aria-expanded", "true");
		await userEvent.click(title);
		expect(onToggleCollapse).toHaveBeenCalledTimes(1);
	});

	it("labels the title button for expansion when collapsed", () => {
		renderHeader({ collapsed: true });
		const title = screen.getByRole("button", { name: "Expand org/repo-a" });
		expect(title).toHaveAttribute("aria-expanded", "false");
	});

	it("fires onRemoveRead from the remove-read button when there are read items", async () => {
		const onRemoveRead = vi.fn();
		renderHeader({ readCount: 2, onRemoveRead });
		const button = screen.getByRole("button", {
			name: "Dismiss all visible read notifications in org/repo-a",
		});
		expect(button).toHaveTextContent("Remove read (2)");
		await userEvent.click(button);
		expect(onRemoveRead).toHaveBeenCalledTimes(1);
	});

	it("hides the remove-read button when there are no read items", () => {
		renderHeader({ readCount: 0 });
		expect(
			screen.queryByRole("button", {
				name: /Dismiss all visible read notifications/,
			}),
		).toBeNull();
	});

	it("disables the remove-read button and skips the callback while dismissing", async () => {
		const onRemoveRead = vi.fn();
		renderHeader({ readCount: 2, isDismissingGroup: true, onRemoveRead });
		const button = screen.getByRole("button", {
			name: "Dismiss all visible read notifications in org/repo-a",
		});
		expect(button).toBeDisabled();
		await userEvent.click(button);
		expect(onRemoveRead).not.toHaveBeenCalled();
	});

	it("fires onMarkAllRead from the mark-all-read button when there are unread items", async () => {
		const onMarkAllRead = vi.fn();
		renderHeader({ unreadCount: 2, onMarkAllRead });
		const button = screen.getByRole("button", {
			name: "Mark all visible unread notifications in org/repo-a as read",
		});
		expect(button).toHaveTextContent("Mark all read (2)");
		await userEvent.click(button);
		expect(onMarkAllRead).toHaveBeenCalledTimes(1);
	});

	it("shows the marking state and disables the mark-all-read button", () => {
		renderHeader({ unreadCount: 2, isMarkingRead: true });
		const button = screen.getByRole("button", {
			name: "Mark all visible unread notifications in org/repo-a as read",
		});
		expect(button).toHaveTextContent("Marking...");
		expect(button).toBeDisabled();
	});

	it("hides the mark-all-read button when there are no unread items", () => {
		renderHeader({ unreadCount: 0 });
		expect(
			screen.queryByRole("button", {
				name: /Mark all visible unread notifications/,
			}),
		).toBeNull();
	});
});
