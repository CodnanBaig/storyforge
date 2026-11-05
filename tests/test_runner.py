import json
import os
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Timer
from unittest.mock import patch

from storyforge.adapters import AdapterError, AgentResult, run_agent
from storyforge.intake import make_brief
from storyforge.runner import run_pipeline
from storyforge.store import Run
from storyforge.util import ROOT, write_json


class RunnerTests(unittest.TestCase):
    def test_bounded_runner_accepts_a_real_contract_and_stops_at_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief = make_brief(); brief["budget"]["max_model_calls"] = 1
            run = Run.create(brief, Path(tmp))
            result = {"schema_version": "1.0", "run_id": run.status()["run_id"], "task_id": "discovery",
                      "status": "complete", "summary": "Synthetic transport integration fixture",
                      "data": {"candidates": [{"id": str(i), "title": "Fixture", "angle": "Synthetic", "source_urls": ["https://example.invalid/fixture"]} for i in range(3)], "selected_id": "0"},
                      "files": [], "sources": [], "warnings": [], "blockers": []}
            with patch("storyforge.adapters.adapter_available", return_value=True), patch("storyforge.adapters.run_agent", return_value=AgentResult(result, {"cost_usd": None}, "fixture", "")) as mocked:
                state = run_pipeline(run, "codex", until="discovery")
            self.assertEqual(mocked.call_count, 1)
            self.assertEqual(state["worker_calls"], 1)
            self.assertEqual(state["counts"]["complete"], 1)
            self.assertFalse(state["delivered"])
            self.assertEqual(len(list(run.path.glob("tasks/discovery/attempt-*/result.json"))), 1)

    def test_worker_failure_is_saved_and_does_not_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Run.create(make_brief(), Path(tmp))
            with patch("storyforge.adapters.adapter_available", return_value=True), patch("storyforge.adapters.run_agent", side_effect=AdapterError("Synthetic unavailable tool")) as mocked:
                state = run_pipeline(run, "codex", until="discovery")
            self.assertEqual(mocked.call_count, 1)
            self.assertEqual(state["counts"]["failed"], 1)

    @unittest.skipUnless(os.name == "posix", "POSIX process cancellation fixture")
    def test_cancel_event_terminates_a_live_local_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); binary = root / "codex"
            binary.write_text(f"#!{sys.executable}\nimport sys,time\nsys.stdin.read()\nprint('{{\"type\":\"turn.started\"}}', flush=True)\ntime.sleep(60)\n")
            binary.chmod(0o755)
            event = Event(); timer = Timer(0.2, event.set)
            before = time.monotonic()
            with patch.dict(os.environ, {"PATH": str(root)+os.pathsep+os.environ.get("PATH", "")}):
                timer.start()
                try:
                    with self.assertRaisesRegex(AdapterError, "cancelled locally"):
                        run_agent("codex", "Synthetic cancellation test", root, ROOT / "schemas/task-result.schema.json", timeout_seconds=20, cancel_event=event)
                finally: timer.cancel()
            self.assertLess(time.monotonic()-before, 8)


if __name__ == "__main__": unittest.main()
