import hashlib
import json
import os
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from storyforge import __version__
from storyforge.project import find_project, load_project
from storyforge.resources import resource_root
from storyforge.scaffold import SetupConflictError, setup_project


def snapshot(root):
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file() and not path.is_symlink()}


class ProjectSetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.resources = self.root / "resources"
        fixture = {
            "AGENTS.md": "# Canonical producer instructions\n",
            "CLAUDE.md": "# Claude producer instructions\n",
            "LICENSE": "Synthetic test license\n",
            "THIRD_PARTY_NOTICES.md": "Synthetic test notices\n",
            "README.md": "Synthetic toolkit fixture\n",
            ".env.example": "ELEVENLABS_API_KEY=\n",
            "agents/discovery.md": "Research with evidence.\n",
            "docs/agent-hosts.md": "Use the installed storyforge CLI.\n",
            "schemas/task-result.schema.json": "{}\n",
            "templates/intake.md": "Ask the required questions.\n",
            "examples/brief.json": "{}\n",
            "renderer/package.json": '{"name":"fixture-renderer","private":true}\n',
            "renderer/package-lock.json": '{"lockfileVersion":3}\n',
            "renderer/src/index.ts": "export const scene = 'original';\n",
            "renderer/public/fonts/fixture.ttf": "Synthetic font bytes\n",
            ".codex/agents/sf_discovery.toml": 'name = "sf_discovery"\n',
            ".claude/agents/sf-discovery.md": "---\nname: sf-discovery\n---\n",
        }
        for name, content in fixture.items():
            self.write(self.resources / name, content)
        self.patch = patch("storyforge.scaffold.resource_root", return_value=self.resources)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.project = self.root / "project"

    @staticmethod
    def write(path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    @staticmethod
    def config(**overrides):
        return {"schema_version": "1.0", "toolkit_version": __version__, "hosts": [],
                "paths": {"toolkit": ".storyforge", "renderer": ".storyforge/renderer", "runs": ".storyforge/runs"}, **overrides}

    def test_fresh_setup_and_discovery_from_run_or_file(self):
        report = setup_project(self.project)
        project = load_project(self.project)
        self.assertEqual(project.root, self.project.resolve())
        self.assertEqual(report["hosts"], ["claude", "codex"])
        self.assertEqual(project.renderer, self.project / ".storyforge/renderer")
        self.assertEqual(project.runs, self.project / ".storyforge/runs")
        self.assertTrue((project.toolkit / "WORKFLOW.md").is_file())
        self.assertTrue((project.renderer / "public/fonts/fixture.ttf").is_file())
        self.assertFalse((self.project / "package.json").exists())
        self.assertEqual(find_project(project.runs / "new-run"), project)
        self.assertEqual(find_project(project.renderer / "src/index.ts"), project)
        self.assertIsNone(find_project(self.root / "unrelated"))
        self.assertEqual(tomllib.loads((self.project / ".codex/config.toml").read_text())["agents"]["enabled"], True)
        self.assertIn("/.storyforge/runs/", (self.project / ".gitignore").read_text())
        self.assertIn("/.storyforge/previews/", (self.project / ".gitignore").read_text())

    def test_rerun_is_a_noop_and_keeps_manifest_stable(self):
        setup_project(self.project)
        before = snapshot(self.project)
        report = setup_project(self.project)
        self.assertEqual(report["created"], [])
        self.assertEqual(report["updated"], [])
        self.assertEqual(snapshot(self.project), before)
        self.assertEqual((self.project / "AGENTS.md").read_text().count("<!-- storyforge:begin -->"), 1)

    def test_existing_application_instructions_and_codex_settings_survive(self):
        package = '{"name":"existing-react-app","scripts":{"dev":"vite"}}\n'
        codex = 'model = "owner-selected"\n\n[agents]\nenabled = false\nmax_concurrent_threads_per_session = 1\n'
        self.write(self.project / "package.json", package)
        self.write(self.project / "AGENTS.md", "# Existing project\nKeep my architecture decisions.")
        self.write(self.project / "CLAUDE.md", "Use existing React components.\n")
        self.write(self.project / ".gitignore", "existing-cache/\n")
        self.write(self.project / ".codex/config.toml", codex)
        self.write(self.project / ".codex/agents/my-own-agent.toml", 'name = "my-own-agent"\n')
        report = setup_project(self.project)
        self.assertEqual((self.project / "package.json").read_text(), package)
        self.assertEqual((self.project / ".codex/config.toml").read_text(), codex)
        self.assertTrue(any("explicitly disabled" in warning for warning in report["warnings"]))
        self.assertTrue((self.project / "AGENTS.md").read_text().startswith("# Existing project\nKeep my architecture decisions.\n\n"))
        agents = self.project / "AGENTS.md"
        agents.write_text("New owner instruction.\n" + agents.read_text() + "\nFurther owner instructions.\n")
        before = agents.read_bytes()
        setup_project(self.project)
        self.assertEqual(agents.read_bytes(), before)
        self.assertTrue((self.project / ".codex/agents/my-own-agent.toml").exists())
        self.assertTrue((self.project / ".gitignore").read_text().startswith("existing-cache/\n"))

    def test_hosts_can_be_added_without_deleting_an_existing_integration(self):
        setup_project(self.project, host="none")
        self.assertFalse((self.project / ".codex").exists())
        self.assertFalse((self.project / ".claude").exists())
        self.assertFalse((self.project / "AGENTS.md").exists())
        setup_project(self.project, host="codex")
        self.assertTrue((self.project / ".codex/agents/sf_discovery.toml").exists())
        self.assertFalse((self.project / ".claude").exists())
        report = setup_project(self.project, host="claude")
        self.assertEqual(report["hosts"], ["claude", "codex"])
        self.assertTrue((self.project / ".claude/agents/sf-discovery.md").exists())
        self.assertEqual(setup_project(self.project, host="none")["hosts"], ["claude", "codex"])

    def test_same_release_preserves_local_renderer_customization_and_baseline(self):
        setup_project(self.project)
        source = self.project / ".storyforge/renderer/src/index.ts"
        manifest = self.project / ".storyforge/installation.json"
        before_manifest = manifest.read_bytes()
        source.write_text("export const scene = 'my custom scene';\n")
        report = setup_project(self.project)
        self.assertEqual(source.read_text(), "export const scene = 'my custom scene';\n")
        self.assertEqual(manifest.read_bytes(), before_manifest)
        self.assertTrue(any("Preserved local customization" in warning for warning in report["warnings"]))
        self.assertEqual(report["updated"], [])

    def test_clean_resource_upgrade_updates_managed_files_and_retains_owner_text(self):
        setup_project(self.project)
        self.write(self.resources / "renderer/src/index.ts", "export const scene = 'upgraded';\n")
        self.write(self.resources / "docs/new-guide.md", "A new bundled guide.\n")
        agents = self.project / "AGENTS.md"
        agents.write_text("Owner's instructions.\n" + agents.read_text())
        with patch("storyforge.scaffold.__version__", "0.3.0"):
            report = setup_project(self.project)
        self.assertIn(".storyforge/renderer/src/index.ts", report["updated"])
        self.assertEqual((self.project / ".storyforge/renderer/src/index.ts").read_text(), "export const scene = 'upgraded';\n")
        self.assertTrue((self.project / ".storyforge/docs/new-guide.md").exists())
        self.assertTrue(agents.read_text().startswith("Owner's instructions.\n"))
        self.assertEqual(load_project(self.project).config["toolkit_version"], "0.3.0")

    def test_overlapping_upgrade_reports_all_conflicts_before_writing(self):
        setup_project(self.project)
        self.write(self.project / ".storyforge/renderer/src/index.ts", "Owner's scene.\n")
        self.write(self.project / ".storyforge/agents/discovery.md", "Owner's role.\n")
        self.write(self.resources / "renderer/src/index.ts", "New upstream scene.\n")
        self.write(self.resources / "agents/discovery.md", "New upstream role.\n")
        self.write(self.resources / "docs/new-guide.md", "This must not be written yet.\n")
        before = snapshot(self.project)
        with self.assertRaises(SetupConflictError) as caught:
            setup_project(self.project)
        self.assertEqual(len(caught.exception.conflicts), 2)
        self.assertEqual(snapshot(self.project), before)

    def test_keep_local_acknowledges_a_merged_upgrade_until_the_next_upstream_change(self):
        setup_project(self.project)
        relative = ".storyforge/renderer/src/index.ts"
        local = self.project / relative
        upstream = self.resources / "renderer/src/index.ts"
        local.write_text("Owner's manually merged scene.\n")
        upstream.write_text("New upstream scene.\n")
        with self.assertRaises(SetupConflictError):
            setup_project(self.project)
        merged_bytes = local.read_bytes()
        report = setup_project(self.project, keep_local=[relative])
        self.assertEqual(local.read_bytes(), merged_bytes)
        manifest = json.loads((self.project / ".storyforge/installation.json").read_text())
        self.assertEqual(manifest["files"][relative], hashlib.sha256(upstream.read_bytes()).hexdigest())
        self.assertTrue(any("Acknowledged --keep-local" in warning for warning in report["warnings"]))
        before = snapshot(self.project)
        rerun = setup_project(self.project)
        self.assertEqual(rerun["updated"], [])
        self.assertEqual(snapshot(self.project), before)
        upstream.write_text("A subsequent upstream revision.\n")
        with self.assertRaises(SetupConflictError):
            setup_project(self.project)
        self.assertEqual(snapshot(self.project), before)

    def test_keep_local_cannot_adopt_an_unmanaged_file_or_skip_instruction_conflicts(self):
        relative = ".storyforge/renderer/src/index.ts"
        self.write(self.project / relative, "Unmanaged scene.\n")
        before = snapshot(self.project)
        with self.assertRaisesRegex(SetupConflictError, "previously managed ordinary resource"):
            setup_project(self.project, keep_local=[relative])
        self.assertEqual(snapshot(self.project), before)
        (self.project / relative).unlink()
        setup_project(self.project)
        agents = self.project / "AGENTS.md"
        agents.write_text(agents.read_text().replace("## StoryForge video production", "## Custom managed block"))
        before = snapshot(self.project)
        with self.assertRaisesRegex(SetupConflictError, "managed block was edited"):
            setup_project(self.project, keep_local=["AGENTS.md"])
        self.assertEqual(snapshot(self.project), before)

    def test_keep_local_rejects_protected_unknown_and_missing_paths_without_writes(self):
        setup_project(self.project)
        for relative in ("storyforge.json", ".storyforge/installation.json", ".codex/config.toml", ".gitignore", "AGENTS.md", ".storyforge/docs/not-a-resource.md", "../outside"):
            with self.subTest(relative=relative):
                before = snapshot(self.project)
                with self.assertRaises(ValueError):
                    setup_project(self.project, keep_local=[relative])
                self.assertEqual(snapshot(self.project), before)
        missing = ".storyforge/renderer/src/index.ts"
        (self.project / missing).unlink()
        before = snapshot(self.project)
        with self.assertRaisesRegex(SetupConflictError, "requires an existing local resource"):
            setup_project(self.project, keep_local=(missing,))
        self.assertEqual(snapshot(self.project), before)

    def test_unmanaged_conflict_leaves_existing_project_untouched(self):
        self.write(self.project / ".storyforge/renderer/src/index.ts", "Unmanaged user's file.\n")
        self.write(self.project / "package.json", '{"name":"my-app"}\n')
        before = snapshot(self.project)
        with self.assertRaisesRegex(SetupConflictError, "unmanaged"):
            setup_project(self.project)
        self.assertEqual(snapshot(self.project), before)
        self.assertFalse((self.project / "storyforge.json").exists())

    def test_identical_unmanaged_resource_can_be_adopted_then_upgraded(self):
        source = self.resources / "renderer/src/index.ts"
        self.write(self.project / ".storyforge/renderer/src/index.ts", source.read_text())
        setup_project(self.project)
        source.write_text("A managed upgrade.\n")
        setup_project(self.project)
        self.assertEqual((self.project / ".storyforge/renderer/src/index.ts").read_text(), "A managed upgrade.\n")

    def test_edited_managed_instruction_block_is_not_overwritten_or_adopted(self):
        setup_project(self.project)
        agents = self.project / "AGENTS.md"
        agents.write_text(agents.read_text().replace("## StoryForge video production", "## Owner-modified block"))
        self.write(self.resources / "docs/new-guide.md", "No partial update.\n")
        before = snapshot(self.project)
        with self.assertRaisesRegex(SetupConflictError, "managed block was edited"):
            setup_project(self.project)
        self.assertEqual(snapshot(self.project), before)

    def test_malformed_or_duplicate_instruction_markers_block_setup(self):
        for markers in ("<!-- storyforge:begin -->\n", "<!-- storyforge:begin -->\n<!-- storyforge:begin -->\n<!-- storyforge:end -->\n"):
            with self.subTest(markers=markers):
                project = self.root / ("duplicate" if markers.count("begin") == 2 else "incomplete")
                self.write(project / "AGENTS.md", "Owner text.\n" + markers)
                before = snapshot(project)
                with self.assertRaisesRegex(SetupConflictError, "duplicate or incomplete"):
                    setup_project(project)
                self.assertEqual(snapshot(project), before)

    def test_codex_agent_settings_are_added_without_rewriting_other_tables(self):
        prefix = 'model = "owner-model"\n\n[features]\nsome_feature = true\n'
        self.write(self.project / ".codex/config.toml", prefix)
        setup_project(self.project, host="codex")
        text = (self.project / ".codex/config.toml").read_text()
        self.assertTrue(text.startswith(prefix))
        config = tomllib.loads(text)
        self.assertEqual(config["model"], "owner-model")
        self.assertEqual(config["agents"]["max_concurrent_threads_per_session"], 3)

    def test_invalid_existing_codex_config_is_preserved_with_no_partial_setup(self):
        self.write(self.project / ".codex/config.toml", "[agents\ninvalid\n")
        before = snapshot(self.project)
        with self.assertRaisesRegex(SetupConflictError, "Codex settings"):
            setup_project(self.project)
        self.assertEqual(snapshot(self.project), before)

    @unittest.skipUnless(hasattr(os, "symlink"), "Symlink containment checks")
    def test_symlinks_cannot_redirect_any_managed_write(self):
        for relative in (".storyforge", ".storyforge/renderer/public", ".codex/agents", "AGENTS.md", "storyforge.json"):
            with self.subTest(relative=relative):
                project = self.root / ("case-" + relative.replace("/", "-"))
                outside = self.root / ("outside-" + relative.replace("/", "-"))
                outside.mkdir()
                self.write(outside / "owner.txt", "Must remain unchanged.\n")
                target = project / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if relative in {"AGENTS.md", "storyforge.json"}:
                    target.symlink_to(outside / "owner.txt")
                else:
                    target.symlink_to(outside, target_is_directory=True)
                before_outside = snapshot(outside)
                before_project = snapshot(project)
                with self.assertRaisesRegex(ValueError, "symlink"):
                    setup_project(project)
                self.assertEqual(snapshot(outside), before_outside)
                self.assertEqual(snapshot(project), before_project)

    @unittest.skipUnless(hasattr(os, "symlink"), "Symlink containment checks")
    def test_selected_project_directory_cannot_itself_be_a_symlink(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.project.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            setup_project(self.project)
        self.assertEqual(list(outside.iterdir()), [])

    def test_project_configuration_rejects_traversal_absolute_and_git_paths(self):
        for value in ("../outside", str(self.root / "outside"), "C:\\outside", ".git/resources", ".storyforge/../outside", "resources\nunsafe"):
            with self.subTest(value=value):
                config = self.config(paths={"toolkit": value, "renderer": ".storyforge/renderer", "runs": ".storyforge/runs"})
                self.write(self.project / "storyforge.json", json.dumps(config))
                before = snapshot(self.project)
                with self.assertRaises(ValueError):
                    find_project(self.project)
                with self.assertRaises(ValueError):
                    setup_project(self.project)
                self.assertEqual(snapshot(self.project), before)

    def test_nearest_project_is_authoritative_even_if_it_is_invalid(self):
        self.write(self.project / "storyforge.json", json.dumps(self.config()))
        nested = self.project / "nested"
        self.write(nested / "storyforge.json", json.dumps(self.config()))
        self.assertEqual(find_project(nested / "future/run").root, nested)
        (nested / "storyforge.json").write_text("not json")
        with self.assertRaisesRegex(ValueError, "Cannot read storyforge.json"):
            find_project(nested / "future/run")

    def test_custom_contained_paths_and_config_keys_are_preserved(self):
        config = self.config(paths={"toolkit": ".video-kit", "renderer": "video renderer", "runs": "video-runs"}, channel={"name": "Owner's channel"})
        original = json.dumps(config, indent=4) + "\n"
        self.write(self.project / "storyforge.json", original)
        report = setup_project(self.project, host="none")
        self.assertEqual(report["renderer_root"], str(self.project / "video renderer"))
        self.assertTrue((self.project / "video renderer/src/index.ts").exists())
        self.assertTrue((self.project / ".video-kit/installation.json").exists())
        self.assertEqual((self.project / "storyforge.json").read_text(), original)
        self.assertIn("/video\\ renderer/node_modules/", (self.project / ".gitignore").read_text())
        setup_project(self.project, host="claude")
        updated = load_project(self.project).config
        self.assertEqual(updated["channel"], config["channel"])
        self.assertEqual(updated["paths"], config["paths"])

    def test_credentials_dependencies_and_output_trees_are_not_scaffolded(self):
        excluded = (
            "renderer/node_modules/module/secret.js", "renderer/out/movie.mp4", "renderer/build/bundle.js",
            "renderer/.env", "renderer/.env.local", "renderer/credentials-private.json", "docs/private.key",
            "renderer/.npmrc", "docs/.pypirc", "renderer/.netrc", "docs/secrets-local.json",
            "renderer/.cache/private.json", "renderer/cache/private.json", "docs/toolkit.egg-info/local.json",
            "renderer/_resources/local.json", "docs/.storyforge/local.json",
        )
        for relative in excluded:
            self.write(self.resources / relative, "Do not copy.\n")
        setup_project(self.project)
        for relative in excluded:
            self.assertFalse((self.project / ".storyforge" / relative).exists(), relative)

    @unittest.skipUnless(hasattr(os, "symlink"), "Symlink containment checks")
    def test_source_host_ancestor_symlink_cannot_import_external_files(self):
        source_host = self.resources / ".codex"
        outside_host = self.root / "external-codex"
        source_host.rename(outside_host)
        source_host.symlink_to(outside_host, target_is_directory=True)
        self.write(outside_host / "agents/private.md", "External private source data.\n")
        with self.assertRaisesRegex(ValueError, "resource uses a symlink"):
            setup_project(self.project)
        self.assertFalse(self.project.exists())

    def test_colliding_custom_paths_fail_before_creating_a_partial_installation(self):
        for key, value in (("toolkit", "AGENTS.md"), ("runs", ".storyforge/docs/agent-hosts.md"), ("renderer", "storyforge.json/renderer")):
            with self.subTest(key=key, value=value):
                config = self.config()
                config["paths"][key] = value
                self.write(self.project / "storyforge.json", json.dumps(config))
                before = snapshot(self.project)
                with self.assertRaises(ValueError):
                    setup_project(self.project)
                self.assertEqual(snapshot(self.project), before)


class BundledScaffoldTests(unittest.TestCase):
    def test_real_resource_set_installs_all_native_workers_and_renderer_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "real-project"
            report = setup_project(project)
            self.assertEqual(len(list((project / ".codex/agents").glob("sf_*.toml"))), 16)
            self.assertEqual(len(list((project / ".claude/agents").glob("sf-*.md"))), 16)
            self.assertTrue((project / ".storyforge/renderer/package-lock.json").is_file())
            self.assertGreater(len(list((project / ".storyforge/renderer/public/fonts").glob("*.ttf"))), 0)
            source = resource_root()
            manifest = json.loads((project / ".storyforge/installation.json").read_text())
            for relative in ("renderer/package-lock.json", "agents/discovery.md", "schemas/task-result.schema.json"):
                expected = hashlib.sha256((source / relative).read_bytes()).hexdigest()
                self.assertEqual(manifest["files"][".storyforge/" + relative], expected)
            for directory, pattern in ((project / ".codex/agents", "*.toml"), (project / ".claude/agents", "*.md")):
                for wrapper in directory.glob(pattern):
                    text = wrapper.read_text()
                    self.assertIn("TOOLKIT_ROOT/agents/", text)
                    self.assertIn("RENDERER_ROOT", text)
                    self.assertNotIn("PROJECT_ROOT/agents/", text)
            self.assertFalse(report["warnings"])


if __name__ == "__main__":
    unittest.main()
