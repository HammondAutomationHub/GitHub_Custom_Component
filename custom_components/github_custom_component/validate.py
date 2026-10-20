"""Validation used by the config flow. No Home Assistant imports."""

from __future__ import annotations

import aiohttp

from .errors import ArchiveError
from .github_client import GitHubClient
from .repo import folder_name_error, normalize_branch, parse_github_repo


async def validate_repository(
    session: aiohttp.ClientSession,
    token: str | None,
    repo_url: str,
    branch: str | None,
    folder: str,
) -> tuple[str, str]:
    """Confirm the repo, branch, and manifest exist. Returns slug and branch."""

    problem = folder_name_error(folder)
    if problem:
        raise ArchiveError(problem)
    parsed = parse_github_repo(repo_url)
    branch_name = normalize_branch(branch or parsed.branch)
    client = GitHubClient(session, token)
    await client.get_repo(parsed.owner, parsed.repo)
    await client.get_commit(parsed.owner, parsed.repo, branch_name)
    await client.get_manifest(parsed.owner, parsed.repo, branch_name, folder)
    return parsed.slug, branch_name
