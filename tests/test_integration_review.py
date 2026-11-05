"""Cross-stage regressions found during an independent integration review.

All evidence/media here is synthetic test data. Nothing is generated or released.
"""

import tempfile
import unittest
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from storyforge.contracts import validate_task
from storyforge.cli import main
from storyforge.demo import create_demo
from storyforge.intake import make_brief
from storyforge.store import Run, StateError
from storyforge.util import canonical, digest, write_json


class IntegrationReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.brief = make_brief()
        self.run = Run.create(self.brief, self.root)

    def result(self, task, data, files=None):
        return {"schema_version": "1.0", "run_id": self.run.status()["run_id"], "task_id": task,
                "status": "complete", "summary": "Synthetic integration regression fixture",
                "data": data, "files": files or [], "sources": [], "warnings": [], "blockers": []}

    def test_uncertain_request_cannot_be_duplicated_with_a_new_key(self):
        # Isolated ledger fixture: emulate already-passed upstream stages without
        # presenting this synthetic state as researched production.
        run = create_demo(self.root)
        with run.transaction() as conn:
            conn.execute("UPDATE meta SET value='false' WHERE key='demo'")
            brief = run._meta(conn, "brief")
            brief["budget"].update(max_media_jobs=10, max_media_cost_usd=100, max_media_credits=1000)
            write_json(run.path / "brief.json", brief)
            conn.execute("UPDATE meta SET value=? WHERE key='brief'", (canonical(brief),))
            conn.execute("UPDATE meta SET value=? WHERE key='brief_hash'", (canonical(digest(brief)),))
            conn.execute("UPDATE tasks SET status='complete' WHERE id='preflight'")
        claim = run.claim("voice", "regression-fixture")
        request = {"text": "The identical approved test script", "voice_id": "test-voice"}
        run.reserve_media("voice", claim["token"], job_key="request-original", provider="fixture",
                          request=request, estimated_usd=1, estimated_credits=20)
        run.record_media("request-original", status="uncertain")
        with self.assertRaises(StateError):
            run.reserve_media("voice", claim["token"], job_key="request-renamed", provider="fixture",
                              request=request, estimated_usd=1, estimated_credits=20)

    def test_qa_cannot_approve_an_explicitly_failing_technical_report(self):
        report = "delivery/technical-report.json"
        write_json(self.run.path / report, {"passed": False, "errors": ["Narration is missing"]})
        checks = {name: {"passed": True, "evidence": "Synthetic reviewer assertion"}
                  for name in ("visual", "audio", "captions", "facts", "rights", "originality", "disclosure")}
        result = self.result("qa", {"approved": True, "checks": checks, "technical_report_path": report}, [report])
        errors = validate_task("qa", result, self.brief, {}, self.run.path)
        self.assertTrue(errors, "A failed technical report must block QA even if the agent checks passed=true.")

    def test_package_must_contain_the_verified_render(self):
        notes = "delivery/title.txt"
        video = "delivery/verified-render.mp4"
        (self.run.path / notes).write_text("Synthetic packaging notes")
        (self.run.path / video).write_bytes(b"synthetic bytes; video validation is a separate tested stage")
        result = self.result("package", {"title": "Fixture", "description": "Fixture only", "credits": [],
                                        "delivery_files": [notes]}, [notes])
        outputs = {"render": {"data": {"video_path": video}}}
        errors = validate_task("package", result, self.brief, outputs, self.run.path)
        self.assertTrue(errors, "Delivering metadata without the accepted film is incomplete.")

    def test_voice_cannot_substitute_a_different_fixed_provider(self):
        self.brief["voice"]["provider"] = "elevenlabs"
        audio = "media/narration.wav"
        captions = "media/words.json"
        (self.run.path / audio).write_bytes(b"audio-probe-is-mocked-for-this-contract-test")
        write_json(self.run.path / captions, [{"text": "Fixture", "start": 0, "end": 1}])
        result = self.result("voice", {"provider": "other-tts", "audio_path": audio, "captions_path": captions,
                                      "duration_seconds": 2, "timing_source": "provider_alignment"}, [audio, captions])
        with patch("storyforge.media.probe_media", return_value={
            "streams": [{"codec_type": "audio"}], "format": {"duration": "2"}
        }):
            errors = validate_task("voice", result, self.brief, {}, self.run.path)
        self.assertTrue(errors, "A concrete approved provider must not be silently substituted.")

    def test_high_confidence_go_needs_actual_viability_evidence(self):
        scores = {name: 5 for name in ("demand", "competition_gap", "hook", "visual_potential", "source_quality", "production_fit")}
        result = self.result("viability", {"recommendation": "go", "confidence": "high",
                                          "score_components": scores, "evidence": []})
        errors = validate_task("viability", result, self.brief, {}, self.run.path)
        self.assertTrue(errors, "Unsupported scores and an empty evidence list cannot pass a real reach review.")

    def test_native_dispatch_claim_counts_and_obeys_the_worker_budget(self):
        self.brief["budget"]["max_model_calls"] = 1
        self.run.amend(self.brief)
        captured = io.StringIO()
        with redirect_stdout(captured):
            first = main(["claim", str(self.run.path), "discovery", "--worker", "native-scout", "--model-call"])
        self.assertEqual(first, 0)
        packet = json.loads(captured.getvalue())
        self.assertEqual(Path(packet["prompt_path"]).parent, Path(packet["workspace"]))
        self.assertIn("attempt-1", packet["workspace"])
        self.assertEqual(self.run.status()["worker_calls"], 1)
        with redirect_stdout(io.StringIO()):
            second = main(["claim", str(self.run.path), "style", "--worker", "native-artist", "--model-call"])
        self.assertEqual(second, 2)
        style = next(row for row in self.run.status()["tasks"] if row["id"] == "style")
        self.assertEqual(style["status"], "pending")

    def test_package_accepts_a_hash_identical_copy_of_the_verified_film(self):
        source = "delivery/render-original.mp4"
        copied = "delivery/final.mp4"
        content = b"same verified film fixture bytes"
        (self.run.path / source).write_bytes(content)
        (self.run.path / copied).write_bytes(content)
        result = self.result("package", {"title": "Fixture", "description": "Fixture only", "credits": [],
                                        "delivery_files": [copied]}, [copied])
        errors = validate_task("package", result, self.brief,
                               {"render": {"data": {"video_path": source}}, "qa": {"data": {"reviewed_packaging": {"title": "Fixture", "description": "Fixture only", "credits": []}}}}, self.run.path)
        self.assertEqual(errors, [])

    def test_final_packaging_cannot_change_after_independent_review(self):
        video = "delivery/verified.mp4"; (self.run.path / video).write_bytes(b"synthetic verified bytes")
        approved = {"title": "Reviewed title", "description": "Reviewed description", "credits": []}
        result = self.result("package", {**approved, "title": "Unreviewed sensational claim", "delivery_files": [video]}, [video])
        outputs = {"render": {"data": {"video_path": video}}, "qa": {"data": {"reviewed_packaging": approved}}}
        errors = validate_task("package", result, self.brief, outputs, self.run.path)
        self.assertTrue(any("Final title" in e for e in errors))

    def test_measured_hook_must_fit_the_agreed_limit(self):
        audio = "media/hook.wav"; (self.run.path / audio).write_bytes(b"fixture")
        words = "media/hook-words.json"; write_json(self.run.path / words, [{"text": "Fixture", "start": 0, "end": 4}])
        result = self.result("voice", {"provider": "external", "audio_path": audio, "duration_seconds": 5,
                            "captions_path": words, "timing_source": "human_verified", "hook_end_seconds": 4}, [audio, words])
        with patch("storyforge.media.probe_media", return_value={"streams": [{"codec_type": "audio"}], "format": {"duration": "5"}}):
            errors = validate_task("voice", result, self.brief, {}, self.run.path)
        self.assertTrue(any("hook_end_seconds" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
