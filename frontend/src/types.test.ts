import { describe, expect, it } from "vitest";
import { makeItem } from "./test/fixtures";
import { notificationKey } from "./types";

describe("notificationKey", () => {
	it("joins account_id and thread_id with a colon", () => {
		expect(
			notificationKey({ account_id: "account", thread_id: "thread" }),
		).toBe("account:thread");
	});

	it("derives the key from a full DashboardItem", () => {
		expect(notificationKey(makeItem({ account_id: "a", thread_id: "b" }))).toBe(
			"a:b",
		);
	});
});
