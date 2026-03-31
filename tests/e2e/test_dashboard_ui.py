"""End-to-end dashboard UI tests with Playwright."""

from __future__ import annotations

import pytest

pytest.importorskip("playwright")


@pytest.mark.e2e
def test_page_loads_and_renders_title(app_page: object) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    expect(app_page).to_have_title("Corvix")
    expect(app_page.locator(".app-name")).to_have_text("Corvix")


@pytest.mark.e2e
def test_notifications_table_renders(app_page: object) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    table = app_page.locator("table.notification-table")
    expect(table).to_be_visible()
    expect(table.locator("tr.notification-row")).to_have_count(3)


@pytest.mark.e2e
def test_dashboard_selector_lists_and_switches(app_page: object) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    selector = app_page.get_by_label("Select dashboard")
    expect(selector).to_be_visible()
    expect(selector.locator("option")).to_have_count(3)
    selector.select_option("triage")
    expect(app_page.locator("tr.notification-row")).to_have_count(1)
    expect(app_page.locator("tr.group-header-row")).to_contain_text(["mention"])


@pytest.mark.e2e
def test_empty_dashboard_shows_empty_state(app_page: object) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    selector = app_page.get_by_label("Select dashboard")
    selector.select_option("empty")

    expect(app_page.locator(".empty-state .empty-title")).to_have_text("All clear")
    expect(app_page.locator("tr.notification-row")).to_have_count(0)


@pytest.mark.e2e
def test_filter_bar_filters_by_reason(app_page: object) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    reason_filter = app_page.get_by_label("Reason filter")
    reason_filter.select_option("subscribed")
    expect(app_page.locator("tr.notification-row")).to_have_count(1)
    expect(app_page.locator("tr.notification-row .col-reason")).to_have_text("subscribed")


@pytest.mark.e2e
def test_notification_row_shows_key_fields(app_page: object) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    row = app_page.locator("tr.notification-row", has_text="Review API changes")
    expect(row).to_have_count(1)
    expect(row.locator(".col-title .title-link")).to_have_text("Review API changes")
    expect(row.locator(".col-repository .repo-label")).to_have_text("org/repo-a")
    expect(row.locator(".col-reason")).to_have_text("mention")
    expect(row.locator(".col-score .score-value")).to_have_text("90.0")


@pytest.mark.e2e
def test_sort_order_matches_config_and_toggles(app_page: object) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    selector = app_page.get_by_label("Select dashboard")
    selector.select_option("triage")
    rows = app_page.locator("tr.notification-row .col-title .title-link")
    expect(rows).to_have_count(2)
    expect(rows.nth(0)).to_have_text("Review API changes")
    expect(rows.nth(1)).to_have_text("Triage flaky integration test")

    app_page.get_by_role("button", name="Score").click()
    expect(rows.nth(0)).to_have_text("Triage flaky integration test")
    expect(rows.nth(1)).to_have_text("Review API changes")


@pytest.mark.e2e
def test_filter_clears_when_input_emptied(app_page: object) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    rows = app_page.locator("tr.notification-row")
    expect(rows).to_have_count(3)
    reason_filter = app_page.get_by_label("Reason filter")
    reason_filter.select_option("subscribed")
    expect(rows).to_have_count(1)
    reason_filter.select_option("")
    expect(rows).to_have_count(3)


@pytest.mark.e2e
def test_dismiss_shows_undo_toast_and_undo_restores_row(app_page: object) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    rows = app_page.locator("tr.notification-row")
    expect(rows).to_have_count(3)
    app_page.get_by_label("Dismiss Dependency update").click()
    expect(rows).to_have_count(2)
    expect(app_page.locator(".undo-toast")).to_contain_text("1 notification dismissing")
    app_page.get_by_role("button", name="Undo").click()
    expect(app_page.locator(".undo-toast")).to_have_count(0)
    expect(rows).to_have_count(3)
