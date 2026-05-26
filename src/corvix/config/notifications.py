"""Notifications configuration model and YAML parsing."""

from __future__ import annotations

from dataclasses import dataclass, field

from corvix.config._utils import (
    _ensure_map,
    _get_bool,
    _get_float,
    _get_int,
    _get_str,
)


@dataclass(slots=True)
class BrowserTabTargetConfig:
    """Config for in-tab browser notification delivery."""

    enabled: bool = True
    max_per_cycle: int = 5
    cooldown_seconds: int = 10


@dataclass(slots=True)
class WebPushTargetConfig:
    """Config for background Web Push notification delivery (phase 2)."""

    enabled: bool = False
    vapid_public_key_env: str = "CORVIX_VAPID_PUBLIC_KEY"
    vapid_private_key_env: str = "CORVIX_VAPID_PRIVATE_KEY"
    subject: str = ""


@dataclass(slots=True)
class NotificationsDetectConfig:
    """Controls which records qualify for notification events."""

    include_read: bool = False
    min_score: float = 0.0


@dataclass(slots=True)
class NotificationsConfig:
    """Top-level notifications configuration."""

    enabled: bool = True
    detect: NotificationsDetectConfig = field(default_factory=NotificationsDetectConfig)
    browser_tab: BrowserTabTargetConfig = field(default_factory=BrowserTabTargetConfig)
    web_push: WebPushTargetConfig = field(default_factory=WebPushTargetConfig)


def _parse_notifications(value: object) -> NotificationsConfig:
    notif = _ensure_map(value, "notifications")
    detect_raw = _ensure_map(notif.get("detect", {}), "notifications.detect")
    browser_raw = _ensure_map(notif.get("browser_tab", {}), "notifications.browser_tab")
    web_push_raw = _ensure_map(notif.get("web_push", {}), "notifications.web_push")
    return NotificationsConfig(
        enabled=_get_bool(notif, "enabled", True, "notifications.enabled"),
        detect=NotificationsDetectConfig(
            include_read=_get_bool(detect_raw, "include_read", False, "notifications.detect.include_read"),
            min_score=_get_float(detect_raw, "min_score", 0.0, "notifications.detect.min_score"),
        ),
        browser_tab=BrowserTabTargetConfig(
            enabled=_get_bool(browser_raw, "enabled", True, "notifications.browser_tab.enabled"),
            max_per_cycle=_get_int(browser_raw, "max_per_cycle", 5, "notifications.browser_tab.max_per_cycle"),
            cooldown_seconds=_get_int(
                browser_raw,
                "cooldown_seconds",
                10,
                "notifications.browser_tab.cooldown_seconds",
            ),
        ),
        web_push=WebPushTargetConfig(
            enabled=_get_bool(web_push_raw, "enabled", False, "notifications.web_push.enabled"),
            vapid_public_key_env=_get_str(
                web_push_raw,
                "vapid_public_key_env",
                "CORVIX_VAPID_PUBLIC_KEY",
                "notifications.web_push.vapid_public_key_env",
            ),
            vapid_private_key_env=_get_str(
                web_push_raw,
                "vapid_private_key_env",
                "CORVIX_VAPID_PRIVATE_KEY",
                "notifications.web_push.vapid_private_key_env",
            ),
            subject=_get_str(web_push_raw, "subject", "", "notifications.web_push.subject"),
        ),
    )
