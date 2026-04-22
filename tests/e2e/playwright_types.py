"""Protocol types for Playwright fixtures used in e2e tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, Protocol, overload


class LocatorLike(Protocol):
    @property
    def first(self) -> LocatorLike: ...

    def nth(self, index: int) -> LocatorLike: ...

    def locator(self, selector: str, *, has_text: str | None = None) -> LocatorLike: ...

    def click(self) -> None: ...

    def focus(self) -> None: ...

    def select_option(self, value: str | list[str]) -> None: ...

    def screenshot(
        self,
        *,
        path: str | None = None,
        animations: Literal["disabled", "allow"] | None = None,
    ) -> bytes: ...


class KeyboardLike(Protocol):
    def press(self, key: str) -> None: ...


class ConsoleMessageLike(Protocol):
    type: str
    text: str


class ApiResponseLike(Protocol): ...


class RouteLike(Protocol):
    def fetch(self, *, timeout: int | None = None) -> ApiResponseLike: ...

    def continue_(self) -> None: ...

    @overload
    def fulfill(self, *, response: ApiResponseLike) -> None: ...

    @overload
    def fulfill(self, *, status: int, content_type: str, body: str) -> None: ...

    def fulfill(
        self,
        *,
        response: ApiResponseLike | None = None,
        status: int | None = None,
        content_type: str | None = None,
        body: str | None = None,
    ) -> None: ...


class PageLike(Protocol):
    keyboard: KeyboardLike

    def add_init_script(self, script: str) -> None: ...

    def goto(
        self,
        url: str,
        *,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] | None = None,
    ) -> None: ...

    def wait_for_selector(self, selector: str) -> LocatorLike: ...

    def locator(self, selector: str, *, has_text: str | None = None) -> LocatorLike: ...

    def get_by_label(self, text: str) -> LocatorLike: ...

    def get_by_role(self, role: str, *, name: str) -> LocatorLike: ...

    def evaluate(self, expression: str) -> object: ...

    @overload
    def on(
        self,
        event: Literal["console"],
        callback: Callable[[ConsoleMessageLike], object | None],
    ) -> None: ...

    @overload
    def on(self, event: Literal["pageerror"], callback: Callable[[BaseException], object | None]) -> None: ...

    @overload
    def on(self, event: str, callback: Callable[[object], object | None]) -> None: ...

    def route(self, url: str, handler: Callable[[RouteLike], object]) -> None: ...

    def unroute(
        self,
        url: str,
        handler: Callable[[RouteLike], object] | None = None,
    ) -> None: ...

    def unroute_all(
        self,
        *,
        behavior: Literal["default", "wait", "ignoreErrors"] | None = None,
    ) -> None: ...

    def wait_for_timeout(self, timeout: float) -> None: ...

    def set_viewport_size(self, viewport: dict[str, int]) -> None: ...

    def wait_for_function(self, expression: str) -> object: ...

    def add_style_tag(self, *, content: str) -> None: ...

    def reload(self) -> None: ...
