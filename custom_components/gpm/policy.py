"""Pure decisions for when GPM checks and installs. No I/O."""

from __future__ import annotations

from dataclasses import dataclass

from .const import UPDATE_MODE_AUTOMATIC


@dataclass(frozen=True)
class Decision:
    """What to persist and whether this check should install."""

    installed_sha: str | None
    bootstrapped: bool
    should_install: bool
    update_available: bool


def decide_check(
    *,
    previous_sha: str | None,
    previous_bootstrapped: bool,
    remote_sha: str,
    local_version: str,
    remote_version: str,
    update_mode: str,
    pinned: bool = False,
) -> Decision:
    """Decide the outcome of a repository check.

    The first check never installs. If the local manifest version already
    matches the remote manifest, that remote commit is recorded as installed
    so an unchanged HACS copy is not flagged as an update.

    A pinned folder stays on the commit the user chose. Automatic mode will
    not replace it with the branch tip.
    """

    if not previous_bootstrapped:
        installed_sha = remote_sha if local_version == remote_version else previous_sha
        return Decision(
            installed_sha=installed_sha,
            bootstrapped=True,
            should_install=False,
            update_available=installed_sha != remote_sha,
        )

    update_available = previous_sha != remote_sha
    return Decision(
        installed_sha=previous_sha,
        bootstrapped=True,
        should_install=update_mode == UPDATE_MODE_AUTOMATIC
        and update_available
        and not pinned,
        update_available=update_available,
    )


def persisted_state(
    *, bootstrapped: bool, installed_sha: str | None, pinned: bool = False
) -> dict:
    """State written to Home Assistant storage. Tokens are never included."""

    return {
        "bootstrapped": bootstrapped,
        "installed_sha": installed_sha,
        "pinned": pinned,
    }
