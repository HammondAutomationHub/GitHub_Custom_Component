"""Check GitHub and decide whether an installed integration should update."""

from __future__ import annotations

from dataclasses import dataclass

from .github_client import GitHubClient
from .policy import Decision, decide_check
from .repo import version_displays


@dataclass(frozen=True)
class Evaluation:
    """Result of comparing the local integration with GitHub."""

    remote_sha: str
    remote_version: str
    commit_message: str
    local_version: str
    decision: Decision
    installed_display: str
    latest_display: str

    @property
    def update_available(self) -> bool:
        """Return whether the Update entity should offer an install."""

        return self.decision.update_available


async def evaluate_update(
    client: GitHubClient,
    *,
    owner: str,
    repo: str,
    branch: str,
    folder: str,
    local_version: str,
    bootstrapped: bool,
    installed_sha: str | None,
    update_mode: str,
) -> Evaluation:
    """Fetch the remote commit and manifest, then apply the update policy."""

    commit = await client.get_commit(owner, repo, branch)
    manifest = await client.get_manifest(owner, repo, branch, folder)
    decision = decide_check(
        previous_sha=installed_sha,
        previous_bootstrapped=bootstrapped,
        remote_sha=commit.sha,
        local_version=local_version,
        remote_version=manifest.version,
        update_mode=update_mode,
    )
    installed_display, latest_display = version_displays(
        local_version=local_version,
        local_sha=decision.installed_sha,
        remote_version=manifest.version,
        remote_sha=commit.sha,
    )
    return Evaluation(
        remote_sha=commit.sha,
        remote_version=manifest.version,
        commit_message=commit.message,
        local_version=local_version,
        decision=decision,
        installed_display=installed_display,
        latest_display=latest_display,
    )


def in_sync_displays(version: str) -> tuple[str, str]:
    """Version strings after a successful install of the commit just checked."""

    return version, version


def status_attributes(
    *,
    folder: str,
    repo: str,
    branch: str,
    installed_sha: str | None,
    remote_sha: str | None,
) -> dict[str, str | None]:
    """Extra state attributes. These must never include a token."""

    return {
        "folder": folder,
        "repository": repo,
        "branch": branch,
        "installed_commit": installed_sha,
        "latest_commit": remote_sha,
    }
