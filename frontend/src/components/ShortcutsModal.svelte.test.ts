import { render, screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ShortcutsModal from "./ShortcutsModal.svelte";

describe("ShortcutsModal", () => {
	it("renders nothing when closed", () => {
		render(ShortcutsModal, { props: { open: false, onClose: vi.fn() } });
		expect(screen.queryByLabelText("Keyboard shortcuts")).toBeNull();
	});

	it("renders the dialog with shortcut rows when open", () => {
		render(ShortcutsModal, { props: { open: true, onClose: vi.fn() } });
		const dialog = screen.getByRole("dialog", { name: "Keyboard shortcuts" });
		expect(dialog).toBeInTheDocument();
		expect(dialog.id).toBe("shortcuts-panel");
		expect(screen.getByText("Focus filters")).toBeInTheDocument();
		expect(screen.getByText("Command palette")).toBeInTheDocument();
		expect(document.querySelectorAll("kbd").length).toBeGreaterThan(0);
	});

	it("calls onClose when the close button is clicked", async () => {
		const onClose = vi.fn();
		render(ShortcutsModal, { props: { open: true, onClose } });
		await userEvent.click(screen.getByRole("button", { name: "Close shortcuts" }));
		expect(onClose).toHaveBeenCalledTimes(1);
	});

	it("calls onClose when the dialog is cancelled (Escape)", () => {
		const onClose = vi.fn();
		render(ShortcutsModal, { props: { open: true, onClose } });
		const dialog = screen.getByRole("dialog", { name: "Keyboard shortcuts" });
		dialog.dispatchEvent(new Event("cancel", { cancelable: true }));
		expect(onClose).toHaveBeenCalledTimes(1);
	});
});
