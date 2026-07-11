"""Notification action helpers: dismiss and mark-read against GitHub + storage.

These plain (non-decorated) functions carry the business logic behind the
``/api/v1/notifications/{account_id}/{thread_id}/dismiss`` and ``.../mark-read``
route handlers.  ``_require_account`` and ``_build_github_client`` are shared
with the rule-snippet builder.
"""

from __future__ import annotations

import logging

from litestar import Response
from litestar.exceptions import HTTPException

from corvix.config import AppConfig, GitHubAccountConfig
from corvix.env import get_env_value
from corvix.ingestion import GitHubNotificationsClient
from corvix.web.runtime_config import _load_runtime_config
from corvix.web.storage_provider import _get_storage

logger = logging.getLogger(__name__)


def _require_account(config: AppConfig, account_id: str) -> GitHubAccountConfig:
    for account in config.github.accounts:
        if account.id == account_id:
            return account
    msg = f"GitHub account '{account_id}' not found in config."
    raise HTTPException(status_code=404, detail=msg)


def _build_github_client(config: AppConfig, account: GitHubAccountConfig, token: str) -> GitHubNotificationsClient:
    return GitHubNotificationsClient(
        token=token,
        api_base_url=account.api_base_url,
        request_timeout_seconds=config.polling.request_timeout_seconds,
    )


def _dismiss_notification_impl(account_id: str, thread_id: str) -> Response[None]:
    config = _load_runtime_config()
    account = _require_account(config=config, account_id=account_id)
    try:
        token = get_env_value(account.token_env)
    except ValueError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    if not token:
        msg = f"GitHub token env var '{account.token_env}' (or '{account.token_env}_FILE') is not set."
        raise HTTPException(status_code=500, detail=msg)
    client = _build_github_client(config=config, account=account, token=token)
    try:
        client.dismiss_thread(thread_id)
    except Exception as error:
        logger.exception("Failed to dismiss thread", extra={"thread_id": thread_id})
        msg = f"Failed to dismiss thread {thread_id}: {error}"
        raise HTTPException(status_code=502, detail=msg) from error

    _get_storage().dismiss_record(thread_id=thread_id, account_id=account_id)
    return Response(content=None, status_code=204)


def _mark_notification_read_impl(account_id: str, thread_id: str) -> Response[None]:
    config = _load_runtime_config()
    account = _require_account(config=config, account_id=account_id)
    try:
        token = get_env_value(account.token_env)
    except ValueError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    if not token:
        msg = f"GitHub token env var '{account.token_env}' (or '{account.token_env}_FILE') is not set."
        raise HTTPException(status_code=500, detail=msg)

    client = _build_github_client(config=config, account=account, token=token)
    try:
        client.mark_thread_read(thread_id)
    except Exception as error:
        logger.exception("Failed to mark thread as read", extra={"thread_id": thread_id})
        msg = f"Failed to mark thread {thread_id} as read."
        raise HTTPException(status_code=502, detail=msg) from error

    _get_storage().mark_record_read(thread_id=thread_id, account_id=account_id)
    return Response(content=None, status_code=204)
