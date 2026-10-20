"""Tags and commits a user can install over the managed folder."""

from __future__ import annotations

from dataclasses import dataclass

from .const import VERSION_PROMPT


@dataclass(frozen=True)
class HistoryRef:
    """One installable tag or commit."""

    ref: str
    label: str


def build_history(*, tags: list[dict], commits: list[dict]) -> list[HistoryRef]:
    """Build a version list with tags first, then commits those tags do not cover."""

    entries: list[HistoryRef] = []
    seen_labels: set[str] = set()
    tag_shas: set[str] = set()

    for tag in tags:
        name = str(tag.get("name") or "").strip()
        sha = str((tag.get("commit") or {}).get("sha") or "")
        if not name or not sha:
            continue
        tag_shas.add(sha)
        entries.append(HistoryRef(ref=name, label=_unique(f"{name} ({sha[:7]})", seen_labels)))

    for commit in commits:
        sha = str(commit.get("sha") or "")
        if not sha or sha in tag_shas:
            continue
        message = str(((commit.get("commit") or {}).get("message") or "")).splitlines()
        title = message[0].strip() if message else "commit"
        if len(title) > 72:
            title = title[:69] + "..."
        entries.append(HistoryRef(ref=sha, label=_unique(f"{sha[:7]} {title}", seen_labels)))

    return entries


def _unique(label: str, seen: set[str]) -> str:
    if label == VERSION_PROMPT:
        label = f"{label} (commit)"
    candidate = label
    suffix = 2
    while candidate in seen:
        candidate = f"{label} ({suffix})"
        suffix += 1
    seen.add(candidate)
    return candidate
