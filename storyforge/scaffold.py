"""Install project-owned assets without overwriting application or user files."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import stat
import tomllib
from pathlib import Path
from typing import Any
from uuid import uuid4

from . import __version__
from .project import CONFIG_NAME, DEFAULT_PATHS, Project, load_project, project_from_config, relative_path, safe_project_path
from .resources import resource_root


RESOURCE_DIRECTORIES = ("agents", "docs", "schemas", "templates", "examples")
RESOURCE_FILES = ("AGENTS.md", "CLAUDE.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "README.md", ".env.example")
# Keep these runtime filters aligned with setup.py's build inventory. Editable
# installs read the canonical source tree, which may contain local auth/cache
# files that are absent from the distributed wheel. Do not import setuptools
# (a build dependency) into the installed, standard-library CLI.
SKIP_DIRECTORIES = frozenset({"node_modules", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache", "cache", "build", "dist", "out", "runs", ".storyforge", "_resources", ".remotion"})
SKIP_FILES = ("BUILD_CONTRACT.md", ".DS_Store", "*.py[cod]", "*.sqlite3*", "*.pem", "*.key", "credentials*.json", "secrets*.json", ".npmrc", ".pypirc", ".netrc")
MARKERS = {
    "markdown": ("<!-- storyforge:begin -->", "<!-- storyforge:end -->"),
    "gitignore": ("# storyforge:begin", "# storyforge:end"),
    "codex": ("# storyforge:agents:begin", "# storyforge:agents:end"),
}


class SetupConflictError(ValueError):
    """All known conflicts are reported before any scaffold files are written."""

    def __init__(self, conflicts: list[str]):
        self.conflicts = sorted(set(conflicts))
        super().__init__(
            "StoryForge setup did not write any files because of conflicts:\n"
            + "\n".join(f"- {item}" for item in self.conflicts)
            + "\nReconcile these files before rerunning setup. To retain a reviewed, previously managed resource, use --keep-local with its exact project-relative path. This cannot bypass configuration or managed-block conflicts."
        )


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _block_hash(text: str) -> str:
    return _hash(text.replace("\r\n", "\n").encode("utf-8"))


def _relative(project: Project, path: Path) -> str:
    return path.relative_to(project.root).as_posix()


def _refuse_source_symlink(path: Path, root: Path) -> None:
    if not path.is_relative_to(root):
        raise ValueError(f"StoryForge resource is outside its resource root: {path}")
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise ValueError(f"StoryForge resource uses a symlink: {candidate}")
        if candidate == root:
            break


def _source_files(directory: Path, *, root: Path):
    _refuse_source_symlink(directory, root)
    if not directory.is_dir():
        raise ValueError(f"Installed StoryForge resources are missing or unsafe: {directory}")
    for current, directories, files in os.walk(directory, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in SKIP_DIRECTORIES and not name.endswith(".egg-info"))
        for name in directories:
            _refuse_source_symlink(Path(current) / name, root)
        for name in sorted(files):
            if (name.startswith(".env") and name != ".env.example") or any(fnmatch.fnmatchcase(name, pattern) for pattern in SKIP_FILES):
                continue
            path = Path(current) / name
            _refuse_source_symlink(path, root)
            if path.is_file():
                yield path.relative_to(directory), path


def _read_manifest(project: Project) -> tuple[dict[str, Any], bytes | None]:
    relative = _relative(project, project.toolkit / "installation.json")
    path = safe_project_path(project.root, relative)
    if not path.exists():
        return {"schema_version": "1.0", "files": {}, "blocks": {}, "hosts": []}, None
    if not path.is_file():
        raise ValueError(f"Installation manifest is not a file: {relative}")
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("StoryForge installation manifest exceeds 2 MiB")
    raw = path.read_bytes()
    try:
        manifest = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read {relative}: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0":
        raise ValueError(f"Unsupported StoryForge installation manifest: {relative}")
    for section in ("files", "blocks"):
        entries = manifest.get(section)
        if not isinstance(entries, dict):
            raise ValueError(f"Installation manifest needs a {section} object")
        for target, fingerprint in entries.items():
            relative_path(target)
            if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
                raise ValueError(f"Invalid installation fingerprint: {target}")
    hosts = manifest.get("hosts", [])
    if not isinstance(hosts, list) or any(not isinstance(host, str) or host not in {"codex", "claude"} for host in hosts):
        raise ValueError("Installation manifest hosts must contain codex and/or claude")
    return manifest, raw


class _Plan:
    def __init__(self, project: Project, manifest: dict[str, Any], *, keep_local: list[str] | tuple[str, ...] = ()):
        self.project = project
        self.files = dict(manifest["files"])
        self.blocks = dict(manifest["blocks"])
        if not isinstance(keep_local, (list, tuple)):
            raise ValueError("keep_local must be a list or tuple of exact project-relative resource paths")
        self.keep_local = frozenset(relative_path(path) for path in keep_local)
        self.consumed_keep_local: set[str] = set()
        self.targets: dict[str, bytes] = {}
        self.writes: dict[str, bytes] = {}
        self.originals: dict[str, bytes | None] = {}
        self.created: list[str] = []
        self.updated: list[str] = []
        self.unchanged: list[str] = []
        self.warnings: list[str] = []
        self.conflicts: list[str] = []

    def read(self, relative: str) -> bytes | None:
        path = safe_project_path(self.project.root, relative)
        if path.exists() and not path.is_file():
            raise ValueError(f"Expected a file: {relative}")
        return path.read_bytes() if path.exists() else None

    def record(self, relative: str, current: bytes | None, desired: bytes) -> None:
        if relative in self.targets and self.targets[relative] != desired:
            self.conflicts.append(f"{relative}: configured resource paths collide at this file")
            return
        self.targets[relative] = desired
        if current == desired:
            self.unchanged.append(relative)
            return
        self.writes[relative] = desired
        self.originals[relative] = current
        (self.created if current is None else self.updated).append(relative)

    def file(self, relative: str, desired: bytes) -> None:
        requested_keep = relative in self.keep_local
        if requested_keep:
            self.consumed_keep_local.add(relative)
        try:
            current = self.read(relative)
        except ValueError as exc:
            self.conflicts.append(str(exc))
            return
        desired_hash = _hash(desired)
        previous_hash = self.files.get(relative)
        if requested_keep:
            if previous_hash is None or relative in self.blocks:
                self.conflicts.append(f"{relative}: --keep-local is allowed only for a previously managed ordinary resource")
            elif current is None:
                self.conflicts.append(f"{relative}: --keep-local requires an existing local resource file")
            else:
                self.record(relative, current, current)
                # Retain the exact local bytes, but acknowledge the newly seen
                # upstream resource. A future upstream change must conflict
                # again rather than silently replacing the user's merged file.
                self.files[relative] = desired_hash
                self.warnings.append(f"Acknowledged --keep-local for {relative}: retained the exact local file and advanced its upstream baseline")
            return
        if current is None or current == desired or (previous_hash is not None and _hash(current) == previous_hash):
            self.record(relative, current, desired)
            self.files[relative] = desired_hash
        elif previous_hash == desired_hash:
            self.record(relative, current, current)
            self.warnings.append(f"Preserved local customization: {relative}")
        elif previous_hash is not None:
            self.conflicts.append(f"{relative}: local edits overlap an updated StoryForge resource")
        else:
            self.conflicts.append(f"{relative}: an existing unmanaged file has different contents")

    def block(self, relative: str, body: str, kind: str) -> None:
        begin, end = MARKERS[kind]
        desired_block = begin + "\n" + body.rstrip("\n") + "\n" + end + "\n"
        try:
            current = self.read(relative)
            text = "" if current is None else current.decode("utf-8")
        except (ValueError, UnicodeError) as exc:
            self.conflicts.append(f"{relative}: {exc}")
            return
        counts = (text.count(begin), text.count(end))
        if counts == (0, 0):
            separator = "" if not text else ("\n" if text.endswith("\n") else "\n\n")
            updated = text + separator + desired_block
        elif counts == (1, 1):
            pattern = re.compile(r"(?m)^" + re.escape(begin) + r"\r?\n[\s\S]*?^" + re.escape(end) + r"(?:\r?\n|$)")
            match = pattern.search(text)
            if match is None:
                self.conflicts.append(f"{relative}: malformed StoryForge managed block")
                return
            current_hash = _block_hash(match.group())
            desired_hash = _block_hash(desired_block)
            previous_hash = self.blocks.get(relative)
            if current_hash != desired_hash and (previous_hash is None or current_hash != previous_hash):
                self.conflicts.append(f"{relative}: StoryForge managed block was edited; keep custom instructions outside its markers")
                return
            updated = text[:match.start()] + desired_block + text[match.end():]
        else:
            self.conflicts.append(f"{relative}: duplicate or incomplete StoryForge managed block")
            return
        self.blocks[relative] = _block_hash(desired_block)
        self.record(relative, current, updated.encode("utf-8"))


def _workflow(project: Project) -> bytes:
    toolkit = _relative(project, project.toolkit)
    renderer = _relative(project, project.renderer)
    runs = _relative(project, project.runs)
    return f"""# StoryForge production workflow

This project owns its StoryForge resources and editable renderer. Use the installed
`storyforge` CLI from any directory inside the project. Start with `storyforge info`
to resolve absolute paths; the Python package does not need a retained checkout.

## Workspace context

- `PROJECT_ROOT`: the directory containing `storyforge.json`.
- `TOOLKIT_ROOT`: `PROJECT_ROOT/{toolkit}`.
- `RENDERER_ROOT`: `PROJECT_ROOT/{renderer}`.
- Runs belong in `PROJECT_ROOT/{runs}`. `RUN_DIR` is the exact production directory
  returned by `storyforge start` or `storyforge init`, never the runs parent.

Read `TOOLKIT_ROOT/AGENTS.md` and `TOOLKIT_ROOT/docs/agent-hosts.md` before starting
or resuming a production. Claude hosts should also read `TOOLKIT_ROOT/CLAUDE.md`.
The project owner's existing instructions and permissions continue to apply.

## Start and coordinate

Use the user's supplied niche, duration, format and references. Ask for missing
essentials together and preserve saved answers. Resolve the hook, narration,
provider access and approved spending before paid work. A sample brief is only
an example; it does not authorize production.

Run `storyforge start` for intake and a new run, or use `storyforge intake` followed
by `storyforge init --brief brief.json`. Inspect `storyforge status RUN_DIR` and
`storyforge next RUN_DIR`. The CLI's task graph and validation gates are authoritative.

The orchestrator alone claims tasks, keeps leases current, reserves approved media,
and submits results. Give every worker the claimed task packet with its exact
`PROJECT_ROOT`, `TOOLKIT_ROOT`, `RENDERER_ROOT`, `RUN_DIR`, attempt workspace and
token context. Role cards live in `TOOLKIT_ROOT/agents/`; guides and schemas live
in `TOOLKIT_ROOT/docs/` and `TOOLKIT_ROOT/schemas/`. Dispatch at most three independent
workers unless the user has selected a different limit. If custom agents are
unavailable, use the same packets with ordinary host agents or report sequential mode.

Use `storyforge studio` to inspect the project renderer, `storyforge preview` for
review stills, and `storyforge doctor` for missing dependencies. Example previews
are explicitly labeled silent demonstrations. A finished production requires the
real narration, measured timing, accepted gates and review of the actual export.

## Project maintenance

Keep application dependencies in their existing location; renderer dependencies
belong only in `RENDERER_ROOT/node_modules`. Keep provider secrets out of tracked
files. Do not write runs or user assets into the installed Python package.

Rerunning `storyforge setup` preserves local asset customizations. When both the
installed version and a local file have changed, reconcile the reported conflict
before upgrading that resource. To retain a reviewed local merge, rerun setup with
`--keep-local PROJECT_RELATIVE_PATH` for each affected managed resource. This keeps
the exact local bytes and acknowledges the current upstream revision; a later
upstream change is checked again. Keep project-specific instructions outside the
managed blocks in root `AGENTS.md` and `CLAUDE.md`.
""".encode("utf-8")


def _host_block(project: Project) -> str:
    workflow = _relative(project, project.toolkit / "WORKFLOW.md")
    return (
        "## StoryForge video production\n\n"
        f"For StoryForge video tasks, read `{workflow}` and run `storyforge info` "
        "to resolve this project's toolkit, renderer and run paths. Follow the "
        "project's existing instructions and permissions. Use the installed "
        "`storyforge` CLI; task packets identify the canonical role cards and "
        "the exact claimed worker workspace.\n"
    )


def _ignore_path(relative: str) -> str:
    # Gitignore patterns are rooted at the project and should match literally.
    return "/" + "".join("\\" + char if char in "*?[]!#\\ " else char for char in relative) + "/"


def _gitignore(project: Project) -> str:
    paths = [project.runs, project.toolkit / "previews", *(project.renderer / suffix for suffix in ("node_modules", "out", "dist", "build"))]
    return "# Local StoryForge runs, review renders and renderer dependencies\n" + "\n".join(_ignore_path(_relative(project, path)) for path in paths)


def _codex_settings(plan: _Plan) -> None:
    relative = ".codex/config.toml"
    try:
        current = plan.read(relative)
        config = {} if current is None else tomllib.loads(current.decode("utf-8"))
    except (ValueError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        plan.conflicts.append(f"{relative}: cannot safely read existing Codex settings ({exc})")
        return
    if "agents" in config:
        plan.unchanged.append(relative)
        agents = config["agents"]
        if isinstance(agents, dict) and agents.get("enabled") is False:
            plan.warnings.append("Codex agents are explicitly disabled in .codex/config.toml; existing settings were preserved. Enable them yourself or use ordinary/sequential workers.")
        elif not isinstance(agents, dict):
            plan.warnings.append("Existing Codex agents settings were preserved; verify that they are valid for your installed Codex host.")
        elif not isinstance(agents.get("max_concurrent_threads_per_session"), int):
            plan.warnings.append("Existing Codex agents settings were preserved. StoryForge's orchestrator still limits workers to the selected production budget.")
        return
    plan.block(relative, "# StoryForge uses at most three native workers by default.\n[agents]\nenabled = true\nmax_concurrent_threads_per_session = 3", "codex")


def _atomic_write(root: Path, relative: str, data: bytes) -> None:
    path = safe_project_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path = safe_project_path(root, relative)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def setup_project(path: Path, *, host: str = "both", keep_local: list[str] | tuple[str, ...] = ()) -> dict[str, Any]:
    """Create or safely refresh project files; dependency installation is separate.

    Current host integrations are retained when adding another host. A same-version
    rerun preserves locally customized ordinary resources. An upstream change that
    overlaps those edits blocks the entire write plan. Existing instruction text
    outside the managed blocks and existing Codex agent settings remain intact.
    Explicit ``keep_local`` paths acknowledge already reconciled, previously
    managed resources while retaining their bytes and advancing the upstream
    baseline. Configuration, managed blocks and unknown paths cannot be bypassed.
    """
    if host not in {"both", "codex", "claude", "none"}:
        raise ValueError("host must be both, codex, claude or none")
    selected = {"codex", "claude"} if host == "both" else ({host} if host != "none" else set())
    requested_root = Path(path).expanduser()
    if requested_root.is_symlink():
        raise ValueError("Setup project directory must not be a symlink")
    root = requested_root.resolve()
    if root.exists() and not root.is_dir():
        raise ValueError(f"Setup project path is not a directory: {root}")
    config_path = safe_project_path(root, CONFIG_NAME)
    if config_path.exists():
        existing = load_project(root)
        config = dict(existing.config)
        selected.update(config["hosts"])
        current_config = config_path.read_bytes()
    else:
        config = {"schema_version": "1.0", "toolkit_version": __version__, "hosts": [], "paths": dict(DEFAULT_PATHS)}
        current_config = None
    config["toolkit_version"] = __version__
    config["hosts"] = sorted(selected)
    project = project_from_config(root, config)
    manifest, original_manifest = _read_manifest(project)
    selected.update(manifest.get("hosts", []))
    config["hosts"] = sorted(selected)
    plan = _Plan(project, manifest, keep_local=keep_local)
    resources = resource_root()

    for directory in RESOURCE_DIRECTORIES:
        for relative, source in _source_files(resources / directory, root=resources):
            plan.file(_relative(project, project.toolkit / directory / relative), source.read_bytes())
    for relative, source in _source_files(resources / "renderer", root=resources):
        plan.file(_relative(project, project.renderer / relative), source.read_bytes())
    for name in RESOURCE_FILES:
        source = resources / name
        _refuse_source_symlink(source, resources)
        if not source.is_file():
            raise ValueError(f"Installed StoryForge resources are missing or unsafe: {name}")
        plan.file(_relative(project, project.toolkit / name), source.read_bytes())
    plan.file(_relative(project, project.toolkit / "WORKFLOW.md"), _workflow(project))

    for selected_host in sorted(selected):
        source_directory = resources / f".{selected_host}" / "agents"
        for relative, source in _source_files(source_directory, root=resources):
            plan.file((Path(f".{selected_host}") / "agents" / relative).as_posix(), source.read_bytes())
        plan.block("AGENTS.md" if selected_host == "codex" else "CLAUDE.md", _host_block(project), "markdown")
    if "codex" in selected:
        _codex_settings(plan)
    plan.block(".gitignore", _gitignore(project), "gitignore")

    # Configuration is user-editable structured data. Preserve custom keys and
    # paths, modifying only version/host metadata. Keep its exact bytes if no
    # semantic changes are needed, including the user's whitespace convention.
    if current_config is not None and json.loads(current_config) == config:
        desired_config = current_config
    else:
        desired_config = _json_bytes(config)
    plan.record(CONFIG_NAME, current_config, desired_config)
    plan.files[CONFIG_NAME] = _hash(desired_config)

    updated_manifest = {
        **manifest,
        "schema_version": "1.0",
        "toolkit_version": __version__,
        "hosts": sorted(selected),
        "files": dict(sorted(plan.files.items())),
        "blocks": dict(sorted(plan.blocks.items())),
    }
    manifest_relative = _relative(project, project.toolkit / "installation.json")
    plan.record(manifest_relative, original_manifest, _json_bytes(updated_manifest))
    # Validate paths against the complete virtual installation too, including
    # parents which do not exist yet. A custom path named AGENTS.md, for example,
    # cannot serve as a directory and as a host instruction file simultaneously.
    for relative in plan.targets:
        for parent in Path(relative).parents:
            if parent.as_posix() in plan.targets:
                plan.conflicts.append(f"{parent.as_posix()}: configured paths need this to be both a file and a directory")
        target = project.root / relative
        for directory in (project.toolkit, project.renderer, project.runs, project.toolkit / "previews"):
            if directory == target or directory.is_relative_to(target):
                plan.conflicts.append(f"{relative}: managed file collides with a configured project directory")
    for relative in sorted(plan.keep_local - plan.consumed_keep_local):
        plan.conflicts.append(f"{relative}: --keep-local must name an exact, previously managed ordinary resource included in this setup; configuration, installation metadata and managed instruction blocks are excluded")
    if plan.conflicts:
        raise SetupConflictError(plan.conflicts)

    # Recheck the complete write set before starting, so changes made during
    # planning do not become accidental overwrites. Atomic replacements prevent
    # readers from observing partial files. The ownership manifest is written last.
    for relative, original in plan.originals.items():
        if plan.read(relative) != original:
            raise SetupConflictError([f"{relative}: file changed while setup was planning"])
    for relative, data in plan.writes.items():
        if plan.read(relative) != plan.originals[relative]:
            raise ValueError(f"{relative} changed while setup was writing; setup stopped without overwriting it")
        _atomic_write(root, relative, data)

    return {
        "project_root": str(project.root),
        "config_path": str(project.config_path),
        "toolkit_root": str(project.toolkit),
        "renderer_root": str(project.renderer),
        "runs_root": str(project.runs),
        "hosts": sorted(selected),
        "created": sorted(set(plan.created)),
        "updated": sorted(set(plan.updated)),
        "unchanged": sorted(set(plan.unchanged)),
        "warnings": plan.warnings,
    }
