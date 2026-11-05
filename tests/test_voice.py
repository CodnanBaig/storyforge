"""No live HTTP or real API key is used by these voice-adapter tests."""

from __future__ import annotations

import base64
from email.message import Message
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from storyforge.store import StateError
from storyforge.voice import VoiceError, alignment_to_words, recover_saved_response, synthesize


SCRIPT = "Hello world."
TOKEN = "test-lease-token"
VOICE_ID = "test_voice_id"
KEY_ENV = "STORYFORGE_TEST_ELEVEN_KEY"


def alignment(text: str = SCRIPT) -> dict:
    return {
        "characters": list(text),
        "character_start_times_seconds": [i / 10 for i in range(len(text))],
        "character_end_times_seconds": [(i + 1) / 10 for i in range(len(text))],
    }


def provider_response(**changes) -> bytes:
    response = {
        "audio_base64": base64.b64encode(b"FAKE AUDIO FOR TRANSPORT TEST ONLY").decode(),
        "alignment": alignment(), "normalized_alignment": alignment(),
    }
    response.update(changes)
    return json.dumps(response).encode()


class FakeResponse:
    def __init__(self, body: bytes, *, request_id: str | None = "provider-request-123", fail_after_first=False):
        self.body = io.BytesIO(body)
        self.headers = Message()
        if request_id:
            self.headers["request-id"] = request_id
        self.headers["x-character-count"] = str(len(SCRIPT))
        self.headers["content-type"] = "application/json"
        self.status = 200
        self.fail_after_first = fail_after_first
        self.read_count = 0
        self.before_read = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.body.close()

    def read(self, amount):
        if self.before_read:
            self.before_read()
        self.read_count += 1
        if self.fail_after_first and self.read_count > 1:
            raise TimeoutError("simulated socket interruption")
        return self.body.read(min(amount, 20) if self.fail_after_first else amount)


class FakeRun:
    """In-memory media ledger; store transactions/idempotency have separate tests."""
    def __init__(self, path: Path):
        self.path = path
        (path / "media").mkdir()
        self.jobs = {}
        self.records = []
        self.reserve_count = 0
        self.ctx = {
            "run_id": "voice-test", "demo": False,
            "task": {"status": "running", "token": TOKEN, "lease_until": time.time() + 600},
            "brief": {"voice": {"provider": "elevenlabs", "voice_id": VOICE_ID, "model_id": ""},
                      "duration_seconds": 5, "hook": {"max_seconds": 3}, "release": {"intent": "private_preview"}},
            "dependencies": {"script": {"data": {"narration": SCRIPT, "selected_hook": SCRIPT}}},
        }

    def context(self, task_id):
        assert task_id == "voice"
        return self.ctx

    def reserve_media(self, task_id, token, *, job_key, provider, request, estimated_usd, estimated_credits):
        assert task_id == "voice" and token == TOKEN
        self.reserve_count += 1
        if job_key in self.jobs:
            if self.jobs[job_key]["request"] != request:
                raise StateError("Idempotency key reused for a different request")
            return {**self.jobs[job_key], "reused": True, "may_generate": False}
        self.jobs[job_key] = {
            "job_key": job_key, "provider": provider, "request": request,
            "estimated_usd": estimated_usd, "estimated_credits": estimated_credits,
            "status": "reserved", "provider_job_id": None,
            "actual_usd": None, "actual_credits": None,
        }
        return {"reused": False, "may_generate": True}

    def record_media(self, job_key, **values):
        if values["status"] in {"submitted", "complete"} and not values.get("provider_job_id"):
            raise StateError("Real provider ID required")
        if self.jobs[job_key]["status"] == "complete" and values["status"] != "complete":
            raise StateError("Cannot downgrade complete media")
        self.records.append(values.copy())
        self.jobs[job_key].update(values)
        return values

    def status(self):
        return {"media_jobs": list(self.jobs.values())}


class AlignmentTests(unittest.TestCase):
    def test_words_retain_punctuation_and_actual_time_boundaries(self):
        words = alignment_to_words(alignment("One, two."))
        self.assertEqual([w["text"] for w in words], ["One,", "two."])
        self.assertEqual(words[0], {"text": "One,", "start": 0.0, "end": 0.4})
        self.assertEqual(words[1]["start"], 0.5)
        self.assertEqual(words[1]["end"], 0.9)

    def test_unicode_and_multiple_whitespace(self):
        words = alignment_to_words(alignment("  café\n  नमस्ते  "))
        self.assertEqual([word["text"] for word in words], ["café", "नमस्ते"])

    def test_bad_alignment_is_rejected_without_estimated_timings(self):
        bad = [None, {}, alignment("")]
        mismatch = alignment()
        mismatch["character_end_times_seconds"].pop()
        bad.append(mismatch)
        reverse = alignment()
        reverse["character_start_times_seconds"][4] = 0
        bad.append(reverse)
        nonfinite = alignment()
        nonfinite["character_end_times_seconds"][1] = float("nan")
        bad.append(nonfinite)
        for value in bad:
            with self.subTest(value=value), self.assertRaises(VoiceError):
                alignment_to_words(value)


class VoiceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="storyforge voice ")
        self.addCleanup(self.temp.cleanup)
        self.run = FakeRun(Path(self.temp.name))
        self.env = patch.dict(os.environ, {KEY_ENV: "fixture-key-never-written"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.which = patch("storyforge.voice.shutil.which", return_value="/fake/ffprobe")
        self.which.start()
        self.addCleanup(self.which.stop)
        self.probe = patch("storyforge.voice.probe_media", return_value={
            "streams": [{"codec_type": "audio"}], "format": {"duration": "2.0"}
        })
        self.probe_mock = self.probe.start()
        self.addCleanup(self.probe.stop)

    def generate(self, **kwargs):
        values = {"voice_id": VOICE_ID, "job_key": "take_001", "estimated_usd": 0.05,
                  "estimated_credits": 100, "api_key_env": KEY_ENV}
        values.update(kwargs)
        return synthesize(self.run, TOKEN, **values)

    @property
    def directory(self):
        return self.run.path / "media" / "voice-take_001"

    def test_success_persists_raw_take_and_alignment_without_secrets(self):
        body = provider_response()
        response = FakeResponse(body)
        def confirm_headers_are_recorded_first():
            self.assertEqual(self.run.jobs["take_001"]["provider_job_id"], "provider-request-123")
        response.before_read = confirm_headers_are_recorded_first
        with patch("storyforge.voice._open_request", return_value=response) as http:
            result = self.generate()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["data"]["duration_seconds"], 2.0)
        self.assertEqual(result["data"]["timing_source"], "provider_alignment")
        self.assertEqual((self.directory / "response.json").read_bytes(), body)
        self.assertEqual((self.directory / "narration.mp3").read_bytes(), b"FAKE AUDIO FOR TRANSPORT TEST ONLY")
        self.assertEqual([w["text"] for w in json.loads((self.directory / "words.json").read_text())], ["Hello", "world."])
        self.assertEqual(self.run.jobs["take_001"]["status"], "complete")
        self.assertIsNone(self.run.jobs["take_001"]["actual_credits"])
        self.assertIsNone(self.run.jobs["take_001"]["actual_usd"])
        request = http.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertTrue(request.full_url.startswith("https://api.elevenlabs.io/"))
        self.assertEqual(json.loads(request.data)["text"], SCRIPT)
        self.assertEqual(dict((key.lower(), value) for key, value in request.header_items())["xi-api-key"], "fixture-key-never-written")
        for path in self.directory.iterdir():
            if path.suffix == ".json":
                self.assertNotIn("fixture-key-never-written", path.read_text())

    def test_reused_reservation_never_generates_twice(self):
        with patch("storyforge.voice._open_request", return_value=FakeResponse(provider_response())) as http:
            self.generate()
            second = self.generate()
        self.assertEqual(http.call_count, 1)
        self.assertEqual(second["status"], "blocked")
        self.assertIn("already exists", second["blockers"][0])

    def test_missing_api_key_never_reserves_or_calls_http(self):
        with patch.dict(os.environ, {KEY_ENV: ""}), patch("storyforge.voice._open_request") as http:
            result = self.generate()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(self.run.reserve_count, 0)
        http.assert_not_called()

    def test_missing_ffprobe_is_detected_before_spending(self):
        with patch("storyforge.voice.shutil.which", return_value=None), patch("storyforge.voice._open_request") as http:
            result = self.generate()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(self.run.reserve_count, 0)
        http.assert_not_called()

    def test_timeout_before_headers_keeps_unknown_id_and_blocks_recreation(self):
        with patch("storyforge.voice._open_request", side_effect=TimeoutError()) as http:
            first = self.generate()
            second = self.generate()
        self.assertEqual(http.call_count, 1)
        self.assertEqual(first["status"], "blocked")
        self.assertEqual(second["status"], "blocked")
        self.assertEqual(self.run.jobs["take_001"]["status"], "uncertain")
        self.assertIsNone(self.run.jobs["take_001"]["provider_job_id"])
        self.assertTrue((self.directory / "request.json").is_file())

    def test_timeout_after_headers_preserves_id_and_partial_response(self):
        with patch("storyforge.voice._open_request", return_value=FakeResponse(provider_response(), fail_after_first=True)):
            result = self.generate()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(self.run.jobs["take_001"]["status"], "uncertain")
        self.assertEqual(self.run.jobs["take_001"]["provider_job_id"], "provider-request-123")
        self.assertGreater((self.directory / "response.json").stat().st_size, 0)

    def test_missing_request_id_preserves_audio_but_blocks_acceptance(self):
        with patch("storyforge.voice._open_request", return_value=FakeResponse(provider_response(), request_id=None)):
            result = self.generate()
        self.assertEqual(result["status"], "blocked")
        self.assertTrue((self.directory / "narration.mp3").is_file())
        self.assertIsNone(result["data"]["provider_job_id"])
        self.assertEqual(self.run.jobs["take_001"]["status"], "uncertain")

    def test_missing_alignment_keeps_completed_media_take(self):
        with patch("storyforge.voice._open_request", return_value=FakeResponse(provider_response(alignment=None, normalized_alignment=None))):
            result = self.generate()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(self.run.jobs["take_001"]["status"], "complete")
        self.assertTrue((self.directory / "narration.mp3").is_file())

    def test_http_failure_is_persisted_without_retry(self):
        headers = Message()
        headers["request-id"] = "real-error-request-id"
        error = HTTPError("https://api.elevenlabs.io/fixture", 401, "Unauthorized", headers, io.BytesIO(b'{"detail":"unauthorized"}'))
        with patch("storyforge.voice._open_request", side_effect=error) as http:
            result = self.generate()
        self.assertEqual(http.call_count, 1)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(self.run.jobs["take_001"]["status"], "failed")
        self.assertEqual(self.run.jobs["take_001"]["provider_job_id"], "real-error-request-id")
        self.assertEqual(json.loads((self.directory / "response.json").read_text()), {"detail": "unauthorized"})

    def test_invalid_base64_preserves_raw_response(self):
        body = provider_response(audio_base64="not base64!!!")
        with patch("storyforge.voice._open_request", return_value=FakeResponse(body)):
            result = self.generate()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual((self.directory / "response.json").read_bytes(), body)
        self.assertFalse((self.directory / "narration.mp3").exists())

    def test_too_long_audio_is_not_trimmed_or_regenerated(self):
        self.probe_mock.return_value["format"]["duration"] = "10"
        with patch("storyforge.voice._open_request", return_value=FakeResponse(provider_response())) as http:
            result = self.generate()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(http.call_count, 1)
        self.assertEqual(result["data"]["duration_seconds"], 10)
        self.assertEqual(self.run.jobs["take_001"]["status"], "complete")

    def test_saved_response_can_be_recovered_without_key_or_http(self):
        self.probe_mock.side_effect = RuntimeError("temporary decoder failure")
        with patch("storyforge.voice._open_request", return_value=FakeResponse(provider_response())):
            first = self.generate()
        self.assertEqual(first["status"], "blocked")
        self.probe_mock.side_effect = None
        with patch.dict(os.environ, {KEY_ENV: ""}), patch("storyforge.voice._open_request") as http:
            recovered = recover_saved_response(self.run, TOKEN, job_key="take_001")
        self.assertEqual(recovered["status"], "complete")
        http.assert_not_called()

    def test_recovery_preserves_completed_media_when_local_probe_fails(self):
        with patch("storyforge.voice._open_request", return_value=FakeResponse(provider_response())):
            self.generate()
        self.probe_mock.side_effect = RuntimeError("decoder temporarily unavailable")
        with patch("storyforge.voice._open_request") as http:
            recovered = recover_saved_response(self.run, TOKEN, job_key="take_001")
        self.assertEqual(recovered["status"], "blocked")
        self.assertEqual(self.run.jobs["take_001"]["status"], "complete")
        http.assert_not_called()

    def test_recovery_rejects_altered_request_metadata(self):
        with patch("storyforge.voice._open_request", return_value=FakeResponse(provider_response())):
            self.generate()
        request_path = self.directory / "request.json"
        altered = json.loads(request_path.read_text())
        altered["body"]["voice_settings"]["speed"] = 1.2
        request_path.write_text(json.dumps(altered))
        with patch("storyforge.voice._open_request") as http, self.assertRaises(StateError):
            recover_saved_response(self.run, TOKEN, job_key="take_001")
        http.assert_not_called()

    def test_script_voice_provider_and_cost_must_match_approved_request(self):
        with patch("storyforge.voice._open_request") as http:
            for kwargs in ({"script_text": "An unreviewed new script"}, {"voice_id": "different_voice"},
                           {"estimated_usd": 0, "estimated_credits": 0}, {"job_key": "../escape"}):
                with self.subTest(kwargs=kwargs), self.assertRaises(VoiceError):
                    self.generate(**kwargs)
            self.run.ctx["brief"]["voice"]["provider"] = "external"
            with self.assertRaises(VoiceError):
                self.generate()
        self.assertEqual(self.run.reserve_count, 0)
        http.assert_not_called()

    def test_budget_rejection_prevents_http(self):
        with patch.object(self.run, "reserve_media", side_effect=StateError("Media credit budget exceeded")), \
                patch("storyforge.voice._open_request") as http:
            with self.assertRaises(StateError):
                self.generate()
        http.assert_not_called()


if __name__ == "__main__":
    unittest.main()
