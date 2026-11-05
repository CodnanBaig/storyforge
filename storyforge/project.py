"""Locate and validate a StoryForge workspace independently of its installation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


CONFIG_NAME = "storyforge.json"
DEFAULT_PATHS = {
    "toolkit": ".storyforge",
    "renderer": ".storyforge/renderer",
    "runs": ".storyforge/runs",
}
HOSTS = frozenset({"codex", "claude"})


@dataclass(frozen=True)
class Project:
    root: Path
    toolkit: Path
    renderer: Path
    runs: Path
    config_path: Path
    config: dict[str, Any]


def relative_path(value: str) -> str:
    """Validate portable, project-relative configuration and manifest paths."""
    if not isinstance(value, str) or not value or "\\" in value or ":" in value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"Expected a relative project path: {value!r}")
    parts = value.split("/")
    if any(part in {"", ".", "..", ".git"} for part in parts) or PurePosixPath(value).is_absolute():
        raise ValueError(f"Project path must stay inside the project: {value!r}")
    return value


def safe_project_path(root: Path, relative: str) -> Path:
    """Reject symlink targets and ancestors before using a managed project path.

    ``root`` is the resolved, explicitly selected workspace. System-level links
    above it (for example macOS's /var) are immaterial to containment; links
    within the workspace cannot redirect a setup write or a configured run.
    """
    if root.is_symlink():
        raise ValueError("Project directory must not be a symlink")
    relative = relative_path(relative)
    path = root
    parts = relative.split("/")
    for index, part in enumerate(parts):
        path = path / part
        if path.is_symlink():
            raise ValueError(f"Project path uses a symlink: {path.relative_to(root)}")
        if index < len(parts) - 1 and path.exists() and not path.is_dir():
            raise ValueError(f"Project path parent is not a directory: {path.relative_to(root)}")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Project path escapes the project: {relative}")
    return path


def project_from_config(root: Path, config: dict[str, Any]) -> Project:
    """Validate a configuration without requiring it to have been written yet."""
    root = root.expanduser().resolve()
    if not isinstance(config, dict) or config.get("schema_version") != "1.0":
        raise ValueError(f"{CONFIG_NAME} must have schema_version '1.0'")
    version = config.get("toolkit_version")
    if not isinstance(version, str) or not version.strip():
        raise ValueError(f"{CONFIG_NAME} must contain a toolkit_version string")
    hosts = config.get("hosts")
    if not isinstance(hosts, list) or any(not isinstance(host, str) or host not in HOSTS for host in hosts):
        raise ValueError(f"{CONFIG_NAME} hosts must be a list containing only codex and/or claude")
    if len(set(hosts)) != len(hosts):
        raise ValueError(f"{CONFIG_NAME} hosts must not contain duplicates")
    paths = config.get("paths")
    if not isinstance(paths, dict) or any(key not in paths for key in DEFAULT_PATHS):
        raise ValueError(f"{CONFIG_NAME} paths must define toolkit, renderer and runs")
    resolved = {key: safe_project_path(root, paths[key]) for key in DEFAULT_PATHS}
    if len(set(resolved.values())) != len(resolved):
        raise ValueError("Toolkit, renderer and runs must use distinct project paths")
    if resolved["renderer"].is_relative_to(resolved["runs"]) or resolved["runs"].is_relative_to(resolved["renderer"]):
        raise ValueError("Renderer and runs directories must not contain one another")
    if resolved["toolkit"].is_relative_to(resolved["renderer"]) or resolved["toolkit"].is_relative_to(resolved["runs"]):
        raise ValueError("Toolkit directory must not be inside renderer or runs")
    for name, path in resolved.items():
        if path.exists() and not path.is_dir():
            raise ValueError(f"Configured {name} path is not a directory: {paths[name]}")
    return Project(
        root=root,
        toolkit=resolved["toolkit"],
        renderer=resolved["renderer"],
        runs=resolved["runs"],
        config_path=safe_project_path(root, CONFIG_NAME),
        config=config,
    )


def load_project(root: Path) -> Project:
    """Read the configuration in exactly ``root`` (without an ancestor search)."""
    root = root.expanduser().resolve()
    config_path = safe_project_path(root, CONFIG_NAME)
    if not config_path.is_file():
        raise ValueError(f"No {CONFIG_NAME} in {root}; run storyforge setup here first")
    if config_path.stat().st_size > 1024 * 1024:
        raise ValueError(f"{CONFIG_NAME} exceeds the 1 MiB configuration limit")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read {CONFIG_NAME}: {exc}") from exc
    return project_from_config(root, config)


def find_project(start: Path | None = None) -> Project | None:
    """Find the nearest project from a directory, file or production run path."""
    path = Path(os.getcwd()) if start is None else Path(start).expanduser()
    path = path.resolve()
    if path.is_file():
        path = path.parent
    for root in (path, *path.parents):
        candidate = root / CONFIG_NAME
        if candidate.exists() or candidate.is_symlink():
            return load_project(root)
    return None
