"""Exercise real subprocess transport with local fake CLIs, without API calls."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from storyforge.adapters import (
    AdapterError, AdapterUnavailable, adapter_available, build_command, run_agent,
)


PAYLOAD = {
    "schema_version": "1.0", "run_id": "test-run", "task_id": "research",
    "status": "complete", "summary": "A test fixture, not factual research.",
    "data": {"fixture": True}, "files": [], "sources": [],
    "warnings": [], "blockers": [],
}

FAKE_CLI = r'''
import json
import os
from pathlib import Path
import subprocess
import sys
import time

provider = Path(sys.argv[0]).name
mode = os.environ.get("STORYFORGE_TEST_MODE", "success")
prompt = sys.stdin.read()
if os.environ.get("STORYFORGE_TEST_CAPTURE"):
    Path(os.environ["STORYFORGE_TEST_CAPTURE"]).write_text(json.dumps({
        "argv": sys.argv[1:], "cwd": os.getcwd(), "prompt": prompt
    }))
payload = json.loads(os.environ["STORYFORGE_TEST_PAYLOAD"])
wrapped = {"artifact_json": json.dumps(payload)}
if mode == "nonzero":
    print("Bearer fake-bearer-token", file=sys.stderr)
    print(os.environ.get("STORYFORGE_TEST_SECRET", ""), file=sys.stderr)
    sys.exit(7)
if mode == "timeout":
    print("partial", flush=True)
    time.sleep(60)
if mode == "child_timeout":
    child = subprocess.Popen([sys.executable, "-c",
        "import time; time.sleep(1.5); open('late-child-write.txt', 'w').write('bad')"])
    print(child.pid, file=sys.stderr, flush=True)
    time.sleep(60)
if mode == "empty":
    sys.exit(0)
if mode == "malformed":
    print("not JSON")
    sys.exit(0)
if mode == "bad_inner":
    wrapped["artifact_json"] = "{}"
if mode == "duplicate_inner":
    wrapped["artifact_json"] = '{"status":"complete","status":"blocked"}'
if mode == "nonfinite":
    wrapped["artifact_json"] = '{"amount":NaN}'
if mode == "list_inner":
    wrapped["artifact_json"] = "[]"
if mode == "redaction":
    print(os.environ["STORYFORGE_TEST_SECRET"], file=sys.stderr)

if provider == "codex":
    events = [
        {"type": "thread.started", "thread_id": "fixture-thread"},
        {"type": "turn.started"},
        {"type": "item.completed", "item": {
            "id": "fixture-item", "type": "agent_message", "text": json.dumps(wrapped)
        }},
        {"type": "turn.completed", "usage": {
            "input_tokens": 100, "cached_input_tokens": 20, "output_tokens": 50
        }},
    ]
    if mode == "partial":
        events.pop()
    if mode == "error":
        events.append({"type": "turn.failed", "error": {"message": "fixture failure"}})
    if mode == "no_message":
        events.pop(2)
    if mode == "restarted_partial":
        events.append({"type": "turn.started"})
    for event in events:
        print(json.dumps(event))
else:
    result = {
        "type": "result", "subtype": "success", "is_error": False,
        "structured_output": wrapped, "result": "", "num_turns": 2,
        "total_cost_usd": 0.0123,
        "usage": {"input_tokens": 120, "output_tokens": 60},
        "session_id": "fixture-session"
    }
    if mode == "error":
        result["is_error"] = True
        result["subtype"] = "error_max_turns"
    if mode == "partial":
        del result["structured_output"]
        result["result"] = json.dumps(wrapped)
    if mode == "invalid_cost":
        result["total_cost_usd"] = "unknown"
    print(json.dumps(result))
'''


class AdapterCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="storyforge adapters ")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.schema = self.workspace / "artifact schema.json"
        self.schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")

    def test_codex_arguments_preserve_spaces_and_do_not_bypass(self) -> None:
        command = build_command("codex", self.workspace, self.schema, model="literal; $(nothing)")
        self.assertIn(str(self.workspace), command)
        self.assertIn(str(self.schema), command)
        self.assertEqual(command[-1], "-")
        self.assertIn("literal; $(nothing)", command)
        self.assertIn("workspace-write", command)
        self.assertIn("agents.enabled=false", command)
        for bad in ("--yolo", "--dangerously-bypass-approvals-and-sandbox", "--ignore-rules"):
            self.assertNotIn(bad, command)

    def test_claude_turn_limit_is_real_and_permissions_are_not_overridden(self) -> None:
        command = build_command("claude", self.workspace, self.schema, max_turns=7)
        self.assertEqual(command[command.index("--max-turns") + 1], "7")
        self.assertEqual(json.loads(command[command.index("--json-schema") + 1]), {"type": "object"})
        self.assertIn("Agent", command)
        self.assertIn("Task", command)
        for bad in ("--dangerously-skip-permissions", "--allowedTools", "--permission-mode", "--bare"):
            self.assertNotIn(bad, command)

    def test_unknown_provider_is_rejected(self) -> None:
        with self.assertRaises(AdapterError):
            build_command("shell", self.workspace, self.schema)
        with self.assertRaises(AdapterError):
            adapter_available("shell")

    def test_invalid_inputs_are_rejected_before_process_launch(self) -> None:
        for count in (0, -1, True, 1.5):
            with self.subTest(count=count), self.assertRaises(AdapterError):
                build_command("codex", self.workspace, self.schema, max_turns=count)
        with self.assertRaises(AdapterError):
            build_command("codex", self.workspace / "missing", self.schema)
        self.schema.write_text("not json", encoding="utf-8")
        with self.assertRaises(AdapterError):
            build_command("claude", self.workspace, self.schema)


@unittest.skipUnless(os.name == "posix", "The fake executable harness targets macOS/Linux.")
class AdapterProcessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="storyforge process ")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.bin = self.workspace / "fake bin"
        self.bin.mkdir()
        for provider in ("codex", "claude"):
            executable = self.bin / provider
            executable.write_text(f"#!{sys.executable}\n" + FAKE_CLI, encoding="utf-8")
            executable.chmod(0o700)
        self.schema = self.workspace / "artifact schema.json"
        self.schema.write_text(json.dumps({
            "type": "object", "properties": {"data": {"type": "object"}}
        }), encoding="utf-8")
        self.capture = self.workspace / "captured.json"
        self.environment = patch.dict(os.environ, {
            "PATH": str(self.bin) + os.pathsep + os.environ.get("PATH", ""),
            "STORYFORGE_TEST_MODE": "success",
            "STORYFORGE_TEST_PAYLOAD": json.dumps(PAYLOAD),
            "STORYFORGE_TEST_CAPTURE": str(self.capture),
            "STORYFORGE_TEST_SECRET": "fixture-secret-never-display",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def invoke(self, provider: str = "codex", mode: str = "success", **kwargs):
        with patch.dict(os.environ, {"STORYFORGE_TEST_MODE": mode}):
            return run_agent(provider, "Task with spaces; $(do-not-execute).", self.workspace, self.schema, **kwargs)

    def test_codex_success_uses_stdin_and_records_unknown_cost(self) -> None:
        self.assertTrue(adapter_available("codex"))
        result = self.invoke()
        self.assertEqual(result.payload, PAYLOAD)
        self.assertIsNone(result.usage["cost_usd"])
        self.assertEqual(result.usage["worker_invocations"], 1)
        self.assertEqual(result.usage["reported_usage"]["input_tokens"], 100)
        captured = json.loads(self.capture.read_text())
        self.assertIn("Task with spaces; $(do-not-execute).", captured["prompt"])
        self.assertNotIn("Task with spaces; $(do-not-execute).", captured["argv"])
        self.assertEqual(Path(captured["cwd"]), self.workspace)
        self.assertEqual(list(self.workspace.glob(".storyforge-transport-*")), [])

    def test_claude_success_extracts_structured_output_and_cost_estimate(self) -> None:
        result = self.invoke("claude")
        self.assertEqual(result.payload, PAYLOAD)
        self.assertEqual(result.usage["cost_usd"], 0.0123)
        self.assertEqual(result.usage["cost_source"], "cli_estimate")
        self.assertEqual(result.usage["reported_turns"], 2)
        captured = json.loads(self.capture.read_text())
        native_schema = json.loads(captured["argv"][captured["argv"].index("--json-schema") + 1])
        self.assertEqual(set(native_schema["properties"]), {"artifact_json"})
        self.assertFalse(native_schema["additionalProperties"])

    def test_errors_and_partial_results_never_become_payloads(self) -> None:
        for provider in ("codex", "claude"):
            for mode in ("empty", "malformed", "partial", "error", "bad_inner", "duplicate_inner", "nonfinite", "list_inner"):
                with self.subTest(provider=provider, mode=mode), self.assertRaises(AdapterError):
                    self.invoke(provider, mode)

    def test_codex_missing_final_message_is_rejected(self) -> None:
        with self.assertRaises(AdapterError):
            self.invoke(mode="no_message")

    def test_codex_prior_success_does_not_complete_a_restarted_turn(self) -> None:
        with self.assertRaises(AdapterError):
            self.invoke(mode="restarted_partial")

    def test_nonzero_exit_does_not_expose_provider_output_in_exception(self) -> None:
        with self.assertRaises(AdapterError) as caught:
            self.invoke("claude", "nonzero")
        error = caught.exception
        self.assertEqual(error.returncode, 7)
        self.assertNotIn("fixture-secret", str(error))
        self.assertNotIn("fixture-secret", error.stderr)
        self.assertNotIn("fake-bearer-token", error.stderr)
        self.assertIn("[REDACTED]", error.stderr)

    def test_success_logs_are_also_redacted(self) -> None:
        result = self.invoke("codex", "redaction")
        self.assertNotIn("fixture-secret", result.stderr)
        self.assertIn("[REDACTED]", result.stderr)

    def test_unparseable_cost_remains_unknown(self) -> None:
        result = self.invoke("claude", "invalid_cost")
        self.assertIsNone(result.usage["cost_usd"])
        self.assertEqual(result.usage["cost_source"], "unknown")

    def test_missing_cli_raises_actionable_error_without_spawning(self) -> None:
        with patch("storyforge.adapters.shutil.which", return_value=None):
            with self.assertRaises(AdapterUnavailable):
                self.invoke()

    def test_timeout_returns_error_and_retains_partial_diagnostics(self) -> None:
        started = time.monotonic()
        with self.assertRaises(AdapterError) as caught:
            self.invoke(mode="timeout", timeout_seconds=0.2)
        self.assertTrue(caught.exception.timed_out)
        self.assertIn("partial", caught.exception.stdout)
        self.assertLess(time.monotonic() - started, 5)

    def test_timeout_stops_the_child_process_group(self) -> None:
        with self.assertRaises(AdapterError):
            self.invoke(mode="child_timeout", timeout_seconds=0.2)
        time.sleep(1.7)
        self.assertFalse((self.workspace / "late-child-write.txt").exists())

    def test_invalid_deadlines_never_invoke_cli(self) -> None:
        for deadline in (0, -1, True, float("nan"), float("inf")):
            with self.subTest(deadline=deadline), self.assertRaises(AdapterError):
                self.invoke(timeout_seconds=deadline)
        self.assertFalse(self.capture.exists())


if __name__ == "__main__":
    unittest.main()
