"""Generate a deterministic UI screenshot for README/docs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.playwright_types import PageLike

pytest.importorskip("playwright")

SCREENSHOT_PATH = Path("docs/_static/corvix-ui.png")
FROZEN_NOW_ISO = "2026-04-09T10:30:00.000Z"


@pytest.mark.e2e
def test_generate_ui_screenshot(page: PageLike, corvix_server: str) -> None:
    frozen_now = json.dumps(FROZEN_NOW_ISO)
    script = """
        (() => {
          const fixedNow = new Date(__FIXED_NOW__).getTime();
          const OriginalDate = Date;
          class MockDate extends OriginalDate {
            constructor(...args) {
              if (args.length === 0) {
                super(fixedNow);
                return;
              }
              super(...args);
            }
            static now() {
              return fixedNow;
            }
          }
          MockDate.UTC = OriginalDate.UTC;
          MockDate.parse = OriginalDate.parse;
          window.Date = MockDate;
        })();
        """
    page.add_init_script(script.replace("__FIXED_NOW__", frozen_now))

    page.set_viewport_size({"width": 1720, "height": 1080})
    page.goto(f"{corvix_server}/dashboards/overview", wait_until="networkidle")
    page.wait_for_selector("table.notification-table")
    page.wait_for_selector("text=Corvix")
    page.wait_for_function("() => document.fonts.status === 'loaded'")

    page.add_style_tag(content="*, *::before, *::after { animation: none !important; transition: none !important; }")

    SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    page.locator(".shell").screenshot(path=str(SCREENSHOT_PATH), animations="disabled")
