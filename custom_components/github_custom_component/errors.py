"""Errors raised by GitHub - Custom_Component. Messages never include tokens or credentials."""

from __future__ import annotations


class GitHubCustomComponentError(Exception):
    """Base error with a config-flow error code."""

    code = "unknown"


class InvalidUrl(GitHubCustomComponentError):
    """Repository URL could not be parsed."""

    code = "invalid_url"


class InvalidAuth(GitHubCustomComponentError):
    """GitHub rejected the token or the token cannot read the repo."""

    code = "invalid_auth"


class RepoNotFound(GitHubCustomComponentError):
    """Repository does not exist or the token cannot see it."""

    code = "repo_not_found"


class BranchNotFound(GitHubCustomComponentError):
    """Branch or ref does not exist."""

    code = "branch_not_found"


class ManifestNotFound(GitHubCustomComponentError):
    """custom component manifest.json was not in the repository."""

    code = "manifest_not_found"


class ManifestMismatch(GitHubCustomComponentError):
    """manifest.json domain does not match the selected folder."""

    code = "manifest_mismatch"


class RateLimited(GitHubCustomComponentError):
    """GitHub API rate limit was reached."""

    code = "rate_limited"


class CannotConnect(GitHubCustomComponentError):
    """GitHub could not be reached or returned an unexpected error."""

    code = "cannot_connect"


class ArchiveError(GitHubCustomComponentError):
    """Downloaded archive was unsafe or not a valid component."""

    code = "archive_invalid"


class InvalidSchedule(GitHubCustomComponentError):
    """Automatic mode requires a periodic check interval."""

    code = "automatic_needs_interval"
