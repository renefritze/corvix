import { render, screen, within } from "@testing-library/preact";
import userEvent from "@testing-library/user-event";
import { makeItem } from "../test/fixtures";
import { FilterBar } from "./FilterBar";

describe("FilterBar", () => {
	it("renders deduped options and fires callbacks", async () => {
		const onFilterChange = vi.fn();
		const onClearFilters = vi.fn();
		const user = userEvent.setup();

		render(
			<FilterBar
				filters={{ unread: "all", reason: [], repository: "" }}
				includeRead={true}
				items={[
					makeItem({ reason: "mention", repository: "org/a" }),
					makeItem({
						thread_id: "2",
						reason: "subscribed",
						repository: "org/b",
					}),
				]}
				onFilterChange={onFilterChange}
				onClearFilters={onClearFilters}
				generatedAt={"2026-04-09T10:00:00Z"}
			/>,
		);

		await user.click(screen.getByLabelText("Reason filter"));
		await user.click(screen.getByRole("button", { name: "subscribed" }));
		expect(onFilterChange).toHaveBeenCalledWith("reason", ["subscribed"]);

		await user.click(screen.getByRole("button", { name: "Clear" }));
		expect(onClearFilters).toHaveBeenCalledTimes(1);
		expect(screen.getByText(/snapshot:/i)).toBeInTheDocument();
	});

	it("supports selecting multiple reasons", async () => {
		const onFilterChange = vi.fn();
		const user = userEvent.setup();

		render(
			<FilterBar
				filters={{ unread: "all", reason: ["mention"], repository: "" }}
				includeRead={true}
				items={[
					makeItem({ reason: "mention", repository: "org/a" }),
					makeItem({
						thread_id: "2",
						reason: "subscribed",
						repository: "org/b",
					}),
					makeItem({
						thread_id: "3",
						reason: "review_requested",
						repository: "org/c",
					}),
				]}
				onFilterChange={onFilterChange}
				onClearFilters={vi.fn()}
				generatedAt={null}
			/>,
		);

		await user.click(screen.getByLabelText("Reason filter"));
		await user.click(screen.getByRole("button", { name: "subscribed" }));
		expect(onFilterChange).toHaveBeenLastCalledWith("reason", [
			"mention",
			"subscribed",
		]);
	});

	it("shows chips and allows removing selected reason", async () => {
		const onFilterChange = vi.fn();
		const user = userEvent.setup();

		render(
			<FilterBar
				filters={{ unread: "all", reason: ["mention"], repository: "" }}
				includeRead={true}
				items={[makeItem({ reason: "mention" })]}
				onFilterChange={onFilterChange}
				onClearFilters={vi.fn()}
				generatedAt={null}
			/>,
		);

		expect(screen.getByText("mention")).toBeInTheDocument();
		await user.click(
			screen.getByRole("button", { name: "Remove mention reason filter" }),
		);
		expect(onFilterChange).toHaveBeenCalledWith("reason", []);
	});

	it("disables read-state options when dashboard excludes read items", () => {
		render(
			<FilterBar
				filters={{ unread: "unread", reason: [], repository: "" }}
				includeRead={false}
				items={[makeItem()]}
				onFilterChange={vi.fn()}
				onClearFilters={vi.fn()}
				generatedAt={null}
			/>,
		);

		const unreadFilter = screen.getByLabelText("Unread state filter");
		expect(
			within(unreadFilter).getByRole("option", { name: /All/ }),
		).toBeDisabled();
		expect(
			within(unreadFilter).getByRole("option", { name: /Read only/ }),
		).toBeDisabled();
		expect(
			within(unreadFilter).getByRole("option", { name: "Unread only" }),
		).not.toBeDisabled();
	});

	it("keeps selected repository visible when it no longer has unread items", () => {
		render(
			<FilterBar
				filters={{ unread: "unread", reason: [], repository: "org/a" }}
				includeRead={false}
				items={[]}
				onFilterChange={vi.fn()}
				onClearFilters={vi.fn()}
				generatedAt={null}
			/>,
		);

		const repositoryFilter = screen.getByLabelText("Repository filter");
		expect(repositoryFilter).toHaveValue("org/a");
		expect(
			within(repositoryFilter).getByRole("option", {
				name: "org/a (no unread notifications)",
			}),
		).toBeInTheDocument();
	});

	it("keeps selected reasons visible when they no longer exist in the current items", async () => {
		const user = userEvent.setup();
		render(
			<FilterBar
				filters={{
					unread: "unread",
					reason: ["mention", "author"],
					repository: "",
				}}
				includeRead={false}
				items={[makeItem({ reason: "review_requested" })]}
				onFilterChange={vi.fn()}
				onClearFilters={vi.fn()}
				generatedAt={null}
			/>,
		);

		const reasonFilter = screen.getByLabelText("Reason filter");
		await user.click(reasonFilter);
		expect(
			screen.getByRole("button", {
				name: "mention (no unread notifications)",
			}),
		).toBeInTheDocument();
		expect(
			screen.getByRole("button", {
				name: "author (no unread notifications)",
			}),
		).toBeInTheDocument();
	});
});
