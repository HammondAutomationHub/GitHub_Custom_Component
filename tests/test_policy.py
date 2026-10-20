"""Update policy: first check, manual mode, and automatic mode."""

from __future__ import annotations

import pytest

from custom_components.gpm.policy import decide_check

REMOTE = "b" * 40


@pytest.mark.parametrize(
    ("local_version", "remote_version", "expected_sha", "available"),
    [
        ("1.0.0", "1.0.0", REMOTE, False),
        ("1.0.0", "1.1.0", None, True),
    ],
)
def test_first_check_never_installs(
    local_version: str, remote_version: str, expected_sha: str | None, available: bool
) -> None:
    decision = decide_check(
        previous_sha=None,
        previous_bootstrapped=False,
        remote_sha=REMOTE,
        local_version=local_version,
        remote_version=remote_version,
        update_mode="automatic",
    )
    assert decision.should_install is False
    assert decision.bootstrapped is True
    assert decision.installed_sha == expected_sha
    assert decision.update_available is available


def test_manual_mode_reports_later_commits_without_installing() -> None:
    decision = decide_check(
        previous_sha="a" * 40,
        previous_bootstrapped=True,
        remote_sha=REMOTE,
        local_version="1.0.0",
        remote_version="1.0.0",
        update_mode="manual",
    )
    assert decision.should_install is False
    assert decision.update_available is True
    assert decision.installed_sha == "a" * 40


def test_automatic_mode_installs_after_the_first_check() -> None:
    decision = decide_check(
        previous_sha="a" * 40,
        previous_bootstrapped=True,
        remote_sha=REMOTE,
        local_version="1.0.0",
        remote_version="1.1.0",
        update_mode="automatic",
    )
    assert decision.should_install is True
    assert decision.update_available is True


def test_matching_commit_is_not_an_update() -> None:
    decision = decide_check(
        previous_sha=REMOTE,
        previous_bootstrapped=True,
        remote_sha=REMOTE,
        local_version="1.0.0",
        remote_version="1.0.0",
        update_mode="automatic",
    )
    assert decision.should_install is False
    assert decision.update_available is False
