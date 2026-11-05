"""Find the read-only toolkit assets in a checkout or an installed wheel.

Canonical assets live at the repository root during development. The build
backend copies those same files into ``storyforge/_resources`` for normal pip
and pipx installations. Nothing is downloaded or written at import time.
"""
from __future__ import annotations

from pathlib import Path


_MARKERS = (
    "AGENTS.md",
    "CLAUDE.md",
    "LICENSE",
    "agents/orchestrator.md",
    "schemas/task-result.schema.json",
    "templates/style-bible.json",
    "examples/brief-fiction-short.json",
    "docs/agent-hosts.md",
    "renderer/package.json",
    "renderer/package-lock.json",
    "renderer/src/Root.tsx",
    "renderer/public/fonts/LICENSE.txt",
    ".codex/config.toml",
    ".claude/agents/sf-discovery.md",
)


def _complete(root: Path) -> bool:
    return all((root / marker).is_file() for marker in _MARKERS)


def resource_root() -> Path:
    """Return the absolute toolkit-resource directory.

    Treat this directory as read-only. Project setup copies its resources to a
    writable project directory before installing renderer dependencies or
    creating output. A broken installation raises an actionable error instead
    of silently using another project's files from the current directory.
    """
    package = Path(__file__).resolve().parent
    bundled = package / "_resources"
    if bundled.exists():
        if _complete(bundled):
            return bundled
        raise RuntimeError(
            "StoryForge's bundled resources are incomplete. Reinstall "
            "storyforge-video with pip or pipx."
        )
    checkout = package.parent
    if (checkout / "pyproject.toml").is_file() and _complete(checkout):
        return checkout
    raise RuntimeError(
        "StoryForge's runtime resources are missing. Install the complete "
        "storyforge-video package with pip or pipx, or use a complete source checkout."
    )
