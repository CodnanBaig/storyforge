"""Build and install both Python distribution paths without network or providers.

Run with the development interpreter (setuptools>=77 and wheel installed):

    python scripts/verify_distribution.py --output-dir dist/verification

The test builds an isolated source copy, checks archive contents and resource
hashes, rebuilds a wheel from the sdist, then deletes both build checkouts before
installing each wheel into a fresh virtualenv. Runtime probes execute outside
the repository in Python isolated mode. No npm install or paid calls are made.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import runpy
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile


REQUIRED_RESOURCES = {
    "AGENTS.md", "CLAUDE.md", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", ".env.example",
    ".codex/config.toml", ".codex/agents/sf_discovery.toml", ".claude/agents/sf-discovery.md",
    "agents/orchestrator.md", "agents/discovery.md", "agents/assets_3d.md",
    "agents/youtube-creative-review-agent/youtube-script-creative-review-agent.md",
    "agents/youtube-creative-review-agent/src/gate.mjs", "docs/creative-review.md",
    "schemas/task-result.schema.json", "schemas/brief.schema.json", "schemas/words.schema.json",
    "templates/style-bible.json", "examples/brief-fiction-short.json", "docs/agent-hosts.md",
    "docs/contracts.md", "docs/assets/StoryForge-Render-Proofs.png", "renderer/README.md",
    "renderer/package.json", "renderer/package-lock.json", "renderer/remotion.config.ts",
    "renderer/tsconfig.json", "renderer/src/Root.tsx", "renderer/src/StoryVideo.tsx",
    "renderer/src/scene/Diorama.tsx", "renderer/scripts/render-video.mjs",
    "renderer/schema/manifest.schema.json", "renderer/examples/demo-short.json",
    "renderer/public/fonts/DejaVuSans.ttf", "renderer/public/fonts/DejaVuSerif.ttf",
    "renderer/public/fonts/LICENSE.txt",
}
FORBIDDEN_FIXTURES = (
    "renderer/node_modules/fake-private-package/index.js", "renderer/out/private.mp4",
    "renderer/build/private.js", "renderer/dist/private.js", "renderer/.cache/private.json",
    "docs/credentials-test.json", "docs/.env.local", "docs/BUILD_CONTRACT.md",
    "templates/private.key", "templates/private.pem", "examples/secrets-test.json",
    "runs/private-run.json", ".git/config", ".venv/private.json", ".env",
    "storyforge/_resources/stale-source-copy.txt",
    "build/lib/storyforge/_resources/stale-build-copy.txt",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def command(args: list[str], *, cwd: Path, env: dict[str, str], timeout: int = 120) -> str:
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {args!r}\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def check_wheel(path: Path, expected: dict[str, str], excluded) -> dict[str, str]:
    with zipfile.ZipFile(path) as archive:
        if archive.testzip():
            raise AssertionError(f"Corrupt wheel: {path.name}")
        names = archive.namelist()
        prefix = "storyforge/_resources/"
        actual = {name[len(prefix):]: sha(archive.read(name))
                  for name in names if name.startswith(prefix) and not name.endswith("/")}
        if actual != expected:
            raise AssertionError(
                f"Wheel resources differ from canonical files: missing={sorted(expected.keys() - actual.keys())}, "
                f"extra={sorted(actual.keys() - expected.keys())}, "
                f"changed={sorted(k for k in actual.keys() & expected.keys() if actual[k] != expected[k])}"
            )
        for name in names:
            relative = name[len(prefix):] if name.startswith(prefix) else name
            if excluded(Path(relative)):
                raise AssertionError(f"Forbidden wheel member: {name}")
        if "storyforge/resources.py" not in names:
            raise AssertionError("Resource resolver is missing from wheel")
    return actual


def unpack_sdist(path: Path, target: Path, expected: dict[str, str], excluded) -> Path:
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        roots = {PurePosixPath(member.name).parts[0] for member in members}
        if len(roots) != 1:
            raise AssertionError("sdist must have one root directory")
        for member in members:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts:
                raise AssertionError(f"Unsafe archive member: {member.name}")
            content_relative = Path(*relative.parts[1:])
            if excluded(content_relative):
                raise AssertionError(f"Forbidden sdist member: {member.name}")
            destination = target.joinpath(*relative.parts)
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                destination.parent.mkdir(parents=True, exist_ok=True)
                stream = archive.extractfile(member)
                if stream is None:
                    raise AssertionError(f"Unreadable archive member: {member.name}")
                with stream, destination.open("wb") as output:
                    shutil.copyfileobj(stream, output)
            else:
                raise AssertionError(f"Unexpected archive link/device: {member.name}")
        root = target / roots.pop()
        for name, digest in expected.items():
            if not (root / name).is_file() or sha((root / name).read_bytes()) != digest:
                raise AssertionError(f"Missing or changed sdist resource: {name}")
        for name in ("setup.py", "MANIFEST.in", "pyproject.toml", "storyforge/resources.py",
                     "scripts/verify_distribution.py", "tests/test_distribution.py"):
            if not (root / name).is_file():
                raise AssertionError(f"Missing sdist build/test input: {name}")
        return root


PROBE = r'''
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import storyforge
from storyforge.resources import resource_root
from storyforge.util import ROOT
from storyforge.intake import make_brief
from storyforge.store import Run
from storyforge.prompts import task_prompt
from storyforge.project import find_project
from storyforge.scaffold import setup_project

root = resource_root()
package = Path(storyforge.__file__).resolve().parent
assert root == package / "_resources", (root, package)
assert root.is_relative_to(Path(sys.prefix).resolve()), (root, sys.prefix)
assert ROOT == root
expected = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for relative, digest in expected.items():
    data = (root / relative).read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest, relative
assert len((root / "renderer/public/fonts/DejaVuSans.ttf").read_bytes()) > 100_000
assert len(list((root / ".codex/agents").glob("*.toml"))) >= 16
assert len(list((root / ".claude/agents").glob("*.md"))) >= 16
run = Run.create(make_brief(), Path.cwd() / "runs")
prompt = task_prompt(run, "discovery")
role = (root / "agents/discovery.md").read_text(encoding="utf-8")
assert role in prompt, "Installed role card was not loaded"
assert str(root / "schemas/task-result.schema.json") in prompt
assert importlib.metadata.version("storyforge-video") == storyforge.__version__
client = Path.cwd() / "existing client app"
client.mkdir()
application = b'{"name":"existing-client","private":true}\n'
instructions = b'# Existing project instructions\nPreserve this exact text.\n'
(client / "package.json").write_bytes(application)
(client / "AGENTS.md").write_bytes(instructions)
setup = setup_project(client)
project = find_project(client)
assert project is not None
assert (client / "package.json").read_bytes() == application
assert (client / "AGENTS.md").read_bytes().startswith(instructions)
assert (project.renderer / "package-lock.json").read_bytes() == (root / "renderer/package-lock.json").read_bytes()
assert (project.renderer / "public/fonts/DejaVuSans.ttf").read_bytes() == (root / "renderer/public/fonts/DejaVuSans.ttf").read_bytes()
for relative in (
    "agents/youtube-creative-review-agent/youtube-script-creative-review-agent.md",
    "agents/youtube-creative-review-agent/src/gate.mjs",
    "agents/youtube-creative-review-agent/schemas/review.schema.json",
    "agents/youtube-creative-review-agent/references/research-protocol.md",
    "docs/creative-review.md",
):
    assert (project.toolkit / relative).read_bytes() == (root / relative).read_bytes(), relative
assert len(list((client / ".codex/agents").glob("*.toml"))) == 16
assert len(list((client / ".claude/agents").glob("*.md"))) == 16
again = setup_project(client)
assert not again["created"] and not again["updated"], again
client_run = Run.create(make_brief(), project.runs, project_root=project.root)
client_prompt = task_prompt(client_run, "discovery")
assert f"TOOLKIT_ROOT: {project.toolkit}" in client_prompt
assert f"RENDERER_ROOT: {project.renderer}" in client_prompt
print(json.dumps({"version": storyforge.__version__, "resource_root": str(root),
                  "resource_files": len(expected), "role_packet": "passed", "project_setup": "passed"}))
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Keep verified wheels, sdist and report in this directory")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = runpy.run_path(str(root / "setup.py"))
    excluded = config["excluded"]
    inventory = config["resource_files"](root)
    expected = {name.as_posix(): sha((root / name).read_bytes()) for name in inventory}
    missing = REQUIRED_RESOURCES - expected.keys()
    if missing:
        raise AssertionError(f"Canonical resource inventory is incomplete: {sorted(missing)}")
    environment = {key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "PYTHONHOME"}}
    environment.update(PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_INDEX="1", SOURCE_DATE_EPOCH="1704067200")
    report: dict = {"resource_files": len(expected), "checks": [], "artifacts": []}
    with tempfile.TemporaryDirectory(prefix="storyforge-distribution-") as temporary:
        work = Path(temporary)
        source = work / "source"

        def ignore(directory: str, names: list[str]) -> list[str]:
            return [name for name in names if excluded((Path(directory) / name).relative_to(root))
                    or (Path(directory) / name).is_symlink()
                    or name.endswith(".egg-info")]

        shutil.copytree(root, source, ignore=ignore)
        for name in FORBIDDEN_FIXTURES:
            destination = source / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("PRIVATE TEST FIXTURE; MUST NOT SHIP\n", encoding="utf-8")
        dist = (args.output_dir.resolve() if args.output_dir else work / "artifacts")
        source_dist = dist / "source-wheel"
        rebuilt_dist = dist / "sdist-wheel"
        source_dist.mkdir(parents=True, exist_ok=True)
        rebuilt_dist.mkdir(parents=True, exist_ok=True)
        command([sys.executable, "-I", "-c", "import setuptools.build_meta as b, sys; b.build_wheel(sys.argv[1])", str(source_dist)],
                cwd=source, env=environment)
        wheels = list(source_dist.glob("*.whl"))
        if len(wheels) != 1:
            raise AssertionError(f"Expected one wheel, found {wheels}")
        wheel = wheels[0]
        check_wheel(wheel, expected, excluded)
        first_hash = sha(wheel.read_bytes())
        command([sys.executable, "-I", "-c", "import setuptools.build_meta as b, sys; b.build_wheel(sys.argv[1])", str(source_dist)],
                cwd=source, env=environment)
        if sha(wheel.read_bytes()) != first_hash:
            raise AssertionError("Repeated wheel builds with SOURCE_DATE_EPOCH are not reproducible")
        report["checks"].append("source wheel: exact resources, exclusions and reproducible bytes")
        command([sys.executable, "-I", "-c", "import setuptools.build_meta as b, sys; b.build_sdist(sys.argv[1])", str(dist)],
                cwd=source, env=environment)
        sdists = list(dist.glob("*.tar.gz"))
        if len(sdists) != 1:
            raise AssertionError(f"Expected one sdist, found {sdists}")
        sdist = sdists[0]
        extracted = unpack_sdist(sdist, work / "extracted", expected, excluded)
        command([sys.executable, "-I", "-c", "import setuptools.build_meta as b, sys; b.build_wheel(sys.argv[1])", str(rebuilt_dist)],
                cwd=extracted, env=environment)
        rebuilt = list(rebuilt_dist.glob("*.whl"))
        if len(rebuilt) != 1:
            raise AssertionError(f"Expected one rebuilt wheel, found {rebuilt}")
        check_wheel(rebuilt[0], expected, excluded)
        report["checks"].append("sdist: complete canonical source and clean rebuild with identical resources")
        shutil.rmtree(source)
        shutil.rmtree(work / "extracted")
        inventory_path = work / "inventory.json"
        inventory_path.write_text(json.dumps(expected, sort_keys=True), encoding="utf-8")
        for index, item in enumerate((wheel, rebuilt[0]), start=1):
            virtualenv = work / f"venv-{index}"
            venv.EnvBuilder(with_pip=True).create(virtualenv)
            executable_dir = virtualenv / ("Scripts" if os.name == "nt" else "bin")
            python = executable_dir / ("python.exe" if os.name == "nt" else "python")
            client = work / f"client-{index}"
            client.mkdir()
            command([str(python), "-I", "-m", "pip", "install", "--no-deps", "--no-index", str(item)],
                    cwd=client, env=environment)
            result = json.loads(command([str(python), "-I", "-c", PROBE, str(inventory_path)], cwd=client, env=environment))
            cli = executable_dir / ("storyforge.exe" if os.name == "nt" else "storyforge")
            version = command([str(cli), "--version"], cwd=client, env=environment)
            if version != result["version"]:
                raise AssertionError(f"CLI version differs: {version}")
            setup_result = json.loads(command([str(cli), "setup", str(client / "existing client app"), "--skip-install", "--json"],
                                              cwd=client, env=environment))
            if setup_result["created"] or setup_result["updated"]:
                raise AssertionError("Installed setup CLI did not preserve its initialized project")
            report["checks"].append(f"{'source' if index == 1 else 'sdist'} wheel: noneditable isolated install, CLI, existing-project setup, idempotent rerun and real role packets")
            report["version"] = result["version"]
        for item in (wheel, sdist, rebuilt[0]):
            report["artifacts"].append({"path": str(item), "bytes": item.stat().st_size, "sha256": sha(item.read_bytes())})
        report["passed"] = True
        if args.output_dir:
            (dist / "distribution-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        else:
            for item in report["artifacts"]:
                item["path"] = str(Path(item["path"]).relative_to(dist))
            report["artifact_retention"] = "temporary; use --output-dir to retain archives"
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
