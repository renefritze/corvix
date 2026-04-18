"""End-to-end dashboard UI tests with Playwright."""

from __future__ import annotations

import pytest

from tests.e2e.playwright_types import PageLike, RouteLike

pytest.importorskip("playwright")


@pytest.mark.e2e
def test_page_loads_and_renders_title(app_page: PageLike) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    expect(app_page).to_have_title("Corvix")
    expect(app_page.locator(".app-name")).to_have_text("Corvix")


@pytest.mark.e2e
def test_notifications_table_renders(app_page: PageLike) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    table = app_page.locator("table.notification-table")
    expect(table).to_be_visible()
    expect(table.locator("tr.notification-row")).to_have_count(3)


@pytest.mark.e2e
def test_page_loads_css_and_js(page: PageLike, corvix_server: str) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    page.goto(corvix_server)
    expect(page.locator("link[rel='stylesheet'][href*='/assets/']")).to_have_count(1)
    body_background = page.evaluate("() => getComputedStyle(document.body).backgroundColor")
    assert isinstance(body_background, str)
    assert body_background.startswith("rgb(")
    assert page_errors == []
    assert console_errors == []


@pytest.mark.e2e
def test_dashboard_selector_lists_and_switches(app_page: PageLike) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    selector = app_page.get_by_label("Select dashboard")
    expect(selector).to_be_visible()
    expect(selector.locator("option")).to_have_count(3)
    selector.select_option("triage")
    expect(app_page.locator("tr.notification-row")).to_have_count(2)
    expect(app_page.locator("tr.group-header-row")).to_contain_text(["mention"])


@pytest.mark.e2e
def test_dashboard_suburl_loads_selected_dashboard(page: PageLike, corvix_server: str) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    page.goto(f"{corvix_server}/dashboards/triage")
    expect(page.get_by_label("Select dashboard")).to_have_value("triage")
    expect(page.locator("tr.notification-row")).to_have_count(2)


@pytest.mark.e2e
def test_empty_dashboard_shows_empty_state(app_page: PageLike) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    selector = app_page.get_by_label("Select dashboard")
    selector.select_option("empty")

    expect(app_page.locator(".empty-state .empty-title")).to_have_text("All clear")
    expect(app_page.locator("tr.notification-row")).to_have_count(0)


@pytest.mark.e2e
def test_filter_bar_filters_by_reason(app_page: PageLike) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    reason_filter = app_page.get_by_label("Reason filter")
    reason_filter.select_option("subscribed")
    expect(app_page.locator("tr.notification-row")).to_have_count(1)
    expect(app_page.locator("tr.notification-row .col-reason")).to_have_text("subscribed")


@pytest.mark.e2e
def test_notification_row_shows_key_fields(app_page: PageLike) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    row = app_page.locator("tr.notification-row", has_text="Review API changes")
    expect(row).to_have_count(1)
    expect(row.locator(".col-title .title-link")).to_have_text("Review API changes")
    expect(row.locator(".col-repository .repo-label")).to_have_text("org/repo-a")
    expect(row.locator(".col-reason")).to_have_text("mention")
    expect(row.locator(".col-score .score-value")).to_have_text("90.0")


@pytest.mark.e2e
def test_sort_order_matches_config(app_page: PageLike) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    selector = app_page.get_by_label("Select dashboard")
    selector.select_option("triage")
    rows = app_page.locator("tr.notification-row .col-title .title-link")
    expect(rows).to_have_count(2)
    expect(rows.nth(0)).to_have_text("Review API changes")
    expect(rows.nth(1)).to_have_text("Triage flaky integration test")


@pytest.mark.e2e
def test_filter_clears_when_input_emptied(app_page: PageLike) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    rows = app_page.locator("tr.notification-row")
    expect(rows).to_have_count(3)
    reason_filter = app_page.get_by_label("Reason filter")
    reason_filter.select_option("subscribed")
    expect(rows).to_have_count(1)
    reason_filter.select_option("")
    expect(rows).to_have_count(3)


@pytest.mark.e2e
def test_dismiss_removes_row(app_page: PageLike) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    rows = app_page.locator("tr.notification-row")
    expect(rows).to_have_count(3)
    app_page.get_by_label("Dismiss Dependency update").click()
    expect(rows).to_have_count(2)


@pytest.mark.e2e
def test_dismiss_shows_undo_toast_and_undo_restores_row(app_page: PageLike) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    rows = app_page.locator("tr.notification-row")
    expect(rows).to_have_count(3)
    app_page.get_by_label("Dismiss Dependency update").click()
    expect(rows).to_have_count(2)
    expect(app_page.locator(".undo-toast")).to_contain_text("1 notification dismissing")
    app_page.get_by_role("button", name="Undo").click()
    expect(app_page.locator(".undo-toast")).to_have_count(0)
    expect(rows).to_have_count(3)


@pytest.mark.e2e
def test_bulk_dismiss_rows_do_not_reappear_while_snapshot_refresh_is_inflight(app_page: PageLike) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    def delayed_snapshot(route: RouteLike) -> None:
        app_page.wait_for_timeout(2_000)
        route.continue_()

    app_page.route("**/api/snapshot*", delayed_snapshot)

    rows = app_page.locator("tr.notification-row")
    expect(rows).to_have_count(3)

    app_page.get_by_label("Dismiss Review API changes").click()
    app_page.get_by_label("Dismiss Dependency update").click()

    expect(rows).to_have_count(1)

    app_page.wait_for_timeout(3_400)
    expect(rows).to_have_count(1)

    expect(app_page.locator(".undo-toast")).to_have_count(0, timeout=8_000)
    expect(rows).to_have_count(1)

    app_page.unroute("**/api/snapshot*", delayed_snapshot)


@pytest.mark.e2e
def test_loading_skeleton_shown_then_replaced(page: PageLike, corvix_server: str) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    def delayed_snapshot(route: RouteLike) -> None:
        page.wait_for_timeout(500)
        route.continue_()

    page.route("**/api/snapshot", delayed_snapshot)
    page.goto(corvix_server)
    expect(page.locator("table.notification-table[aria-label='Loading notifications']")).to_be_visible()
    expect(page.locator("tr.skeleton-row")).to_have_count(9)
    expect(page.locator("tr.notification-row")).to_have_count(3)


@pytest.mark.e2e
def test_server_error_shows_error_state(page: PageLike, corvix_server: str) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    page.route(
        "**/api/snapshot",
        lambda route: route.fulfill(
            status=500,
            content_type="application/json",
            body='{"detail":"forced test failure"}',
        ),
    )
    page.goto(corvix_server)
    expect(page.locator(".empty-state.error-state .empty-title")).to_have_text("Failed to load")
    expect(page.locator(".empty-state.error-state .empty-body")).to_contain_text("Snapshot fetch failed: 500")


@pytest.mark.e2e
def test_groups_displayed_with_headers(app_page: PageLike) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    headers = app_page.locator("tr.group-header-row .group-header-cell")
    expect(headers).to_have_count(2)
    expect(headers.nth(0)).to_contain_text("org/repo-a")
    expect(headers.nth(0)).to_contain_text("(2)")
    expect(headers.nth(1)).to_contain_text("org/repo-b")
    expect(headers.nth(1)).to_contain_text("(1)")


@pytest.mark.e2e
def test_mobile_viewport_renders_without_horizontal_scroll(page: PageLike, corvix_server: str) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(corvix_server)
    expect(page.locator("tr.notification-row")).to_have_count(3)
    has_horizontal_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth",
    )
    assert isinstance(has_horizontal_overflow, bool)
    assert has_horizontal_overflow is False


@pytest.mark.e2e
def test_keyboard_navigation_with_j_and_k(app_page: PageLike) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    first_row = app_page.locator("tr.notification-row").first
    second_row = app_page.locator("tr.notification-row").nth(1)
    first_row.focus()
    app_page.keyboard.press("j")
    expect(second_row).to_be_focused()
    app_page.keyboard.press("k")
    expect(first_row).to_be_focused()


@pytest.mark.e2e
def test_keyboard_dismiss_with_d(app_page: PageLike) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    rows = app_page.locator("tr.notification-row")
    expect(rows).to_have_count(3)
    second_row = rows.nth(1)
    second_row.focus()
    app_page.keyboard.press("d")
    expect(rows).to_have_count(2)


@pytest.mark.e2e
def test_dismiss_persists_on_reload(app_page: PageLike) -> None:
    expect = pytest.importorskip("playwright.sync_api").expect

    app_page.get_by_label("Dismiss Dependency update").click()
    expect(app_page.locator("tr.notification-row")).to_have_count(2)
    expect(app_page.locator(".undo-toast")).to_have_count(0, timeout=7_000)
    app_page.reload()
    expect(app_page.locator("tr.notification-row")).to_have_count(2)
    expect(app_page.locator("tr.notification-row", has_text="Dependency update")).to_have_count(0)
