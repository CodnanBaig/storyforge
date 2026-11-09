"""Studio gates: no self-advancing past an unapproved or stale choice."""
import base64
import tempfile
import unittest
from pathlib import Path

from storyforge.intake import make_brief
from storyforge.store import Run, StateError


def envelope(run, task, data, files=None):
    return {"schema_version": "1.0", "run_id": run.status()["run_id"], "task_id": task,
            "status": "complete", "summary": "Synthetic test, not a real video",
            "data": data, "files": files or [], "sources": [], "warnings": [], "blockers": []}


class StudioGatesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        brief = make_brief()
        brief["constraints"]["workflow_profile"] = "unified_studio_v1"
        self.run = Run.create(brief, Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def add_discovery(self):
        claim = self.run.claim("discovery", "fixture")
        result = self.run.submit("discovery", claim["token"], envelope(self.run, "discovery",
            {"candidates": [{"id": f"n{i}", "title": f"Topic {i}", "angle": "Synthetic angle",
                              "source_urls": ["https://example.org/source"]} for i in range(3)],
             "selected_id": "n0"}))
        self.assertTrue(result["accepted"], result)

    def add_style(self, missing=False):
        claim = self.run.claim("style", "fixture")
        concepts, files = [], []
        for i in range(3):
            path = Path(claim["workspace"]) / f"proof{i}.png"
            if not (missing and i == 0):
                path.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l/oAAAAASUVORK5CYII=") + b"\x00" * 200)
                files.append(str(path.relative_to(self.run.path)))
            concepts.append({"id": f"v{i}", "build_route": "Remotion SVG", "motion_limits": "2D",
                             "code_proof_path": str(path.relative_to(self.run.path))})
        return self.run.submit("style", claim["token"], envelope(self.run, "style",
            {"palette": {"background": "#112233"}, "font": "Arial", "characters": [],
             "asset_rules": [], "visual_concepts": concepts}, files))

    def test_selected_niche_overrides_provisional_scout_choice(self):
        self.add_discovery()
        self.assertNotIn("research", self.run.status()["ready"])
        with self.assertRaisesRegex(StateError, "niche approval"):
            self.run.claim("research", "without-consent")
        approved = self.run.approve_studio_gate("niche", "n2", "Owner preferred candidate n2")
        self.assertEqual(approved["choice"], "n2")
        self.assertIn("research", self.run.status()["ready"])
        self.assertEqual(self.run.context("research")["studio_gates"][0]["choice"], "n2")

    def test_invalidating_upstream_revokes_approval(self):
        self.add_discovery()
        self.run.approve_studio_gate("niche", "n0", "Owner chose candidate n0")
        self.run.invalidate("discovery", "Topic changed after review")
        self.add_discovery()
        self.assertEqual(self.run.status()["gates"][0]["status"], "awaiting_human")
        with self.assertRaisesRegex(StateError, "niche approval"):
            self.run.claim("research", "no-stale-consent")

    def test_visual_approval_requires_three_render_proofs(self):
        rejected = self.add_style(missing=True)
        self.assertFalse(rejected["accepted"])
        self.assertTrue(any("proof" in e for e in rejected["errors"]))
        self.run.retry("style")
        success = self.add_style()
        self.assertTrue(success["accepted"], success)
        visual = self.run.approve_studio_gate("visual", "v1", "Owner selected second visual")
        self.assertEqual(visual["status"], "approved")

    def test_final_gate_cannot_be_approved_before_packaging(self):
        with self.assertRaisesRegex(StateError, "until package is complete"):
            self.run.approve_studio_gate("final", "approve", "Owner reviewed final video")

    def test_other_briefs_keep_existing_behavior(self):
        legacy = Run.create(make_brief(), Path(self.tmp.name))
        self.assertEqual(legacy.status()["gates"], [])
        self.assertEqual(legacy.status()["ready"], ["discovery", "style"])


if __name__ == "__main__":
    unittest.main()
