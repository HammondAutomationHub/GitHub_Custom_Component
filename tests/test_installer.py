"""Archive install tests, including the HACS folder layout."""

from __future__ import annotations

import json
from pathlib import Path
import stat
import zipfile

import pytest

from custom_components.gpm.errors import ArchiveError, ManifestMismatch, ManifestNotFound
from custom_components.gpm.installer import (
    install_archive,
    list_integrations,
    locate_component,
    safe_extract,
)


def _manifest(domain: str, version: str) -> str:
    return json.dumps({"domain": domain, "name": domain, "version": version})


def _zip(path: Path, files: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def test_install_replaces_hacs_layout_and_removes_stale_files(tmp_path: Path) -> None:
    archive = tmp_path / "repo.zip"
    prefix = "owner-demo-abc/"
    _zip(
        archive,
        {
            prefix + "custom_components/demo/manifest.json": _manifest("demo", "1.2.0"),
            prefix + "custom_components/demo/__init__.py": "UPDATED = True\n",
            prefix + "custom_components/demo/new.py": "value = 1\n",
            prefix + "README.md": "not installed\n",
        },
    )
    config = tmp_path / "config"
    folder = config / "custom_components" / "demo"
    folder.mkdir(parents=True)
    (folder / "manifest.json").write_text(_manifest("demo", "1.0.0"), encoding="utf-8")
    (folder / "old.py").write_text("stale = True\n", encoding="utf-8")

    version = install_archive(archive, config, "demo")

    assert version == "1.2.0"
    assert (folder / "new.py").is_file()
    assert (folder / "__init__.py").read_text(encoding="utf-8") == "UPDATED = True\n"
    assert not (folder / "old.py").exists()
    assert not (folder.parent / "demo.gpm-backup").exists()
    assert not (config / "custom_components" / "README.md").exists()


def test_root_manifest_layout_is_accepted(tmp_path: Path) -> None:
    archive = tmp_path / "repo.zip"
    _zip(
        archive,
        {
            "manifest.json": _manifest("demo", "2.0.0"),
            "__init__.py": "ROOT = True\n",
        },
    )
    config = tmp_path / "config"
    version = install_archive(archive, config, "demo")
    installed = config / "custom_components" / "demo"
    assert version == "2.0.0"
    assert (installed / "__init__.py").is_file()


def test_unsafe_archive_does_not_write_files(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("ok.txt", "should not land")
        zipped.writestr("../evil.txt", "nope")
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(ArchiveError):
        safe_extract(archive, dest)
    assert not (tmp_path / "evil.txt").exists()
    assert not (dest / "ok.txt").exists()


def test_symlink_entries_are_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "link.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        info = zipfile.ZipInfo("link.py")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        zipped.writestr(info, "../outside.py")
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(ArchiveError):
        safe_extract(archive, dest)


def test_domain_mismatch_and_self_update_are_refused(tmp_path: Path) -> None:
    nested = tmp_path / "extract" / "custom_components" / "demo"
    nested.mkdir(parents=True)
    (nested / "manifest.json").write_text(_manifest("other", "1.0.0"), encoding="utf-8")
    with pytest.raises(ManifestMismatch):
        locate_component(tmp_path / "extract", "demo")

    config = tmp_path / "config"
    archive = tmp_path / "gpm.zip"
    _zip(archive, {"manifest.json": _manifest("gpm", "1.0.0")})
    with pytest.raises(ArchiveError):
        install_archive(archive, config, "gpm")
    with pytest.raises(ArchiveError):
        install_archive(archive, config, "../demo")


def test_folder_list_skips_gpm_and_folders_without_a_manifest(tmp_path: Path) -> None:
    base = tmp_path / "custom_components"
    (base / "demo").mkdir(parents=True)
    (base / "demo" / "manifest.json").write_text(_manifest("demo", "1.0.0"), encoding="utf-8")
    (base / "gpm").mkdir()
    (base / "gpm" / "manifest.json").write_text(_manifest("gpm", "1.0.0"), encoding="utf-8")
    (base / "notes").mkdir()
    found = list_integrations(tmp_path)
    assert [item[0] for item in found] == ["demo"]
    assert "1.0.0" in found[0][1]


def test_missing_component_is_reported(tmp_path: Path) -> None:
    archive = tmp_path / "empty.zip"
    _zip(archive, {"README.md": "nothing here"})
    with pytest.raises(ManifestNotFound):
        install_archive(archive, tmp_path / "config", "demo")
