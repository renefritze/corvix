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
    expect(table.locator("tr.notification-row")).to_have_count(2)


@pytest.mark.e2e
def test_dashboard_selector_lists_and_switches(app_page: object) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    selector = app_page.get_by_label("Select dashboard")
    expect(selector).to_be_visible()
    expect(selector.locator("option")).to_have_count(2)
    selector.select_option("triage")
    expect(app_page.locator("tr.notification-row")).to_have_count(1)
    expect(app_page.locator("tr.group-header-row")).to_contain_text(["mention"])
