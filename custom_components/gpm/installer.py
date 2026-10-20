"""Safely extract a GitHub archive over a custom component folder."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import stat
import tempfile
import zipfile

from .const import DOMAIN, MAX_FILE_BYTES
from .errors import ArchiveError, ManifestMismatch, ManifestNotFound
from .repo import folder_name_error


@dataclass(frozen=True)
class LocatedComponent:
    """A component directory found inside an extracted archive."""

    path: Path
    version: str


def integration_dir(config_dir: Path, folder: str) -> Path:
    """Return the destination folder, refusing paths that escape custom_components."""

    problem = folder_name_error(folder)
    if problem:
        raise ArchiveError(problem)
    base = (config_dir / "custom_components").resolve()
    dest = (base / folder).resolve()
    if dest.parent != base:
        raise ArchiveError("Invalid integration folder name.")
    return dest


def install_archive(zip_path: Path, config_dir: Path, folder: str) -> str:
    """Replace ``custom_components/<folder>`` with the copy from a zipball.

    The previous folder is kept until the new copy is in place. On failure the
    previous folder is restored. Returns the installed manifest version.
    """

    dest = integration_dir(config_dir, folder)
    with tempfile.TemporaryDirectory(prefix="gpm-extract-") as tmp:
        root = Path(tmp)
        safe_extract(zip_path, root)
        located = locate_component(root, folder)
        replace_tree(located.path, dest)
        return located.version


def read_local_version(config_dir: Path, folder: str) -> str:
    """Read the manifest version currently installed on disk."""

    dest = integration_dir(config_dir, folder)
    manifest = dest / "manifest.json"
    if not manifest.is_file():
        raise ManifestNotFound(
            f"{folder} is not installed in custom_components. Install it before GPM can update it."
        )
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise ManifestNotFound(f"Could not read the local manifest for {folder}.") from err
    return str(data.get("version") or "0")


def list_integrations(config_dir: Path) -> list[tuple[str, str]]:
    """Return ``(folder, label)`` for custom components GPM is allowed to update."""

    base = config_dir / "custom_components"
    if not base.is_dir():
        return []
    found: list[tuple[str, str]] = []
    for child in sorted(base.iterdir(), key=lambda path: path.name.lower()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if folder_name_error(child.name):
            continue
        manifest_path = child / "manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        name = str(data.get("name") or child.name)
        version = str(data.get("version") or "unknown")
        domain = data.get("domain")
        label = f"{name} ({child.name} {version})"
        if domain and domain != child.name:
            label = f"{label} — manifest domain is {domain}"
        found.append((child.name, label))
    return found


def safe_extract(zip_path: Path, dest: Path) -> None:
    """Extract a zip, rejecting path traversal, absolute paths, and symlinks."""

    dest_resolved = dest.resolve()
    try:
        archive = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as err:
        raise ArchiveError("Downloaded file is not a zip archive.") from err

    with archive:
        total = 0
        for info in archive.infolist():
            if _is_symlink(info):
                raise ArchiveError("Archive contains a symlink, which GPM will not extract.")
            if _unsafe_name(info.filename):
                raise ArchiveError("Archive contains an unsafe path.")
            if info.file_size > MAX_FILE_BYTES:
                raise ArchiveError("A file in the archive exceeds the size limit.")
            total += info.file_size
            if total > MAX_FILE_BYTES * 4:
                raise ArchiveError("Archive uncompressed size exceeds the limit.")
            target = (dest_resolved / info.filename).resolve()
            if dest_resolved != target and dest_resolved not in target.parents:
                raise ArchiveError("Archive contains an unsafe path.")
        archive.extractall(dest_resolved)


def locate_component(root: Path, folder: str) -> LocatedComponent:
    """Find the component inside a GitHub zipball.

    Prefers ``custom_components/<folder>`` (the HACS layout). A repository whose
    root is the component is accepted when that manifest domain matches.
    """

    bases = [root]
    children = [path for path in root.iterdir() if path.is_dir()]
    if len(children) == 1:
        bases.append(children[0])

    mismatch: str | None = None
    for base in bases:
        nested = base / "custom_components" / folder / "manifest.json"
        if nested.is_file():
            return _load_component(nested.parent, folder)
        root_manifest = base / "manifest.json"
        if root_manifest.is_file():
            try:
                return _load_component(base, folder)
            except ManifestMismatch as err:
                mismatch = str(err)
                continue
    if mismatch:
        raise ManifestMismatch(mismatch)
    raise ManifestNotFound(
        f"Could not find custom_components/{folder} or a root manifest for {folder}."
    )


def replace_tree(source: Path, dest: Path) -> None:
    """Replace ``dest`` with ``source``, restoring ``dest`` if the swap fails."""

    dest.parent.mkdir(parents=True, exist_ok=True)
    staging = dest.with_name(dest.name + ".gpm-new")
    backup = dest.with_name(dest.name + ".gpm-backup")
    if staging.exists():
        shutil.rmtree(staging)
    if backup.exists():
        shutil.rmtree(backup)
    shutil.copytree(source, staging, symlinks=False, ignore=_ignore_runtime_files)
    moved_aside = False
    try:
        if dest.exists():
            dest.rename(backup)
            moved_aside = True
        staging.rename(dest)
    except Exception:
        if moved_aside and not dest.exists() and backup.exists():
            backup.rename(dest)
        raise
    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)


def _load_component(path: Path, folder: str) -> LocatedComponent:
    try:
        data = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise ManifestNotFound("manifest.json is not valid JSON.") from err
    domain = data.get("domain")
    if domain != folder:
        raise ManifestMismatch(
            f"Remote manifest domain is {domain!r}, expected {folder!r}."
        )
    if folder == DOMAIN:
        raise ArchiveError("Refusing to overwrite GPM itself.")
    return LocatedComponent(path=path, version=str(data.get("version") or "0"))


def _unsafe_name(name: str) -> bool:
    normalized = name.replace("\\", "/")
    if not normalized or normalized.startswith("/") or normalized.startswith("//"):
        return True
    if len(normalized) > 1 and normalized[1] == ":":
        return True
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    return any(part == ".." for part in parts)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = info.external_attr >> 16
    return stat.S_ISLNK(mode)


def _ignore_runtime_files(directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name in {"__pycache__", ".git", ".github"}:
            ignored.add(name)
            continue
        if (Path(directory) / name).is_symlink():
            ignored.add(name)
    return ignored
