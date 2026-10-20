"""Errors raised by Component Update. Messages never include tokens or credentials."""

from __future__ import annotations


class ComponentUpdateError(Exception):
    """Base error with a config-flow error code."""

    code = "unknown"


class InvalidUrl(ComponentUpdateError):
    """Repository URL could not be parsed."""

    code = "invalid_url"


class InvalidAuth(ComponentUpdateError):
    """GitHub rejected the token or the token cannot read the repo."""

    code = "invalid_auth"


class RepoNotFound(ComponentUpdateError):
    """Repository does not exist or the token cannot see it."""

    code = "repo_not_found"


class BranchNotFound(ComponentUpdateError):
    """Branch or ref does not exist."""

    code = "branch_not_found"


class ManifestNotFound(ComponentUpdateError):
    """custom component manifest.json was not in the repository."""

    code = "manifest_not_found"


class ManifestMismatch(ComponentUpdateError):
    """manifest.json domain does not match the selected folder."""

    code = "manifest_mismatch"


class RateLimited(ComponentUpdateError):
    """GitHub API rate limit was reached."""

    code = "rate_limited"


class CannotConnect(ComponentUpdateError):
    """GitHub could not be reached or returned an unexpected error."""

    code = "cannot_connect"


class ArchiveError(ComponentUpdateError):
    """Downloaded archive was unsafe or not a valid component."""

    code = "archive_invalid"


class InvalidSchedule(ComponentUpdateError):
    """Automatic mode requires a periodic check interval."""

    code = "automatic_needs_interval"
