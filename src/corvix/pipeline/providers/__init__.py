"""Built-in pipeline providers (field completion and context enrichment)."""

from corvix.pipeline.providers.github_latest_comment import GitHubLatestCommentProvider
from corvix.pipeline.providers.github_pr_state import GitHubPRStateProvider
from corvix.pipeline.providers.github_thread_subject import GitHubThreadSubjectProvider
from corvix.pipeline.providers.github_web_url import GitHubWebUrlProvider

__all__ = [
    "GitHubLatestCommentProvider",
    "GitHubPRStateProvider",
    "GitHubThreadSubjectProvider",
    "GitHubWebUrlProvider",
]
