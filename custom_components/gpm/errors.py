"""Errors raised by GPM. Messages never include tokens or credentials."""

from __future__ import annotations


class GPMError(Exception):
    """Base error with a config-flow error code."""

    code = "unknown"


class InvalidUrl(GPMError):
    """Repository URL could not be parsed."""

    code = "invalid_url"


class InvalidAuth(GPMError):
    """GitHub rejected the token or the token cannot read the repo."""

    code = "invalid_auth"


class RepoNotFound(GPMError):
    """Repository does not exist or the token cannot see it."""

    code = "repo_not_found"


class BranchNotFound(GPMError):
    """Branch or ref does not exist."""

    code = "branch_not_found"


class ManifestNotFound(GPMError):
    """custom component manifest.json was not in the repository."""

    code = "manifest_not_found"


class ManifestMismatch(GPMError):
    """manifest.json domain does not match the selected folder."""

    code = "manifest_mismatch"


class RateLimited(GPMError):
    """GitHub API rate limit was reached."""

    code = "rate_limited"


class CannotConnect(GPMError):
    """GitHub could not be reached or returned an unexpected error."""

    code = "cannot_connect"


class ArchiveError(GPMError):
    """Downloaded archive was unsafe or not a valid component."""

    code = "archive_invalid"


class InvalidSchedule(GPMError):
    """Automatic mode requires a periodic check interval."""

    code = "automatic_needs_interval"
