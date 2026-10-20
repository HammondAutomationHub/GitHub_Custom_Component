"""Parse GitHub repositories and build version strings for the UI."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .const import DEFAULT_BRANCH
from .errors import InvalidSchedule, InvalidUrl

_OWNER = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?"
_REPO = r"[A-Za-z0-9._-]{1,100}"
_HTTPS = re.compile(
    rf"^https://github\.com/(?P<owner>{_OWNER})/(?P<repo>{_REPO})(?:\.git)?"
    rf"(?:/tree/(?P<branch>[^\s?#]+))?/?$",
    re.IGNORECASE,
)
_SSH = re.compile(
    rf"^git@github\.com:(?P<owner>{_OWNER})/(?P<repo>{_REPO})(?:\.git)?$",
    re.IGNORECASE,
)
_SLUG = re.compile(rf"^(?P<owner>{_OWNER})/(?P<repo>{_REPO})$")
_FOLDER = re.compile(r"[a-zA-Z][a-zA-Z0-9_]*$")


@dataclass(frozen=True)
class ParsedRepo:
    """A GitHub owner/repo pair and an optional branch taken from the URL."""

    owner: str
    repo: str
    branch: str | None = None

    @property
    def slug(self) -> str:
        """Return ``owner/repo``."""

        return f"{self.owner}/{self.repo}"


def parse_github_repo(value: str) -> ParsedRepo:
    """Parse a GitHub URL or ``owner/repo`` slug.

    Credentials embedded in the URL are rejected so a token is never taken
    from a string that might later be written to a log.
    """

    raw = value.strip()
    if not raw or raw.startswith("-"):
        raise InvalidUrl("Enter a GitHub repository URL or owner/repo.")

    if "://" in raw:
        authority = raw.split("://", 1)[1].split("/", 1)[0]
        if "@" in authority:
            raise InvalidUrl("Remove credentials from the URL and use the token field.")
    if raw.lower().startswith("http://"):
        raise InvalidUrl("Use an https://github.com URL.")
    if "github.com" not in raw.lower() and "/" in raw and not raw.lower().startswith("git@"):
        # owner/repo is allowed; other hosts are not.
        if not _SLUG.match(raw):
            raise InvalidUrl("Only github.com repositories are supported.")

    lowered_host = raw.lower()
    if "://" in lowered_host or lowered_host.startswith("git@"):
        if "github.com" not in lowered_host:
            raise InvalidUrl("Only github.com repositories are supported.")

    for pattern in (_HTTPS, _SSH):
        match = pattern.match(raw)
        if match:
            branch = match.groupdict().get("branch")
            return ParsedRepo(
                match.group("owner"),
                _strip_git_suffix(match.group("repo")),
                _clean_branch(branch),
            )

    match = _SLUG.match(raw)
    if match:
        return ParsedRepo(
            match.group("owner"), _strip_git_suffix(match.group("repo")), None
        )

    raise InvalidUrl("Enter a GitHub repository URL or owner/repo.")


def _strip_git_suffix(repo: str) -> str:
    if repo.lower().endswith(".git"):
        return repo[: -len(".git")]
    return repo


def _clean_branch(branch: str | None) -> str | None:
    if not branch:
        return None
    branch = branch.strip("/")
    if not branch or ".." in branch.split("/"):
        raise InvalidUrl("The branch in that URL is not valid.")
    return branch


def folder_name_error(folder: str) -> str | None:
    """Return an error message when a folder name is not safe to write to."""

    if folder == "component_update":
        return "Component Update will not update its own folder."
    if not _FOLDER.match(folder):
        return "Integration folder names must be letters, numbers, and underscores."
    return None


def version_displays(
    *,
    local_version: str,
    local_sha: str | None,
    remote_version: str,
    remote_sha: str,
) -> tuple[str, str]:
    """Return installed and latest strings for an Update entity.

    When the manifest versions match but the commits do not, the short commit
    is included so Home Assistant still shows an available update.
    """

    if local_sha and local_sha == remote_sha:
        return local_version, remote_version

    if local_version != remote_version:
        return local_version, remote_version

    local_label = f"{local_version} ({local_sha[:7]})" if local_sha else local_version
    return local_label, f"{remote_version} ({remote_sha[:7]})"


def schedule_error(update_mode: str, check_interval: str) -> None:
    """Reject automatic installs that have no schedule to run on."""

    if update_mode == "automatic" and check_interval == "manual":
        raise InvalidSchedule(
            "Automatic updates need an hourly, daily, or weekly check."
        )


def redact_config(data: dict) -> dict:
    """Return config data safe to put in diagnostics and logs."""

    redacted = dict(data)
    token = redacted.get("token") or ""
    redacted["token"] = "configured" if token else "not set"
    return redacted


def split_slug(slug: str) -> tuple[str, str]:
    """Split ``owner/repo`` into its parts."""

    parsed = parse_github_repo(slug)
    if parsed.branch:
        raise InvalidUrl("Stored repository must be owner/repo.")
    return parsed.owner, parsed.repo


def normalize_branch(branch: str | None) -> str:
    """Return a branch name, falling back to main."""

    cleaned = (branch or "").strip()
    if not cleaned:
        return DEFAULT_BRANCH
    if ".." in cleaned.split("/") or cleaned.startswith("/") or " " in cleaned:
        raise InvalidUrl("Branch name is not valid.")
    return cleaned
