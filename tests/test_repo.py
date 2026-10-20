"""Repository parsing, version labels, and schedule rules."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.github_custom_component.const import CHECK_INTERVALS, UPDATE_MODES
from custom_components.github_custom_component.errors import InvalidSchedule, InvalidUrl
from custom_components.github_custom_component.policy import persisted_state
from custom_components.github_custom_component.repo import (
    normalize_branch,
    parse_github_repo,
    redact_config,
    schedule_error,
    version_displays,
)
from custom_components.github_custom_component.updater import status_attributes

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("value", "slug", "branch"),
    [
        ("owner/repo", "owner/repo", None),
        ("https://github.com/owner/repo", "owner/repo", None),
        ("https://github.com/owner/repo/", "owner/repo", None),
        ("https://github.com/owner/repo.git", "owner/repo", None),
        ("https://github.com/owner/repo/tree/develop", "owner/repo", "develop"),
        ("https://github.com/owner/repo/tree/feature/one", "owner/repo", "feature/one"),
        ("git@github.com:owner/repo.git", "owner/repo", None),
    ],
)
def test_parse_github_repo(value: str, slug: str, branch: str | None) -> None:
    parsed = parse_github_repo(value)
    assert parsed.slug == slug
    assert parsed.branch == branch


def test_embedded_token_is_rejected_without_echoing_it() -> None:
    token = "ghp_super_secret_value"
    with pytest.raises(InvalidUrl) as caught:
        parse_github_repo(f"https://user:{token}@github.com/owner/repo")
    assert token not in str(caught.value)


@pytest.mark.parametrize(
    "value",
    [
        "https://gitlab.com/owner/repo",
        "https://github.com/owner",
        "not a repo",
        "http://github.com/owner/repo",
    ],
)
def test_parse_rejects_non_github_locations(value: str) -> None:
    with pytest.raises(InvalidUrl):
        parse_github_repo(value)


def test_version_display_uses_commit_when_manifest_version_is_unchanged() -> None:
    installed, latest = version_displays(
        local_version="1.0.0",
        local_sha="a" * 40,
        remote_version="1.0.0",
        remote_sha="b" * 40,
    )
    assert installed == "1.0.0 (aaaaaaa)"
    assert latest == "1.0.0 (bbbbbbb)"


def test_version_display_hides_commit_when_already_installed() -> None:
    sha = "c" * 40
    installed, latest = version_displays(
        local_version="1.2.0",
        local_sha=sha,
        remote_version="1.2.0",
        remote_sha=sha,
    )
    assert installed == latest == "1.2.0"


def test_automatic_mode_requires_a_schedule() -> None:
    with pytest.raises(InvalidSchedule):
        schedule_error("automatic", "manual")
    schedule_error("automatic", "daily")
    schedule_error("manual", "manual")


def test_branch_normalization() -> None:
    assert normalize_branch("") == "main"
    assert normalize_branch(" develop ") == "develop"
    with pytest.raises(InvalidUrl):
        normalize_branch("../main")


def test_redaction_and_attributes_do_not_carry_a_token() -> None:
    redacted = redact_config({"repo": "owner/repo", "token": "ghp_secret"})
    assert redacted["token"] == "configured"
    assert "ghp_secret" not in json.dumps(redacted)
    assert redact_config({"token": ""})["token"] == "not set"
    attrs = status_attributes(
        folder="demo",
        repo="owner/repo",
        branch="main",
        installed_sha="abc",
        remote_sha="def",
    )
    assert "token" not in attrs
    stored = persisted_state(bootstrapped=True, installed_sha="abc")
    assert set(stored) == {"bootstrapped", "installed_sha", "paused"}
    assert stored["paused"] is False


def test_check_intervals_match_the_ui_strings() -> None:
    strings = json.loads((ROOT / "custom_components" / "github_custom_component" / "strings.json").read_text())
    english = json.loads(
        (ROOT / "custom_components" / "github_custom_component" / "translations" / "en.json").read_text()
    )
    assert english == strings
    assert set(strings["selector"]["check_interval"]["options"]) == set(CHECK_INTERVALS)
    assert set(strings["selector"]["update_mode"]["options"]) == set(UPDATE_MODES)
    assert CHECK_INTERVALS["manual"] is None
    assert CHECK_INTERVALS["hourly"].total_seconds() == 3600
    assert CHECK_INTERVALS["daily"].days == 1
    assert CHECK_INTERVALS["weekly"].days == 7
