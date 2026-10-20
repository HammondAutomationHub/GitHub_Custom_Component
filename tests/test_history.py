"""Version list used by the rollback dropdown."""

from __future__ import annotations

from custom_components.github_custom_component.history import build_history


def test_tags_are_listed_before_other_commits() -> None:
    tag_sha = "b" * 40
    older = "a" * 40
    history = build_history(
        tags=[{"name": "v1.2.0", "commit": {"sha": tag_sha}}],
        commits=[
            {"sha": tag_sha, "commit": {"message": "Release 1.2.0"}},
            {"sha": older, "commit": {"message": "Fix lights\n\nmore detail"}},
        ],
    )
    assert [item.ref for item in history] == ["v1.2.0", older]
    assert history[0].label == "v1.2.0 (bbbbbbb)"
    assert history[1].label == "aaaaaaa Fix lights"


def test_duplicate_labels_stay_distinct() -> None:
    sha = "b" * 40
    history = build_history(
        tags=[
            {"name": "v1.2.0", "commit": {"sha": sha}},
            {"name": "v1.2.0", "commit": {"sha": sha}},
        ],
        commits=[],
    )
    assert history[0].label == "v1.2.0 (bbbbbbb)"
    assert history[1].label == "v1.2.0 (bbbbbbb) (2)"
