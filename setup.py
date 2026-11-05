"""Build the installable toolkit without duplicating canonical assets in git."""
from __future__ import annotations

import fnmatch
import os
from pathlib import Path
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist


RESOURCE_FILES = (
    "AGENTS.md", "CLAUDE.md", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md",
    ".env.example", ".codex/config.toml",
)
RESOURCE_TREES = (
    "agents", "schemas", "templates", "examples", "docs", "renderer",
    ".codex/agents", ".claude/agents",
)
EXCLUDED_DIRS = frozenset({
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".cache", "cache", "build", "dist", "out",
    "runs", ".storyforge", "_resources",
})
EXCLUDED_FILES = (
    "BUILD_CONTRACT.md", ".DS_Store", "*.py[cod]", "*.sqlite3*", "*.pem", "*.key",
    "credentials*.json", "secrets*.json", ".npmrc", ".pypirc", ".netrc",
)


def excluded(relative: Path) -> bool:
    """Apply the same dependency, output and credential filter to both formats."""
    return (
        any(part in EXCLUDED_DIRS for part in relative.parts)
        or (relative.name.startswith(".env") and relative.name != ".env.example")
        or any(fnmatch.fnmatchcase(relative.name, pattern) for pattern in EXCLUDED_FILES)
    )


def refuse_symlink(path: Path, root: Path) -> None:
    """An allowed-looking child must not escape through a linked ancestor."""
    for candidate in (path, *path.parents):
        if candidate == root:
            break
        if candidate.is_symlink():
            raise RuntimeError(f"Refusing source/resource symlink: {candidate.relative_to(root)}")


def resource_files(root: Path) -> list[Path]:
    """Return a sorted, explicit resource inventory; never follow symlinks."""
    selected: set[Path] = set()
    for name in RESOURCE_FILES:
        path = root / name
        refuse_symlink(path, root)
        if not path.is_file():
            raise RuntimeError(f"Required StoryForge resource is missing: {name}")
        selected.add(Path(name))
    for name in RESOURCE_TREES:
        tree = root / name
        refuse_symlink(tree, root)
        if not tree.is_dir():
            raise RuntimeError(f"Required StoryForge resource directory is missing: {name}")
        for current, directories, files in os.walk(tree, followlinks=False):
            current_path = Path(current)
            directories[:] = sorted(item for item in directories
                                     if not excluded((current_path / item).relative_to(root)))
            for item in directories:
                refuse_symlink(current_path / item, root)
            for item in sorted(files):
                path = current_path / item
                relative = path.relative_to(root)
                if excluded(relative):
                    continue
                refuse_symlink(path, root)
                selected.add(relative)
    return sorted(selected, key=Path.as_posix)


class BuildToolkit(build_py):
    def run(self) -> None:
        super().run()
        if self.editable_mode:
            return
        root = Path(__file__).resolve().parent
        destination = Path(self.build_lib) / "storyforge" / "_resources"
        # Rebuild from the canonical inputs so deleted assets cannot survive a
        # second build in a previously used build directory.
        if destination.exists():
            shutil.rmtree(destination)
        for relative in resource_files(root):
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / relative, target)

    def get_outputs(self, include_bytecode: bool = True) -> list[str]:
        outputs = super().get_outputs(include_bytecode)
        if self.editable_mode:
            return outputs
        destination = Path(self.build_lib) / "storyforge" / "_resources"
        return outputs + [str(destination / item) for item in resource_files(Path(__file__).resolve().parent)]


class SourceToolkit(sdist):
    def make_release_tree(self, base_dir: str, files: list[str]) -> None:
        root = Path(__file__).resolve().parent
        selected = []
        for name in sorted(files):
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts or excluded(relative):
                continue
            path = root / relative
            refuse_symlink(path, root)
            selected.append(name)
        super().make_release_tree(base_dir, selected)
        # SOURCES.txt must describe the filtered source archive, not a stale
        # egg-info inventory from an earlier build.
        egg_info = Path(self.get_finalized_command("egg_info").egg_info)
        if egg_info.is_absolute():
            egg_info = egg_info.relative_to(root)
        sources = Path(base_dir) / egg_info / "SOURCES.txt"
        if sources.exists():
            # The sdist builder may use hard links. Replace before writing.
            sources.unlink()
            sources.write_text("\n".join(selected) + "\n", encoding="utf-8")


if __name__ == "__main__":
    setup(cmdclass={"build_py": BuildToolkit, "sdist": SourceToolkit})
