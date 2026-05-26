"""GitHub account configuration model and YAML parsing."""

from __future__ import annotations

from dataclasses import dataclass, field

from corvix.config._utils import (
    _ensure_list,
    _ensure_map,
    _get_str,
)

DEFAULT_GITHUB_API_BASE_URL = "https://api.github.com"


@dataclass(slots=True)
class GitHubAccountConfig:
    """One GitHub account configuration for multi-account polling."""

    id: str
    label: str
    token_env: str
    api_base_url: str = DEFAULT_GITHUB_API_BASE_URL


@dataclass(slots=True)
class GitHubConfig:
    """GitHub API configuration."""

    accounts: list[GitHubAccountConfig] = field(default_factory=list)

    @property
    def token_env(self) -> str:
        """Backward-compatible shortcut to first account token env."""
        return self.accounts[0].token_env if self.accounts else "GITHUB_TOKEN"

    @property
    def api_base_url(self) -> str:
        """Backward-compatible shortcut to first account API base URL."""
        return self.accounts[0].api_base_url if self.accounts else DEFAULT_GITHUB_API_BASE_URL


def _parse_github(value: object) -> GitHubConfig:
    github = _ensure_map(value, "github")
    fallback_token_env = _get_str(github, "token_env", "GITHUB_TOKEN", "github.token_env")
    fallback_api_base_url = _get_str(
        github,
        "api_base_url",
        DEFAULT_GITHUB_API_BASE_URL,
        "github.api_base_url",
    )
    if "accounts" not in github:
        raw_accounts: list[object] = [{"label": "Primary"}]
    else:
        raw_accounts = _ensure_list(github.get("accounts", []), "github.accounts")
    if "accounts" in github and not raw_accounts:
        msg = "Config section 'github.accounts' must contain at least one account."
        raise ValueError(msg)
    accounts: list[GitHubAccountConfig] = []
    seen_ids: set[str] = set()
    for index, raw_account in enumerate(raw_accounts):
        account = _ensure_map(raw_account, f"github.accounts[{index}]")
        account_id = _get_str(account, "id", "primary", f"github.accounts[{index}].id").strip()
        if not account_id:
            msg = f"Config field 'github.accounts[{index}].id' is required."
            raise ValueError(msg)
        if account_id in seen_ids:
            msg = f"Config field 'github.accounts[{index}].id' must be unique ('{account_id}')."
            raise ValueError(msg)
        seen_ids.add(account_id)
        label = _get_str(account, "label", account_id, f"github.accounts[{index}].label").strip() or account_id
        token_env = _get_str(account, "token_env", fallback_token_env, f"github.accounts[{index}].token_env").strip()
        if not token_env:
            msg = f"Config field 'github.accounts[{index}].token_env' is required."
            raise ValueError(msg)
        api_base_url = _get_str(
            account,
            "api_base_url",
            fallback_api_base_url,
            f"github.accounts[{index}].api_base_url",
        )
        accounts.append(
            GitHubAccountConfig(
                id=account_id,
                label=label,
                token_env=token_env,
                api_base_url=api_base_url,
            )
        )
    return GitHubConfig(accounts=accounts)
