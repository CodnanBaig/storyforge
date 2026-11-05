"""Tests use synthetic fixtures, never live research or paid media services."""
from __future__ import annotations

import copy
import json
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from storyforge.contracts import ValidationError, validate_brief, validate_task
from storyforge.demo import create_demo
from storyforge.intake import make_brief
from storyforge.store import Run, StateError
from storyforge.util import canonical, read_json, safe_path, write_json


def envelope(run: Run, task: str, data: dict, files: list[str] | None = None) -> dict:
    return {"schema_version": "1.0", "run_id": run.status()["run_id"], "task_id": task,
            "status": "complete", "summary": "Synthetic test fixture", "data": data,
            "files": files or [], "sources": [], "warnings": [], "blockers": []}


def discovery(run: Run) -> dict:
    return envelope(run, "discovery", {"candidates": [{"id": str(i), "title": f"Fixture {i}",
                    "angle": "Synthetic contract test", "source_urls": ["https://example.invalid/fixture"]} for i in range(3)], "selected_id": "0"})


class CoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.brief = make_brief()
        self.run = Run.create(self.brief, self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_initial_parallel_tasks_and_dependency_gates(self):
        self.assertEqual(self.run.status()["ready"], ["discovery", "style"])
        with self.assertRaises(StateError): self.run.claim("voice", "worker")
        claim = self.run.claim("discovery", "worker")
        self.assertTrue(self.run.submit("discovery", claim["token"], discovery(self.run))["accepted"])
        self.assertEqual(self.run.status()["ready"], ["style", "research", "viability"])

    def test_concurrent_claims_have_only_one_owner(self):
        def attempt(name):
            try: return self.run.claim("discovery", name)
            except StateError: return None
        with ThreadPoolExecutor(max_workers=4) as pool:
            claims = list(pool.map(attempt, ["a", "b", "c", "d"]))
        self.assertEqual(sum(c is not None for c in claims), 1)
        self.assertEqual(self.run.status()["tasks"][0]["attempts"], 1)

    def test_stale_lease_cannot_submit_after_expiry_and_resume(self):
        old = self.run.claim("discovery", "old")
        with self.run.transaction() as c:
            c.execute("UPDATE tasks SET lease_until=? WHERE id='discovery'", (time.time()-1,))
        self.assertEqual(self.run.resume(), ["discovery"])
        new = self.run.claim("discovery", "new")
        with self.assertRaises(StateError): self.run.submit("discovery", old["token"], discovery(self.run))
        self.assertTrue(self.run.submit("discovery", new["token"], discovery(self.run))["accepted"])

    def test_resume_preserves_a_live_worker(self):
        self.run.claim("discovery", "live")
        self.assertEqual(self.run.resume(), [])
        self.assertEqual(self.run.status()["tasks"][0]["status"], "running")

    def test_invalid_claim_and_missing_file_block_downstream(self):
        c = self.run.claim("discovery", "worker")
        r = discovery(self.run); r["files"] = ["missing.txt"]
        result = self.run.submit("discovery", c["token"], r)
        self.assertFalse(result["accepted"])
        self.assertEqual(self.run.status()["ready"], ["style"])
        self.assertIn("missing", " ".join(result["errors"]))

    def test_completed_artifact_edit_is_detected(self):
        c = self.run.claim("discovery", "worker")
        file = Path(c["workspace"]) / "research.txt"; file.write_text("original")
        r = discovery(self.run); r["files"] = [str(file.relative_to(self.run.path))]
        self.assertTrue(self.run.submit("discovery", c["token"], r)["accepted"])
        file.write_text("changed")
        with self.assertRaisesRegex(StateError, "artifact changed"):
            self.run.claim("research", "next")

    def test_parent_invalidation_revokes_descendant_lease(self):
        c = self.run.claim("discovery", "worker")
        self.run.submit("discovery", c["token"], discovery(self.run))
        downstream = self.run.claim("research", "researcher")
        affected = self.run.invalidate("discovery", "Different story")
        self.assertIn("package", affected); self.assertNotIn("style", affected)
        with self.assertRaises(StateError): self.run.fail("research", downstream["token"], "old worker")
        self.assertEqual(self.run.status()["tasks"][0]["attempts"], 1)

    def test_retry_budget_is_not_reset_by_invalidation(self):
        for i in range(3):
            c = self.run.claim("discovery", "worker")
            self.run.fail("discovery", c["token"], "failed test attempt")
            if i < 2: self.run.retry("discovery")
        with self.assertRaisesRegex(StateError, "budget exhausted"): self.run.retry("discovery")
        self.run.invalidate("discovery", "Still respects lifetime budget")
        with self.assertRaisesRegex(StateError, "budget exhausted"): self.run.claim("discovery", "worker")

    def test_worker_invocation_cap_is_transactional(self):
        b = copy.deepcopy(self.brief); b["budget"]["max_model_calls"] = 1
        self.run.amend(b)
        self.run.claim("discovery", "model", model_call=True)
        with self.assertRaisesRegex(StateError, "invocation budget"):
            self.run.claim("style", "model", model_call=True)
        self.assertEqual(self.run.status()["worker_calls"], 1)

    def test_brief_edit_cannot_silently_reuse_stale_work(self):
        b = read_json(self.run.path / "brief.json"); b["niche"] = "changed"
        write_json(self.run.path / "brief.json", b)
        with self.assertRaisesRegex(StateError, "brief.json changed"): self.run.claim("discovery", "worker")
        self.run.amend(b)
        self.assertIsNotNone(self.run.claim("discovery", "worker"))

    def test_paths_reject_traversal_absolute_and_symlink_escape(self):
        outside = self.root / "outside.txt"; outside.write_text("secret fixture")
        for p in ("../outside.txt", str(outside)):
            with self.assertRaises(ValueError): safe_path(self.run.path, p)
        (self.run.path / "escape.txt").symlink_to(outside)
        with self.assertRaises(ValueError): safe_path(self.run.path, "escape.txt")

    def test_demo_is_honest_and_does_not_spend_or_deliver(self):
        run = create_demo(self.root)
        s = run.status()
        self.assertTrue(s["demo"]); self.assertFalse(s["delivered"])
        self.assertEqual(s["worker_calls"], 0)
        self.assertEqual(s["counts"]["complete"], 7)
        self.assertEqual(s["counts"]["blocked"], 1)
        self.assertEqual(s["media_jobs"], [])

    def test_real_run_rejects_fixture_output(self):
        c = self.run.claim("discovery", "worker"); r = discovery(self.run)
        r["data"]["fixture"] = True
        self.assertFalse(self.run.submit("discovery", c["token"], r)["accepted"])

    def test_bad_types_become_validation_errors_not_success(self):
        c = self.run.claim("discovery", "worker"); r = discovery(self.run)
        r["data"]["candidates"][0]["id"] = ["bad type"]
        result = self.run.submit("discovery", c["token"], r)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["status"], "blocked")

    def test_invalid_brief_requires_actual_inputs(self):
        for key in ("niche", "format", "duration_seconds", "references", "budget"):
            b = copy.deepcopy(self.brief); b[key] = None
            with self.assertRaises(ValidationError): validate_brief(b)
        b = copy.deepcopy(self.brief); b["hook"]["mode"] = "fixed"
        with self.assertRaises(ValidationError): validate_brief(b)

    def test_fiction_cannot_pass_as_documentary_research(self):
        r = envelope(self.run, "research", {"claims": [{"id": "c1", "text": "Invented event", "status": "fictional", "source_ids": []}]})
        e = validate_task("research", r, self.brief, {}, self.run.path)
        self.assertTrue(any("fictional" in x.lower() for x in e))


class MediaBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        # A synthetic state fixture tests ledger mechanics without running models.
        # It is never delivered or claimed to be a real preproduction review.
        self.run = create_demo(self.root)
        with self.run.transaction() as c:
            c.execute("UPDATE meta SET value='false' WHERE key='demo'")
            brief = self.run._meta(c, "brief")
            brief["budget"].update(max_media_jobs=2, max_media_cost_usd=2, max_media_credits=100)
            write_json(self.run.path / "brief.json", brief)
            from storyforge.util import digest
            c.execute("UPDATE meta SET value=? WHERE key='brief'", (canonical(brief),))
            c.execute("UPDATE meta SET value=? WHERE key='brief_hash'", (canonical(digest(brief)),))
            c.execute("UPDATE tasks SET status='complete' WHERE id='preflight'")
        self.claim = self.run.claim("voice", "test")

    def tearDown(self): self.tmp.cleanup()

    def reserve(self, key="voice-001", usd=1, credits=40, request=None):
        return self.run.reserve_media("voice", self.claim["token"], job_key=key, provider="test-provider",
                                     request=request or {"text": "fixture"}, estimated_usd=usd, estimated_credits=credits)

    def test_reservation_idempotency_and_request_mismatch(self):
        self.assertTrue(self.reserve()["may_generate"])
        self.assertFalse(self.reserve()["may_generate"])
        with self.assertRaisesRegex(StateError, "different request"):
            self.reserve(request={"text": "different"})
        self.assertEqual(len(self.run.status()["media_jobs"]), 1)

    def test_atomic_reservations_prevent_budget_overcommit(self):
        def go(key):
            try: return self.reserve(key=key, usd=1.5, credits=60)
            except StateError: return None
        with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(go, ["job-one", "job-two"]))
        self.assertEqual(sum(x is not None for x in results), 1)

    def test_timeout_retains_reservation_without_invented_provider_id(self):
        self.reserve()
        self.run.record_media("voice-001", status="uncertain")
        result = self.reserve()
        self.assertFalse(result["may_generate"])
        self.assertIsNone(result["provider_job_id"])
        with self.assertRaises(StateError): self.reserve(key="voice-002", usd=1.5)

    def test_resumed_worker_packet_contains_only_its_existing_media_jobs(self):
        from storyforge.prompts import write_task_packet
        self.reserve()
        response = self.run.path / "media" / "voice-response.txt"
        response.write_text("Synthetic saved response for recovery", encoding="utf-8")
        self.run.record_media("voice-001", status="uncertain", provider_job_id="provider-request-existing",
                              files=["media/voice-response.txt"])
        sound = self.run.claim("sound", "sound-fixture")
        self.run.reserve_media("sound", sound["token"], job_key="sound-other-task", provider="test-provider",
                               request={"effect": "fixture"}, estimated_usd=0.5, estimated_credits=20)
        self.run.fail("voice", self.claim["token"], "Synthetic interruption")
        self.run.retry("voice")
        resumed = self.run.claim("voice", "resumed-fixture")

        context = self.run.context("voice")
        self.assertEqual(len(context["media_jobs"]), 1)
        job = context["media_jobs"][0]
        self.assertEqual(job["job_key"], "voice-001")
        self.assertEqual(job["status"], "uncertain")
        self.assertEqual(job["provider_job_id"], "provider-request-existing")
        self.assertEqual(job["files"], ["media/voice-response.txt"])
        self.assertIsNone(job["actual_usd"])
        self.assertTrue(job["request_hash"])
        packet = write_task_packet(self.run, "voice", Path(resumed["workspace"]))
        prompt = Path(packet["prompt_path"]).read_text(encoding="utf-8")
        self.assertIn("provider-request-existing", prompt)
        self.assertIn("media/voice-response.txt", prompt)
        self.assertNotIn("sound-other-task", prompt)
        self.assertNotIn(resumed["token"], prompt)
        self.assertEqual(self.run.context("discovery")["media_jobs"], [])

    def test_completion_needs_real_output_and_provider_id(self):
        self.reserve()
        with self.assertRaises(StateError): self.run.record_media("voice-001", status="complete", files=[])
        with self.assertRaises(StateError): self.run.record_media("voice-001", status="complete", provider_job_id="test-request-1", files=[])
        file = self.run.path / "media" / "fixture.txt"; file.write_text("test output")
        self.run.record_media("voice-001", status="complete", provider_job_id="test-request-1", files=["media/fixture.txt"])
        with self.assertRaises(StateError): self.run.record_media("voice-001", status="submitted", provider_job_id="test-request-1")

    def test_unknown_cost_is_not_accepted_as_zero(self):
        with self.assertRaises(StateError): self.reserve(usd=float("nan"))
        with self.assertRaises(StateError): self.reserve(credits=-1)


if __name__ == "__main__": unittest.main()
