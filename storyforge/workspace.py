"""Project-aware paths, diagnostics and local renderer convenience commands.

The installed Python package is read-only runtime material. npm and generated
media always operate in a project-owned renderer created by ``setup``.
"""
from __future__ import annotations

import hashlib
import math
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from . import __version__
from .project import Project, find_project
from .resources import resource_root
from .store import Run, StateError


def selected_project(start: Path | None = None, *, required: bool = False) -> Project | None:
    if start is not None and not start.expanduser().exists():
        raise StateError(f"Project location does not exist: {start}. Run storyforge setup {str(start)!r} first.")
    project = find_project(start.expanduser() if start is not None else None)
    if project is None and (required or start is not None):
        raise StateError("No storyforge.json found here or in a parent directory. Run storyforge setup in your project first.")
    return project


def default_runs_dir(override: Path | None = None, start: Path | None = None) -> Path:
    project = selected_project(start)
    if override is not None:
        return override.expanduser().resolve()
    return project.runs if project else Path.cwd() / "runs"


def run_resource_paths(run_dir: Path) -> dict[str, Path]:
    """Use the run's own project, never an unrelated project in the caller's cwd."""
    project = find_project(run_dir)
    if project is None:
        origin = Run(run_dir).project_root()
        if origin is not None:
            project = find_project(origin)
            if project is None or project.root != origin.resolve():
                raise StateError(f"This run belongs to a StoryForge project that is no longer at {origin}. "
                                 "Restore the project there, or move this run inside its current StoryForge project before continuing.")
    toolkit = project.toolkit if project else resource_root()
    return {
        "project": project.root if project else run_dir.resolve().parent,
        "toolkit": toolkit,
        "renderer": project.renderer if project else toolkit / "renderer",
    }


def project_info(start: Path | None = None) -> dict:
    project = selected_project(start)
    return {
        "storyforge": __version__,
        "package_resources": str(resource_root()),
        "project_root": str(project.root) if project else None,
        "config_path": str(project.config_path) if project else None,
        "toolkit_root": str(project.toolkit) if project else None,
        "renderer_root": str(project.renderer) if project else None,
        "runs_root": str(project.runs) if project else None,
        "hosts": project.config["hosts"] if project else [],
        "project_toolkit_version": project.config.get("toolkit_version") if project else None,
        "next": "Open Codex or Claude in the project and ask it to start StoryForge."
        if project else "Run storyforge setup in a new or existing project.",
    }


def _node_details() -> dict:
    binary = shutil.which("node")
    if not binary:
        return {"available": False, "version": None, "supported": False}
    try:
        completed = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=10, check=False)
        version = completed.stdout.strip()
        match = re.fullmatch(r"v?(\d+)\.\d+\.\d+(?:[-+].*)?", version)
        supported = completed.returncode == 0 and match is not None and int(match.group(1)) >= 22
        return {"available": True, "version": version or None, "supported": supported}
    except (OSError, subprocess.SubprocessError) as ex:
        return {"available": True, "version": None, "supported": False, "error": str(ex)}


def _lock_hash(renderer: Path) -> str:
    # npm ci validates both files. A locally edited package.json must also
    # invalidate the install marker, even before its lockfile is regenerated.
    manifest = (renderer / "package.json").read_bytes()
    lock = (renderer / "package-lock.json").read_bytes()
    return hashlib.sha256(manifest + b"\0" + lock).hexdigest()


def renderer_dependencies(renderer: Path) -> dict:
    installed = all((renderer / "node_modules" / name / "package.json").is_file()
                    for name in ("remotion", "@remotion/cli", "@remotion/renderer", "typescript"))
    marker = renderer / "node_modules" / ".storyforge-lock.sha256"
    current = installed and marker.is_file() and (renderer / "package.json").is_file() and (renderer / "package-lock.json").is_file() \
        and marker.read_text(encoding="utf-8").strip() == _lock_hash(renderer)
    return {"installed": installed, "lockfile_current": current}


def doctor(start: Path | None = None) -> dict:
    from .adapters import adapter_available

    info = project_info(start)
    project = selected_project(start)
    resources = resource_root()
    required = ("agents/orchestrator.md", "schemas/task-result.schema.json", "docs/contracts.md",
                "templates/intake.md", "renderer/package-lock.json", "renderer/src/index.ts")
    missing = [path for path in required if not (resources / path).is_file()]
    project_missing = []
    if project:
        for path in ("agents/orchestrator.md", "schemas/task-result.schema.json", "docs/contracts.md", "templates/intake.md"):
            if not (project.toolkit / path).is_file():
                project_missing.append(str(project.toolkit / path))
        for path in ("package.json", "package-lock.json", "src/index.ts", "public/fonts/DejaVuSans.ttf"):
            if not (project.renderer / path).is_file():
                project_missing.append(str(project.renderer / path))
    node = _node_details()
    tools = {name: bool(shutil.which(name)) for name in ("node", "npm", "ffmpeg", "ffprobe")}
    dependencies = renderer_dependencies(project.renderer) if project else {"installed": False, "lockfile_current": False}
    actions: list[str] = []
    if missing:
        actions.append("Reinstall storyforge-video; required package resources are missing.")
    if project is None:
        actions.append("Run storyforge setup in your project to install its agent instructions and renderer.")
    elif info["project_toolkit_version"] != __version__:
        actions.append("Run storyforge setup to review and update this project's toolkit resources.")
    if project_missing:
        actions.append("Run storyforge setup to restore missing project resources.")
    if not node["supported"] or not tools["npm"]:
        actions.append("Install Node.js 22 or newer with npm, then rerun storyforge setup.")
    elif project and not dependencies["lockfile_current"]:
        actions.append("Run storyforge setup to install the renderer dependencies for its current lockfile.")
    if not tools["ffmpeg"] or not tools["ffprobe"]:
        actions.append("Install FFmpeg (including ffprobe) before narrated production and final media QA.")
    preview_ready = not missing and not project_missing and project is not None and node["supported"] and tools["npm"] and dependencies["lockfile_current"]
    return {
        **info,
        "python": sys.version.split()[0],
        "python_ok": sys.version_info >= (3, 11),
        "package_resources_ok": not missing,
        "missing_resources": missing,
        "missing_project_resources": project_missing,
        "node": node,
        "tools": tools,
        "adapters": {name: adapter_available(name) for name in ("codex", "claude")},
        "renderer_installed": dependencies["installed"],
        "renderer_lockfile_current": dependencies["lockfile_current"],
        "preview_ready": preview_ready,
        "production_media_tools_ready": preview_ready and tools["ffmpeg"] and tools["ffprobe"],
        "authentication": "Not inspected. Verify provider authentication in its own host or CLI.",
        "note": "Native host mode does not require subprocess CLIs. These checks do not certify provider access or a completed production.",
        "actions": actions,
    }


def _npm(renderer: Path, *, dependencies_required: bool) -> str:
    if not (renderer / "package.json").is_file() or not (renderer / "package-lock.json").is_file():
        raise StateError(f"Renderer workspace is incomplete: {renderer}. Rerun storyforge setup to restore missing files.")
    node = _node_details()
    binary = shutil.which("npm")
    if not node["supported"] or not binary:
        raise StateError("Renderer commands require Node.js 22 or newer and npm. Install them, then rerun storyforge setup.")
    if dependencies_required and not renderer_dependencies(renderer)["lockfile_current"]:
        raise StateError("Renderer dependencies are missing or do not match the current package/lock files. "
                         "Run storyforge setup without --skip-install first.")
    return binary


def install_renderer(project: Project) -> dict:
    npm = _npm(project.renderer, dependencies_required=False)
    if renderer_dependencies(project.renderer)["lockfile_current"]:
        return {"status": "already_installed", "renderer_root": str(project.renderer)}
    print(f"Installing renderer dependencies in {project.renderer} …", file=sys.stderr, flush=True)
    result = subprocess.run([npm, "ci", "--no-fund", "--no-audit"], cwd=project.renderer,
                            stdout=sys.stderr, stderr=sys.stderr, check=False)
    if result.returncode:
        raise StateError(f"Project files are ready at {project.root}, but npm ci failed (exit {result.returncode}). "
                         "Resolve the npm error above and rerun storyforge setup in that project.")
    if not renderer_dependencies(project.renderer)["installed"]:
        raise StateError("npm ci returned successfully but renderer dependencies are incomplete. Check npm's configuration and rerun storyforge setup.")
    (project.renderer / "node_modules" / ".storyforge-lock.sha256").write_text(_lock_hash(project.renderer) + "\n", encoding="utf-8")
    return {"status": "installed", "renderer_root": str(project.renderer)}


def _caller_path(path: Path) -> Path:
    return path.expanduser().resolve()


def renderer_command(command: str, *, start: Path | None = None, props: Path | None = None,
                     output: Path | None = None, frames: str | None = None,
                     scale: float = 0.5, allow_demo: bool = False) -> int:
    project = selected_project(start, required=True)
    assert project is not None
    npm = _npm(project.renderer, dependencies_required=True)
    if command not in {"studio", "preview", "render"}:
        raise StateError(f"Unknown renderer command: {command}")
    arguments = [npm, "run", "stills" if command == "preview" else command]
    options: list[str] = []
    if props is not None:
        props = _caller_path(props)
        if not props.is_file():
            raise StateError(f"Props file does not exist: {props}")
    elif command == "preview":
        props = project.renderer / "examples" / "demo-short.json"
        print("Rendering a labeled, silent technical demo. Supply --props for your own film.", file=sys.stderr)
    if props is not None:
        options.extend(["--props", str(props)])
    if command == "preview":
        if not math.isfinite(scale) or not 0 < scale <= 1:
            raise StateError("Preview --scale must be greater than 0 and at most 1.")
        options.extend(["--scale", str(scale)])
        if frames is not None:
            if not re.fullmatch(r"\d+(?:,\d+)*", frames):
                raise StateError("Preview --frames must be comma-separated nonnegative integers, such as 0,120,300.")
            options.extend(["--frames", frames])
        if output is None:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            output = project.toolkit / "previews" / f"{stamp}-{uuid4().hex[:8]}"
        else:
            output = _caller_path(output)
        if output.exists() and (not output.is_dir() or any(output.iterdir())):
            raise StateError(f"Preview output is not an empty directory: {output}. Choose a new --out directory to preserve earlier frames.")
        options.extend(["--out", str(output)])
    elif command == "render":
        if props is None or output is None:
            raise StateError("render requires --props FILE and --out VIDEO.mp4.")
        output = _caller_path(output)
        if output.exists():
            raise StateError(f"Refusing to overwrite {output}. Choose a new --out file.")
        options.extend(["--out", str(output)])
        if allow_demo:
            options.append("--allow-demo")
    if options:
        arguments.extend(["--", *options])
    print(f"Using renderer: {project.renderer}", file=sys.stderr, flush=True)
    if output is not None:
        print(f"Output: {output}", file=sys.stderr, flush=True)
    # Inherit the caller's streams so Studio and long renders report progress.
    # An argv list keeps spaces and shell metacharacters in user paths literal.
    return subprocess.run(arguments, cwd=project.renderer, check=False).returncode
