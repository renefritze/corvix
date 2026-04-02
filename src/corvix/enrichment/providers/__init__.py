"""Built-in enrichment providers."""

from corvix.enrichment.providers.github_latest_comment import GitHubLatestCommentProvider
from corvix.enrichment.providers.github_pr_state import GitHubPRStateProvider

__all__ = ["GitHubLatestCommentProvider", "GitHubPRStateProvider"]
