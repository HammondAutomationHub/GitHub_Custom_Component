"""Minimal GitHub REST client for private and public repositories."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

import aiohttp

from .const import GITHUB_API, HISTORY_LIMIT, MAX_DOWNLOAD_BYTES, USER_AGENT
from .errors import (
    ArchiveError,
    BranchNotFound,
    CannotConnect,
    InvalidAuth,
    ManifestMismatch,
    ManifestNotFound,
    RateLimited,
    RepoNotFound,
)
from .history import HistoryRef, build_history

_API_TIMEOUT = aiohttp.ClientTimeout(total=30)
_DOWNLOAD_TIMEOUT = aiohttp.ClientTimeout(total=180)


def _seg(value: str) -> str:
    """URL-encode one path segment, including slashes in branch names."""

    return quote(value, safe="")


@dataclass(frozen=True)
class RepoMeta:
    """Repository metadata needed during setup."""

    private: bool
    default_branch: str


@dataclass(frozen=True)
class CommitInfo:
    """A commit GitHub - Custom_Component can install."""

    sha: str
    message: str


@dataclass(frozen=True)
class RemoteManifest:
    """manifest.json fetched from the repository without downloading the archive."""

    version: str
    domain: str
    path: str


class _NotFound(Exception):
    """Internal 404 marker so callers can map it to a specific error."""


class GitHubClient:
    """Call the GitHub API. The token is sent only to the configured API host."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: str | None,
        api_base: str = GITHUB_API,
    ) -> None:
        self._session = session
        self._token = token.strip() if token else ""
        self._api_base = api_base.rstrip("/")

    async def get_repo(self, owner: str, repo: str) -> RepoMeta:
        """Return whether the repo is private and its default branch."""

        try:
            data = await self._get_json(f"{self._api_base}/repos/{_seg(owner)}/{_seg(repo)}")
        except _NotFound as err:
            raise RepoNotFound(
                "Repository not found. If it is private, the token needs access to it."
            ) from err
        return RepoMeta(
            private=bool(data.get("private")),
            default_branch=str(data.get("default_branch") or "main"),
        )

    async def get_commit(self, owner: str, repo: str, ref: str) -> CommitInfo:
        """Return the commit currently at a branch, tag, or sha."""

        url = f"{self._api_base}/repos/{_seg(owner)}/{_seg(repo)}/commits/{_seg(ref)}"
        try:
            data = await self._get_json(url)
        except _NotFound as err:
            raise BranchNotFound(f"Branch or ref {ref!r} was not found.") from err
        commit = data.get("commit") or {}
        message = str(commit.get("message") or "")
        sha = str(data.get("sha") or "")
        if not sha:
            raise CannotConnect("GitHub did not return a commit.")
        return CommitInfo(sha=sha, message=message[:4000])

    async def list_history(self, owner: str, repo: str, branch: str) -> list[HistoryRef]:
        """Return recent tags and commits that can be installed."""

        tags = await self._get_list(
            f"{self._api_base}/repos/{_seg(owner)}/{_seg(repo)}/tags?per_page={HISTORY_LIMIT}"
        )
        commits = await self._get_list(
            f"{self._api_base}/repos/{_seg(owner)}/{_seg(repo)}/commits"
            f"?sha={_seg(branch)}&per_page={HISTORY_LIMIT}"
        )
        return build_history(tags=tags, commits=commits)

    async def get_manifest(
        self, owner: str, repo: str, ref: str, folder: str
    ) -> RemoteManifest:
        """Load the component manifest for ``folder`` at ``ref``."""

        paths = [
            f"custom_components/{folder}/manifest.json",
            "manifest.json",
        ]
        mismatch: ManifestMismatch | None = None
        for path in paths:
            try:
                text = await self.get_text_file(owner, repo, path, ref)
            except ManifestNotFound:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError as err:
                raise ManifestNotFound("Remote manifest.json is not valid JSON.") from err
            domain = data.get("domain")
            if domain != folder:
                mismatch = ManifestMismatch(
                    f"Remote manifest domain is {domain!r}, expected {folder!r}."
                )
                if path != "manifest.json":
                    raise mismatch
                continue
            return RemoteManifest(
                version=str(data.get("version") or "0"),
                domain=str(domain),
                path=path,
            )
        if mismatch:
            raise mismatch
        raise ManifestNotFound(
            f"Could not find manifest.json for {folder} in the repository."
        )

    async def get_text_file(self, owner: str, repo: str, path: str, ref: str) -> str:
        """Return a small text file from the contents API."""

        encoded_path = "/".join(_seg(part) for part in path.split("/"))
        url = (
            f"{self._api_base}/repos/{_seg(owner)}/{_seg(repo)}/contents/{encoded_path}"
            f"?ref={_seg(ref)}"
        )
        try:
            payload = await self._get_json(url)
        except _NotFound as err:
            raise ManifestNotFound(f"{path} was not found at {ref}.") from err
        if payload.get("encoding") != "base64" or "content" not in payload:
            raise ManifestNotFound(f"{path} is not a readable file.")
        try:
            return base64.b64decode(payload["content"]).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as err:
            raise ManifestNotFound(f"{path} could not be decoded.") from err

    async def download_archive(
        self,
        owner: str,
        repo: str,
        ref: str,
        dest: Path,
        max_bytes: int = MAX_DOWNLOAD_BYTES,
    ) -> None:
        """Download a zipball for an exact commit sha."""

        url = f"{self._api_base}/repos/{_seg(owner)}/{_seg(repo)}/zipball/{_seg(ref)}"
        try:
            await self._download(url, dest, max_bytes)
        except _NotFound as err:
            raise RepoNotFound("Archive was not found for that commit.") from err

    def _headers(self, *, include_auth: bool) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if include_auth and self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _get_json(self, url: str) -> dict:
        data = await self._request_json(url)
        if not isinstance(data, dict):
            raise CannotConnect("GitHub returned an unexpected response.")
        return data

    async def _get_list(self, url: str) -> list:
        try:
            data = await self._request_json(url)
        except _NotFound:
            return []
        if not isinstance(data, list):
            return []
        return data

    async def _request_json(self, url: str) -> dict | list:
        try:
            async with self._session.get(
                url, headers=self._headers(include_auth=True), timeout=_API_TIMEOUT
            ) as response:
                self._raise_for_status(response)
                data = await response.json(content_type=None)
        except _NotFound:
            raise
        except (aiohttp.ClientError, ValueError) as err:
            raise CannotConnect("Could not reach GitHub.") from err
        if not isinstance(data, (dict, list)):
            raise CannotConnect("GitHub returned an unexpected response.")
        return data

    async def _download(self, url: str, dest: Path, max_bytes: int) -> None:
        current = url
        send_auth = True
        api_host = urlparse(self._api_base).netloc
        for _ in range(5):
            try:
                async with self._session.get(
                    current,
                    headers=self._headers(include_auth=send_auth),
                    allow_redirects=False,
                    timeout=_DOWNLOAD_TIMEOUT,
                ) as response:
                    if response.status in {301, 302, 303, 307, 308}:
                        location = response.headers.get("Location")
                        if not location:
                            raise CannotConnect("GitHub redirect was missing a location.")
                        current = urljoin(str(response.url), location)
                        # The PAT stays on the API host. GitHub puts a temporary
                        # credential in the codeload redirect URL.
                        send_auth = urlparse(current).netloc == api_host
                        continue
                    self._raise_for_status(response)
                    await self._write_body(response, dest, max_bytes)
                    return
            except aiohttp.ClientError as err:
                raise CannotConnect("Could not reach GitHub.") from err
        raise CannotConnect("GitHub redirected too many times.")

    async def _write_body(
        self, response: aiohttp.ClientResponse, dest: Path, max_bytes: int
    ) -> None:
        size = 0
        try:
            with dest.open("wb") as handle:
                async for chunk in response.content.iter_chunked(65536):
                    size += len(chunk)
                    if size > max_bytes:
                        raise ArchiveError("Repository archive exceeds the size limit.")
                    handle.write(chunk)
        except ArchiveError:
            dest.unlink(missing_ok=True)
            raise
        if size == 0:
            dest.unlink(missing_ok=True)
            raise ArchiveError("GitHub returned an empty archive.")

    def _raise_for_status(self, response: aiohttp.ClientResponse) -> None:
        if response.status == 401:
            raise InvalidAuth("GitHub rejected the token.")
        if response.status == 403:
            if response.headers.get("X-RateLimit-Remaining") == "0":
                raise RateLimited("GitHub API rate limit reached. Try again later.")
            raise InvalidAuth("GitHub forbidden this request. Check the token access.")
        if response.status == 404:
            raise _NotFound
        if response.status >= 400:
            raise CannotConnect(f"GitHub returned HTTP {response.status}.")
