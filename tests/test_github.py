"""GitHub client, config validation, and a private-repo update."""

from __future__ import annotations

import base64
import json
from pathlib import Path
import zipfile

import aiohttp
from aiohttp import web
import pytest

from custom_components.github_custom_component.const import UPDATE_MODE_AUTOMATIC, UPDATE_MODE_MANUAL
from custom_components.github_custom_component.errors import (
    ArchiveError,
    BranchNotFound,
    InvalidAuth,
    ManifestMismatch,
    RateLimited,
    RepoNotFound,
)
from custom_components.github_custom_component.github_client import GitHubClient
from custom_components.github_custom_component.installer import install_archive
from custom_components.github_custom_component.updater import evaluate_update
from custom_components.github_custom_component.validate import validate_repository

TOKEN = "ghp_test_token_do_not_log"


def open_session() -> aiohttp.ClientSession:
    """Use a threaded resolver so Windows tests are not stuck on aiodns."""

    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    return aiohttp.ClientSession(connector=connector)


class FakeGitHub:
    """Small stand-in for the GitHub REST API."""

    def __init__(self) -> None:
        self.private = True
        self.branch = "main"
        self.sha = "a" * 40
        self.version = "1.2.0"
        self.domain = "demo"
        self.folder = "demo"
        self.message = "Release 1.2.0"
        self.rate_limit = False
        self.zip_bytes = b""
        self.redirect_to: str | None = None
        self.api_authorization: str | None = None
        self.redirect_authorization: str | None = None
        self.manifest_paths = {
            "custom_components/demo/manifest.json",
        }

    def manifest_body(self) -> dict:
        raw = json.dumps(
            {"domain": self.domain, "name": "Demo", "version": self.version}
        ).encode()
        return {
            "type": "file",
            "encoding": "base64",
            "content": base64.b64encode(raw).decode(),
        }

    def authorized(self, request: web.Request) -> web.Response | None:
        authorization = request.headers.get("Authorization")
        if self.rate_limit:
            return web.Response(status=403, headers={"X-RateLimit-Remaining": "0"})
        if self.private and authorization != f"Bearer {TOKEN}":
            if authorization:
                return web.Response(status=401, text="bad token")
            return web.Response(status=404, text="hidden")
        return None


async def start_site(app: web.Application) -> tuple[web.AppRunner, str]:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = runner.addresses[0][1]
    return runner, f"http://127.0.0.1:{port}"


@pytest.fixture
async def github():
    """Yield a fake API base URL and the mutable GitHub state."""

    state = FakeGitHub()

    async def repo(request: web.Request) -> web.Response:
        denied = state.authorized(request)
        if denied is not None:
            return denied
        return web.json_response({"private": state.private, "default_branch": "main"})

    async def commit(request: web.Request) -> web.Response:
        denied = state.authorized(request)
        if denied is not None:
            return denied
        if request.match_info["ref"] != state.branch and request.match_info["ref"] != state.sha:
            return web.Response(status=404)
        return web.json_response({"sha": state.sha, "commit": {"message": state.message}})

    async def contents(request: web.Request) -> web.Response:
        denied = state.authorized(request)
        if denied is not None:
            return denied
        path = request.match_info["path"]
        if path not in state.manifest_paths:
            return web.Response(status=404)
        return web.json_response(state.manifest_body())

    async def zipball(request: web.Request) -> web.Response:
        state.api_authorization = request.headers.get("Authorization")
        denied = state.authorized(request)
        if denied is not None:
            return denied
        if state.redirect_to:
            raise web.HTTPFound(state.redirect_to)
        return web.Response(body=state.zip_bytes, content_type="application/zip")

    app = web.Application()
    app.router.add_get("/repos/{owner}/{repo}", repo)
    app.router.add_get("/repos/{owner}/{repo}/commits/{ref}", commit)
    app.router.add_get("/repos/{owner}/{repo}/contents/{path:.*}", contents)
    app.router.add_get("/repos/{owner}/{repo}/zipball/{ref}", zipball)
    runner, base = await start_site(app)

    async def redirected(request: web.Request) -> web.Response:
        state.redirect_authorization = request.headers.get("Authorization")
        return web.Response(body=state.zip_bytes, content_type="application/zip")

    redirect_app = web.Application()
    redirect_app.router.add_get("/zip", redirected)
    redirect_runner, redirect_base = await start_site(redirect_app)
    state.redirect_base = redirect_base  # type: ignore[attr-defined]
    try:
        yield state, base
    finally:
        await runner.cleanup()
        await redirect_runner.cleanup()


@pytest.mark.asyncio
async def test_private_repo_requires_a_token(github) -> None:
    state, base = github
    async with open_session() as session:
        client = GitHubClient(session, "", api_base=base)
        with pytest.raises(RepoNotFound):
            await client.get_repo("owner", "demo")
        client = GitHubClient(session, "wrong-token", api_base=base)
        with pytest.raises(InvalidAuth) as caught:
            await client.get_repo("owner", "demo")
        assert TOKEN not in str(caught.value)
        assert "wrong-token" not in str(caught.value)


@pytest.mark.asyncio
async def test_missing_branch_is_reported(github) -> None:
    _state, base = github
    async with open_session() as session:
        client = GitHubClient(session, TOKEN, api_base=base)
        with pytest.raises(BranchNotFound):
            await client.get_commit("owner", "demo", "missing")


@pytest.mark.asyncio
async def test_validate_repository_against_the_fake_api(github, monkeypatch) -> None:
    state, base = github
    monkeypatch.setattr(
        "custom_components.github_custom_component.validate.GitHubClient",
        lambda session, token: GitHubClient(session, token, api_base=base),
    )
    async with open_session() as session:
        slug, branch = await validate_repository(
            session, TOKEN, "owner/demo", "main", "demo"
        )
        assert (slug, branch) == ("owner/demo", "main")
        state.domain = "other"
        with pytest.raises(ManifestMismatch):
            await validate_repository(session, TOKEN, "owner/demo", "main", "demo")
        state.domain = "demo"
        state.rate_limit = True
        with pytest.raises(RateLimited):
            await validate_repository(session, TOKEN, "owner/demo", "main", "demo")


@pytest.mark.asyncio
async def test_download_does_not_send_the_token_to_the_redirect_host(github, tmp_path: Path) -> None:
    state, base = github
    state.redirect_to = f"{state.redirect_base}/zip"
    state.zip_bytes = b"PK\x05\x06" + b"\x00" * 18
    async with open_session() as session:
        client = GitHubClient(session, TOKEN, api_base=base)
        dest = tmp_path / "repo.zip"
        await client.download_archive("owner", "demo", state.sha, dest, max_bytes=100)
    assert state.api_authorization == f"Bearer {TOKEN}"
    assert state.redirect_authorization is None
    assert dest.is_file()


@pytest.mark.asyncio
async def test_download_rejects_oversized_archives(github, tmp_path: Path) -> None:
    state, base = github
    state.zip_bytes = b"0123456789abcdef"
    async with open_session() as session:
        client = GitHubClient(session, TOKEN, api_base=base)
        with pytest.raises(ArchiveError) as caught:
            await client.download_archive(
                "owner", "demo", "a" * 40, tmp_path / "big.zip", max_bytes=8
            )
    assert "size" in str(caught.value).lower()


@pytest.mark.asyncio
async def test_private_repo_check_then_install(github, tmp_path: Path) -> None:
    """Walk the user-facing sequence: detect an update, then install that commit."""

    state, base = github
    state.sha = "b" * 40
    state.version = "1.2.0"
    state.message = "Add private-repo fix"
    archive = tmp_path / "built.zip"
    prefix = "owner-demo-bbbbbbb/"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr(
            prefix + "custom_components/demo/manifest.json",
            json.dumps({"domain": "demo", "name": "Demo", "version": "1.2.0"}),
        )
        zipped.writestr(prefix + "custom_components/demo/__init__.py", "LEVEL = 2\n")
    state.zip_bytes = archive.read_bytes()

    config = tmp_path / "config"
    local = config / "custom_components" / "demo"
    local.mkdir(parents=True)
    (local / "manifest.json").write_text(
        json.dumps({"domain": "demo", "name": "Demo", "version": "1.0.0"}),
        encoding="utf-8",
    )
    (local / "stale.py").write_text("old = True\n", encoding="utf-8")

    async with open_session() as session:
        client = GitHubClient(session, TOKEN, api_base=base)
        first = await evaluate_update(
            client,
            owner="owner",
            repo="demo",
            branch="main",
            folder="demo",
            local_version="1.0.0",
            bootstrapped=False,
            installed_sha=None,
            update_mode=UPDATE_MODE_AUTOMATIC,
        )
        assert first.update_available is True
        assert first.decision.should_install is False
        assert first.latest_display == "1.2.0"
        assert "private-repo fix" in first.commit_message

        manual = await evaluate_update(
            client,
            owner="owner",
            repo="demo",
            branch="main",
            folder="demo",
            local_version="1.0.0",
            bootstrapped=True,
            installed_sha="a" * 40,
            update_mode=UPDATE_MODE_MANUAL,
        )
        assert manual.update_available is True
        assert manual.decision.should_install is False

        automatic = await evaluate_update(
            client,
            owner="owner",
            repo="demo",
            branch="main",
            folder="demo",
            local_version="1.0.0",
            bootstrapped=True,
            installed_sha="a" * 40,
            update_mode=UPDATE_MODE_AUTOMATIC,
        )
        assert automatic.decision.should_install is True

        downloaded = tmp_path / "download.zip"
        await client.download_archive("owner", "demo", automatic.remote_sha, downloaded)
        version = install_archive(downloaded, config, "demo")

    assert version == "1.2.0"
    assert (local / "__init__.py").read_text(encoding="utf-8") == "LEVEL = 2\n"
    assert not (local / "stale.py").exists()
    assert TOKEN not in (local / "__init__.py").read_text(encoding="utf-8")
