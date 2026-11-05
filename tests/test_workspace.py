"""Project/CLI integration checks; renderer processes and providers are mocked."""
from __future__ import annotations

import io
import hashlib
import json
import subprocess
import tempfile
import unittest
from contextlib import chdir, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from storyforge.cli import main
from storyforge.intake import make_brief
from storyforge.project import find_project
from storyforge.prompts import task_prompt
from storyforge.scaffold import setup_project
from storyforge.store import Run, StateError
from storyforge.util import write_json
from storyforge.workspace import (doctor, install_renderer, renderer_command,
                                 renderer_dependencies, run_resource_paths)


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.client = self.root / "existing app with spaces"
        setup_project(self.client, host="none")
        self.project = find_project(self.client)
        self.assertIsNotNone(self.project)

    def invoke(self, arguments):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(arguments)
        return code, json.loads(output.getvalue())

    def fake_dependencies(self):
        for name in ("remotion", "@remotion/cli", "@remotion/renderer", "typescript"):
            target = self.project.renderer / "node_modules" / name / "package.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('{"name":"synthetic fixture"}', encoding="utf-8")
        manifest = (self.project.renderer / "package.json").read_bytes()
        lock = (self.project.renderer / "package-lock.json").read_bytes()
        (self.project.renderer / "node_modules" / ".storyforge-lock.sha256").write_text(
            hashlib.sha256(manifest + b"\0" + lock).hexdigest() + "\n", encoding="utf-8")

    def test_start_with_saved_brief_never_repeats_intake_and_uses_project_runs(self):
        brief = self.root / "brief.json"
        write_json(brief, make_brief(project_name="Saved channel brief"))
        with chdir(self.root), patch("storyforge.cli.interactive", side_effect=AssertionError("Intake must not run")):
            code, result = self.invoke(["start", "--project", str(self.client), "--brief", str(brief), "--json"])
        self.assertEqual(code, 0)
        run_path = Path(result["path"])
        self.assertEqual(run_path.parent, self.project.runs)
        self.assertEqual(result["ready"], ["discovery", "style"])
        self.assertEqual(json.loads((run_path / "brief.json").read_text())["project_name"], "Saved channel brief")
        self.assertEqual(result["worker_calls"], 0)

    def test_init_and_demo_use_project_runs_from_a_subdirectory(self):
        nested = self.client / "src" / "components"
        nested.mkdir(parents=True)
        brief = self.root / "brief.json"
        write_json(brief, make_brief())
        with chdir(nested):
            code, run = self.invoke(["init", "--brief", str(brief)])
            demo_code, demo = self.invoke(["demo"])
        self.assertEqual((code, demo_code), (0, 0))
        self.assertEqual(Path(run["path"]).parent, self.project.runs)
        self.assertEqual(Path(demo["path"]).parent, self.project.runs)
        self.assertEqual(demo["counts"]["complete"], 7)
        self.assertFalse(demo["delivered"])
        self.assertFalse((nested / "runs").exists())

    def test_external_runs_retain_the_selected_project_for_later_workers(self):
        brief = self.root / "brief.json"
        write_json(brief, make_brief())
        external = self.root / "external-disk" / "productions"
        with chdir(self.root):
            code, result = self.invoke(["start", "--project", str(self.client), "--runs-dir", str(external),
                                       "--brief", str(brief), "--json"])
        self.assertEqual(code, 0)
        run = Run(Path(result["path"]))
        self.assertEqual(run.path.parent, external)
        self.assertEqual(run.project_root(), self.project.root)
        self.assertEqual(run_resource_paths(run.path)["renderer"], self.project.renderer)
        self.assertIn(f"TOOLKIT_ROOT: {self.project.toolkit}", task_prompt(run, "discovery"))

    def test_moved_external_project_does_not_silently_switch_to_bundled_roles(self):
        run = Run.create(make_brief(), self.root / "outside-runs", project_root=self.project.root)
        self.client.rename(self.root / "moved-project")
        with self.assertRaisesRegex(StateError, "no longer at"):
            task_prompt(run, "discovery")

    def test_setup_rerun_from_subdirectory_preserves_host_selection_and_root(self):
        nested = self.client / "src"
        nested.mkdir()
        with chdir(nested), patch("storyforge.workspace.install_renderer", side_effect=AssertionError("No npm calls")):
            code, result = self.invoke(["setup", "--skip-install", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(result["hosts"], [])
        self.assertEqual(Path(result["project_root"]), self.client)
        self.assertFalse((nested / "storyforge.json").exists())

    def test_worker_packet_uses_its_run_project_and_locally_customized_role(self):
        run = Run.create(make_brief(), self.project.runs)
        role = self.project.toolkit / "agents" / "discovery.md"
        role.write_text(role.read_text() + "\nProject-specific instruction fixture.\n", encoding="utf-8")
        other = self.root / "other-project"
        setup_project(other, host="none")
        with chdir(other):
            packet = task_prompt(run, "discovery")
        self.assertIn("Project-specific instruction fixture.", packet)
        self.assertIn(f"PROJECT_ROOT: {self.client}", packet)
        self.assertIn(f"TOOLKIT_ROOT: {self.project.toolkit}", packet)
        self.assertIn(f"RENDERER_ROOT: {self.project.renderer}", packet)
        self.assertIn(f"RUN_DIR: {run.path}", packet)
        self.assertEqual(run_resource_paths(run.path)["toolkit"], self.project.toolkit)
        self.assertNotIn(f"PROJECT_ROOT: {other}", packet)

    def test_preview_passes_caller_paths_as_literal_argv_from_project_renderer(self):
        self.fake_dependencies()
        props = self.root / "props with $literal; words.json"
        props.write_text('{}', encoding="utf-8")
        destination = self.root / "frames with spaces"
        with chdir(self.root), patch("storyforge.workspace._node_details", return_value={"supported": True}), \
                patch("storyforge.workspace.shutil.which", return_value="/fixture/npm"), \
                patch("storyforge.workspace.subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as invoked:
            code = renderer_command("preview", start=self.client, props=Path(props.name),
                                    output=Path(destination.name), frames="0,120", scale=0.25)
        self.assertEqual(code, 0)
        argv = invoked.call_args.args[0]
        self.assertEqual(argv[:4], ["/fixture/npm", "run", "stills", "--"])
        self.assertEqual(argv[argv.index("--props") + 1], str(props))
        self.assertEqual(argv[argv.index("--out") + 1], str(destination))
        self.assertEqual(invoked.call_args.kwargs["cwd"], self.project.renderer)
        self.assertNotIn("shell", invoked.call_args.kwargs)

    def test_preview_refuses_to_replace_an_existing_output_directory(self):
        self.fake_dependencies()
        destination = self.root / "already-rendered"
        destination.mkdir()
        saved = destination / "important.png"
        saved.write_bytes(b"preserve me")
        with patch("storyforge.workspace._node_details", return_value={"supported": True}), \
                patch("storyforge.workspace.shutil.which", return_value="/fixture/npm"), \
                patch("storyforge.workspace.subprocess.run") as invoked:
            with self.assertRaisesRegex(StateError, "not an empty directory"):
                renderer_command("preview", start=self.client, output=destination)
        invoked.assert_not_called()
        self.assertEqual(saved.read_bytes(), b"preserve me")

    def test_install_renderer_reuses_matching_lockfile_and_reinstalls_after_change(self):
        def npm_ci(*args, **kwargs):
            self.fake_dependencies()
            return subprocess.CompletedProcess(args[0], 0)

        with patch("storyforge.workspace._node_details", return_value={"supported": True}), \
                patch("storyforge.workspace.shutil.which", return_value="/fixture/npm"), \
                patch("storyforge.workspace.subprocess.run", side_effect=npm_ci) as invoked:
            first = install_renderer(self.project)
            second = install_renderer(self.project)
            self.assertEqual((first["status"], second["status"]), ("installed", "already_installed"))
            self.assertEqual(invoked.call_count, 1)
            lock = self.project.renderer / "package-lock.json"
            lock.write_text(lock.read_text() + "\n", encoding="utf-8")
            third = install_renderer(self.project)
            self.assertEqual(third["status"], "installed")
            self.assertEqual(invoked.call_count, 2)
        self.assertTrue(renderer_dependencies(self.project.renderer)["lockfile_current"])
        self.assertEqual(invoked.call_args.args[0], ["/fixture/npm", "ci", "--no-fund", "--no-audit"])

    def test_failed_npm_install_keeps_scaffold_and_does_not_mark_dependencies_ready(self):
        with patch("storyforge.workspace._node_details", return_value={"supported": True}), \
                patch("storyforge.workspace.shutil.which", return_value="/fixture/npm"), \
                patch("storyforge.workspace.subprocess.run", return_value=subprocess.CompletedProcess([], 1)):
            with self.assertRaisesRegex(StateError, "Project files are ready"):
                install_renderer(self.project)
        self.assertTrue((self.client / "storyforge.json").is_file())
        self.assertFalse((self.project.renderer / "node_modules" / ".storyforge-lock.sha256").exists())

    def test_doctor_reports_missing_project_resources_without_hiding_saved_runs(self):
        run = Run.create(make_brief(), self.project.runs)
        missing = self.project.renderer / "package-lock.json"
        missing.unlink()
        report = doctor(self.client)
        self.assertIn(str(missing), report["missing_project_resources"])
        self.assertFalse(report["preview_ready"])
        self.assertTrue(run.db.is_file())
        self.assertTrue(any("restore missing" in action for action in report["actions"]))

    def test_studio_requires_setup_and_never_installs_into_package_resources(self):
        with chdir(self.root):
            with self.assertRaisesRegex(StateError, "storyforge setup"):
                renderer_command("studio")


if __name__ == "__main__":
    unittest.main()
