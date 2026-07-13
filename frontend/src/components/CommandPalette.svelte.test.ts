import { render, screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Command } from "../lib/commandPalette.svelte";
import CommandPalette from "./CommandPalette.svelte";

function makeCommands(): Command[] {
	return [
		{ id: "a", label: "Alpha", run: vi.fn() },
		{ id: "b", label: "Beta", hint: "hint-b", run: vi.fn() },
		{ id: "c", label: "Gamma", run: vi.fn() },
	];
}

function renderPalette(overrides: Record<string, unknown> = {}) {
	const commands = (overrides.commands as Command[]) ?? makeCommands();
	const props = {
		query: "",
		commands,
		onQueryChange: vi.fn(),
		onRun: vi.fn(),
		onClose: vi.fn(),
		...overrides,
	};
	render(CommandPalette, { props });
	return props;
}

describe("CommandPalette", () => {
	it("renders the dialog and command options", () => {
		renderPalette();
		expect(screen.getByRole("dialog", { name: "Command palette" })).toBeInTheDocument();
		expect(screen.getByLabelText("Command palette search")).toBeInTheDocument();
		expect(screen.getByRole("option", { name: "Alpha" })).toBeInTheDocument();
		expect(screen.getByText("hint-b")).toBeInTheDocument();
	});

	it("calls onQueryChange while typing", async () => {
		const props = renderPalette();
		await userEvent.type(screen.getByLabelText("Command palette search"), "x");
		expect(props.onQueryChange).toHaveBeenCalledWith("x");
	});

	it("marks the first option active initially and runs it on Enter", async () => {
		const props = renderPalette();
		expect(screen.getByRole("option", { name: "Alpha" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		await userEvent.keyboard("{Enter}");
		expect(props.onRun).toHaveBeenCalledWith(
			expect.objectContaining({ id: "a" }),
		);
	});

	it("moves the active option with ArrowDown/ArrowUp", async () => {
		const props = renderPalette();
		const input = screen.getByLabelText("Command palette search");
		input.focus();
		await userEvent.keyboard("{ArrowDown}{ArrowDown}");
		expect(screen.getByRole("option", { name: "Gamma" })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		await userEvent.keyboard("{ArrowUp}");
		expect(screen.getByRole("option", { name: /Beta/ })).toHaveAttribute(
			"aria-selected",
			"true",
		);
		await userEvent.keyboard("{Enter}");
		expect(props.onRun).toHaveBeenCalledWith(
			expect.objectContaining({ id: "b" }),
		);
	});

	it("calls onClose on Escape", async () => {
		const props = renderPalette();
		screen.getByLabelText("Command palette search").focus();
		await userEvent.keyboard("{Escape}");
		expect(props.onClose).toHaveBeenCalledTimes(1);
	});

	it("runs a command when its option is clicked", async () => {
		const props = renderPalette();
		await userEvent.click(screen.getByRole("option", { name: "Gamma" }));
		expect(props.onRun).toHaveBeenCalledWith(
			expect.objectContaining({ id: "c" }),
		);
	});

	it("shows an empty message when there are no commands", () => {
		renderPalette({ commands: [] });
		expect(screen.getByText("No matching commands")).toBeInTheDocument();
	});

	it("calls onClose when the overlay is clicked", async () => {
		const props = renderPalette();
		const overlay = document.querySelector(".cmdk-overlay") as HTMLElement;
		await userEvent.click(overlay);
		expect(props.onClose).toHaveBeenCalledTimes(1);
	});
});
