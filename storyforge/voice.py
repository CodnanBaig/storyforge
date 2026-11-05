"""Opt-in ElevenLabs narration with durable, non-retrying media bookkeeping.

Official contract checked 2026-11-06:
https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps

This helper makes one synchronous request for the accepted script. Long-form
chunking, voice casting and commercial-rights review remain production tasks.
No provider request is made merely by importing this module or running tests.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .media import probe_media
from .store import Run, StateError
from .util import now, safe_path, write_json


_API_ROOT = "https://api.elevenlabs.io/v1/text-to-speech"
_OUTPUT_FORMAT = "mp3_44100_128"
_MAX_RESPONSE_BYTES = 64 * 1024 * 1024
_FILES = (
    "request.json", "response-headers.json", "response.json", "narration.mp3",
    "probe.json", "alignment.json", "words.json",
)


class VoiceError(StateError):
    """An invalid invocation or an unsafe recovery request; never includes keys."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # API credentials must never follow a redirect to another origin.
        return None


def _open_request(request: Request, timeout_seconds: int):
    return build_opener(_NoRedirect()).open(request, timeout=timeout_seconds)


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def alignment_to_words(alignment: dict[str, Any]) -> list[dict[str, Any]]:
    """Group provider character timings into whitespace-delimited words.

    No timing is estimated or stretched. Preserve the original alignment for
    languages that need a language-specific caption tokenizer.
    """
    if not isinstance(alignment, dict):
        raise VoiceError("The provider supplied no usable character alignment.")
    characters = alignment.get("characters")
    starts = alignment.get("character_start_times_seconds")
    ends = alignment.get("character_end_times_seconds")
    if not all(isinstance(value, list) for value in (characters, starts, ends)):
        raise VoiceError("Character alignment must contain three arrays.")
    if not characters or len(characters) != len(starts) or len(characters) != len(ends):
        raise VoiceError("Character alignment arrays have different lengths or are empty.")
    words: list[dict[str, Any]] = []
    pending: list[str] = []
    word_start = 0.0
    word_end = 0.0
    previous_start = 0.0

    def flush() -> None:
        nonlocal pending
        if not pending:
            return
        if word_end <= word_start:
            raise VoiceError("A caption token has no positive provider-measured duration.")
        if words and word_start < words[-1]["end"] - 0.01:
            raise VoiceError("Provider word timings overlap; preserve and realign the existing audio.")
        words.append({"text": "".join(pending), "start": word_start, "end": word_end})
        pending = []

    for character, start, end in zip(characters, starts, ends):
        if not isinstance(character, str) or len(character) != 1:
            raise VoiceError("Alignment entries must be individual Unicode characters.")
        if not _finite(start) or not _finite(end) or start < 0 or end < start:
            raise VoiceError("Character alignment contains invalid times.")
        if start < previous_start - 0.001:
            raise VoiceError("Character alignment runs backwards.")
        previous_start = start
        if character.isspace():
            flush()
            continue
        if not pending:
            word_start = float(start)
            word_end = float(end)
        pending.append(character)
        word_end = max(word_end, float(end))
    flush()
    if not words:
        raise VoiceError("Character alignment contains no spoken words.")
    return words


def _context(run: Run, token: str) -> dict:
    context = run.context("voice")
    Run._check_lease(context["task"], token)
    if context.get("demo"):
        raise VoiceError("Offline fixtures cannot generate narration.")
    if context["brief"].get("voice", {}).get("provider", "").lower() != "elevenlabs":
        raise VoiceError("The approved brief must select ElevenLabs before this adapter is used.")
    script = context.get("dependencies", {}).get("script", {}).get("data", {}).get("narration")
    if not isinstance(script, str) or not script.strip():
        raise VoiceError("An accepted, nonempty script is required for narration.")
    return context


def _job_directory(run: Run, job_key: str) -> Path:
    if not isinstance(job_key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{3,100}", job_key):
        raise VoiceError("job_key must contain 3–100 letters, numbers, underscores or hyphens.")
    return safe_path(run.path, f"media/voice-{job_key}", must_exist=False)


def _existing_files(run: Run, directory: Path | None) -> list[str]:
    if directory is None:
        return []
    return [str((directory / name).relative_to(run.path)) for name in _FILES
            if (directory / name).is_file() and (directory / name).stat().st_size]


def _draft(context: dict, data: dict, files: list[str], *, blockers: list[str] | None = None,
           warnings: list[str] | None = None) -> dict:
    blockers = blockers or []
    return {
        "schema_version": "1.0", "run_id": context["run_id"], "task_id": "voice",
        "status": "blocked" if blockers else "complete",
        "summary": "Narration needs the listed recovery or review action." if blockers else
                   "ElevenLabs audio saved, measured and paired with provider-aligned caption words.",
        "data": data, "files": files, "sources": [],
        "warnings": warnings or [], "blockers": blockers,
    }


def _persist_draft(directory: Path, result: dict) -> dict:
    write_json(directory / "voice-result.json", result)
    return result


def _record_uncertain(run: Run, job_key: str, metadata: dict, directory: Path) -> None:
    """A later local processing failure cannot revoke an already saved take."""
    jobs = {job["job_key"]: job for job in run.status()["media_jobs"]}
    if jobs.get(job_key, {}).get("status") == "complete":
        return
    run.record_media(job_key, status="uncertain", provider_job_id=metadata.get("provider_job_id"),
                     files=_existing_files(run, directory))


def _write_once(path: Path, content: bytes) -> None:
    if path.exists():
        if not path.is_file() or path.read_bytes() != content:
            raise VoiceError("Saved provider media differs from the recovered response; preserve both and inspect it.")
        return
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _response_metadata(response: Any) -> dict:
    headers = response.headers
    provider_id = headers.get("request-id") or headers.get("x-request-id")
    if not isinstance(provider_id, str) or not provider_id.strip():
        provider_id = None
    return {
        "received_at": now(), "http_status": getattr(response, "status", None) or getattr(response, "code", None),
        "provider_job_id": provider_id,
        "request_id_header": "request-id" if headers.get("request-id") else
                             "x-request-id" if headers.get("x-request-id") else None,
        "reported_character_count": headers.get("x-character-count"),
        "reported_character_cost": headers.get("character-cost"),
        "content_type": headers.get("content-type"),
        "accounting_note": "Headers are preserved as reported. Character count is not assumed to equal billed credits.",
    }


def _capture_response(run: Run, job_key: str, directory: Path, response: Any) -> dict:
    metadata = _response_metadata(response)
    # Record the genuine request ID before reading a possibly interrupted body.
    write_json(directory / "response-headers.json", metadata)
    run.record_media(job_key, status="submitted" if metadata["provider_job_id"] else "uncertain",
                     provider_job_id=metadata["provider_job_id"], files=_existing_files(run, directory))
    total = 0
    with (directory / "response.json").open("xb") as stream:
        try:
            while True:
                try:
                    chunk = response.read(min(64 * 1024, _MAX_RESPONSE_BYTES - total + 1))
                except http.client.IncompleteRead as exc:
                    if exc.partial:
                        stream.write(exc.partial[:max(0, _MAX_RESPONSE_BYTES - total)])
                    raise
                if not chunk:
                    break
                total += len(chunk)
                if total > _MAX_RESPONSE_BYTES:
                    raise VoiceError("Provider response exceeds the local 64 MiB limit; preserve the request for recovery.")
                stream.write(chunk)
        finally:
            stream.flush()
            os.fsync(stream.fileno())
    return metadata


def _finish_saved(run: Run, context: dict, job_key: str, directory: Path, request: dict,
                  metadata: dict) -> dict:
    data = {
        "provider": "elevenlabs", "voice_id": request["voice_id"],
        "model_id": request["body"]["model_id"], "job_key": job_key,
        "provider_job_id": metadata.get("provider_job_id"),
        "script_sha256": hashlib.sha256(request["body"]["text"].encode("utf-8")).hexdigest(),
        "request_path": str((directory / "request.json").relative_to(run.path)),
        "timing_source": "provider_alignment", "requires_listening_review": True,
    }
    warnings = [
        "Listen to the saved take for omissions, pronunciation and performance before final QA.",
        "Commercial-use permission remains the preflight and release review's responsibility.",
    ]
    audio_valid = False
    try:
        raw = (directory / "response.json").read_bytes()
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise VoiceError("Saved provider response exceeds the local 64 MiB limit.")
        response = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
        if not isinstance(response, dict) or not isinstance(response.get("audio_base64"), str):
            raise VoiceError("The provider response contains no audio_base64 value.")
        audio_bytes = base64.b64decode(response["audio_base64"], validate=True)
        if not audio_bytes:
            raise VoiceError("The provider returned empty audio.")
        audio_path = directory / "narration.mp3"
        _write_once(audio_path, audio_bytes)  # Preserve the exact take before timing/QA parsing.
        data["audio_path"] = str(audio_path.relative_to(run.path))
        probe = probe_media(audio_path)
        write_json(directory / "probe.json", probe)
        if not any(stream.get("codec_type") == "audio" for stream in probe.get("streams", [])):
            raise VoiceError("The saved narration has no decodable audio stream.")
        duration = float(probe.get("format", {}).get("duration", "nan"))
        if not math.isfinite(duration) or duration <= 0:
            raise VoiceError("The narration duration could not be measured.")
        data["duration_seconds"] = duration
        data["probe_path"] = str((directory / "probe.json").relative_to(run.path))
        audio_valid = True
        # A usable audio take exists even if caption processing later needs repair.
        run.record_media(job_key, status="complete" if metadata.get("provider_job_id") else "uncertain",
                         provider_job_id=metadata.get("provider_job_id"), files=_existing_files(run, directory))
        alignment = response.get("normalized_alignment")
        if alignment is None:
            alignment = response.get("alignment")
            warnings.append("Only original-text alignment was supplied; inspect spoken normalization carefully.")
        if not isinstance(alignment, dict):
            raise VoiceError("No character alignment was returned. Align the existing audio without regenerating it.")
        write_json(directory / "alignment.json", alignment)
        original_alignment = response.get("alignment")
        if isinstance(original_alignment, dict) and isinstance(original_alignment.get("characters"), list):
            original_text = "".join(original_alignment["characters"])
            if " ".join(original_text.split()) != " ".join(request["body"]["text"].split()):
                raise VoiceError("Original-text alignment does not cover the approved script; inspect the saved take.")
        words = alignment_to_words(alignment)
        if words[-1]["end"] > duration + 0.1:
            raise VoiceError("Aligned words exceed the measured narration duration.")
        write_json(directory / "words.json", words)
        data["captions_path"] = str((directory / "words.json").relative_to(run.path))
        blockers = []
        hook = context["dependencies"]["script"]["data"].get("selected_hook", "").rstrip()
        hook_alignment = original_alignment if isinstance(original_alignment, dict) else alignment
        hook_characters = hook_alignment.get("characters", [])
        hook_ends = hook_alignment.get("character_end_times_seconds", [])
        if hook and "".join(hook_characters).startswith(hook) and len(hook_ends) >= len(hook) and _finite(hook_ends[len(hook)-1]):
            data["hook_end_seconds"] = float(hook_ends[len(hook)-1])
            if data["hook_end_seconds"] > context["brief"]["hook"]["max_seconds"] + 0.05:
                blockers.append("The measured opening exceeds hook.max_seconds. Preserve any fixed prefix and revise/review the script or the agreed limit.")
        else:
            blockers.append("The hook boundary could not be matched to actual alignment. Measure it from the saved take; do not regenerate merely to retrieve timing.")
        if duration > context["brief"]["duration_seconds"] + 0.05:
            blockers.append("The measured narration exceeds the video duration. Revise the plan or script before another take; do not cut words.")
        if not metadata.get("provider_job_id"):
            blockers.append("The response omitted a provider request ID. Preserve this take and reconcile the request before accepting the voice task.")
        result = _draft(context, data, _existing_files(run, directory), blockers=blockers, warnings=warnings)
    except (ValueError, TypeError, KeyError, OSError, RuntimeError, binascii.Error, subprocess.SubprocessError) as exc:
        # Do not turn a valid paid take into a failed generation merely because
        # alignment or downstream analysis failed. Its reservation still blocks
        # accidental regeneration under the same idempotency key.
        if not audio_valid:
            _record_uncertain(run, job_key, metadata, directory)
        message = str(exc) if isinstance(exc, VoiceError) else \
            "Saved response processing failed. Preserve its files and request ID, then recover or align the existing take."
        result = _draft(context, data, _existing_files(run, directory), blockers=[message], warnings=warnings)
    return _persist_draft(directory, result)


def synthesize(
    run: Run,
    token: str,
    *,
    voice_id: str,
    model_id: str = "eleven_multilingual_v2",
    job_key: str,
    estimated_usd: float,
    estimated_credits: float,
    api_key_env: str = "ELEVENLABS_API_KEY",
    timeout_seconds: int = 180,
    script_text: str | None = None,
) -> dict:
    """Reserve and submit one explicit synthesis request; return a draft artifact.

    This is an opt-in spending action. The caller must supply current estimates
    and an active voice-task lease after preflight. A reused key never submits a
    second request. API credentials are read only from ``api_key_env`` and are
    never stored. ``timeout_seconds`` is the HTTP/socket timeout; the external
    provider may continue processing after a local timeout.
    """
    context = _context(run, token)
    script = context["dependencies"]["script"]["data"]["narration"]
    if script_text is not None and script_text != script:
        raise VoiceError("script_text must equal the accepted narration; revise and reapprove changed scripts first.")
    if not isinstance(voice_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{3,256}", voice_id):
        raise VoiceError("Supply an explicit, valid voice ID from your ElevenLabs account.")
    if not isinstance(model_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{3,128}", model_id):
        raise VoiceError("Supply a valid model ID.")
    if not isinstance(api_key_env, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", api_key_env):
        raise VoiceError("api_key_env must be the name of one environment variable.")
    if not _finite(timeout_seconds) or timeout_seconds <= 0:
        raise VoiceError("timeout_seconds must be positive and finite.")
    if not all(_finite(value) and value >= 0 for value in (estimated_usd, estimated_credits)):
        raise VoiceError("Supply known, nonnegative media cost and credit estimates.")
    if estimated_usd == 0 and estimated_credits == 0:
        raise VoiceError("Nonempty speech synthesis needs a positive verified cost or credit estimate.")
    planned_voice = context["brief"]["voice"]
    if planned_voice.get("voice_id") and planned_voice["voice_id"] != voice_id:
        raise VoiceError("The voice ID differs from the approved brief.")
    if planned_voice.get("model_id") and planned_voice["model_id"] != model_id:
        raise VoiceError("The model ID differs from the approved brief.")
    data = {"provider": "elevenlabs", "voice_id": voice_id, "model_id": model_id, "job_key": job_key}
    key = os.environ.get(api_key_env, "").strip()
    if not key or "\n" in key or "\r" in key:
        return _draft(context, data, [], blockers=[f"Set a valid {api_key_env} in your local environment; no request was submitted."])
    if shutil.which("ffprobe") is None:
        return _draft(context, data, [], blockers=["Install FFmpeg/ffprobe before synthesis so the returned take can be measured; no request was submitted."])
    directory = _job_directory(run, job_key)
    body: dict[str, Any] = {"text": script, "model_id": model_id, "apply_text_normalization": "auto"}
    if model_id == "eleven_multilingual_v2":
        body["voice_settings"] = {
            "stability": 0.5, "similarity_boost": 0.75, "style": 0,
            "use_speaker_boost": True, "speed": 1.0,
        }
    request_record = {
        "provider": "elevenlabs", "voice_id": voice_id, "output_format": _OUTPUT_FORMAT,
        "endpoint": f"{_API_ROOT}/{quote(voice_id, safe='')}/with-timestamps?output_format={_OUTPUT_FORMAT}",
        "body": body,
    }
    reservation = run.reserve_media("voice", token, job_key=job_key, provider="elevenlabs", request=request_record,
                                    estimated_usd=estimated_usd, estimated_credits=estimated_credits)
    if reservation.get("reused") or not reservation.get("may_generate"):
        return _draft(context, data, _existing_files(run, directory), blockers=[
            "This media key already exists. No second generation was submitted. Recover its saved response or reconcile the provider request."
        ])
    try:
        directory.mkdir(parents=True, exist_ok=False)
        write_json(directory / "request.json", request_record)
    except OSError as exc:
        run.record_media(job_key, status="failed")
        raise VoiceError("Could not prepare a new durable media folder; no request was submitted.") from exc
    request = Request(request_record["endpoint"], data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                      headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "application/json"},
                      method="POST")
    try:
        with _open_request(request, timeout_seconds) as response:
            metadata = _capture_response(run, job_key, directory, response)
    except HTTPError as exc:
        try:
            metadata = _capture_response(run, job_key, directory, exc)
        except (OSError, ValueError, RuntimeError, http.client.HTTPException):
            metadata = _response_metadata(exc)
        finally:
            exc.close()
        uncertain = exc.code >= 500 or exc.code in {408, 429}
        run.record_media(job_key, status="uncertain" if uncertain else "failed",
                         provider_job_id=metadata.get("provider_job_id"), files=_existing_files(run, directory))
        data["provider_job_id"] = metadata.get("provider_job_id")
        return _persist_draft(directory, _draft(context, data, _existing_files(run, directory), blockers=[
            f"ElevenLabs returned HTTP {exc.code}. No automatic retry was made. Inspect the saved response and reconcile the reservation."
        ]))
    except (URLError, TimeoutError, socket.timeout, OSError, RuntimeError, http.client.HTTPException) as exc:
        metadata_path = directory / "response-headers.json"
        metadata = json.loads(metadata_path.read_text()) if metadata_path.is_file() else {}
        run.record_media(job_key, status="uncertain", provider_job_id=metadata.get("provider_job_id"),
                         files=_existing_files(run, directory))
        data["provider_job_id"] = metadata.get("provider_job_id")
        return _persist_draft(directory, _draft(context, data, _existing_files(run, directory), blockers=[
            "The synthesis request did not complete locally. Its charge or remote completion is uncertain; recover this request before generating again."
        ]))
    return _finish_saved(run, context, job_key, directory, request_record, metadata)


def recover_saved_response(run: Run, token: str, *, job_key: str) -> dict:
    """Reprocess saved bytes locally; never reads an API key or makes HTTP calls."""
    context = _context(run, token)
    directory = _job_directory(run, job_key)
    try:
        request = json.loads((directory / "request.json").read_text())
        metadata = json.loads((directory / "response-headers.json").read_text())
        if request["provider"] != "elevenlabs" or request["body"]["text"] != context["dependencies"]["script"]["data"]["narration"]:
            raise VoiceError("The saved request does not match the current approved narration.")
        # Never invent a job record or accept unrelated files as provider output.
        jobs = {job["job_key"]: job for job in run.status()["media_jobs"]}
        if job_key not in jobs or jobs[job_key]["provider"] != "elevenlabs":
            raise VoiceError("The saved response has no matching ElevenLabs reservation.")
        recorded_id = jobs[job_key].get("provider_job_id")
        if recorded_id and recorded_id != metadata.get("provider_job_id"):
            raise VoiceError("The saved request ID differs from the reservation.")
        planned_voice = context["brief"]["voice"]
        if planned_voice.get("voice_id") and planned_voice["voice_id"] != request["voice_id"]:
            raise VoiceError("The saved take uses a different voice from the current approved brief.")
        if planned_voice.get("model_id") and planned_voice["model_id"] != request["body"]["model_id"]:
            raise VoiceError("The saved take uses a different model from the current approved brief.")
        reservation = run.reserve_media(
            "voice", token, job_key=job_key, provider="elevenlabs", request=request,
            estimated_usd=jobs[job_key]["estimated_usd"], estimated_credits=jobs[job_key]["estimated_credits"],
        )
        if not reservation.get("reused"):
            raise VoiceError("Recovery requires a pre-existing matching media reservation.")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise VoiceError("Saved request metadata is incomplete; reconcile the provider request first.") from exc
    return _finish_saved(run, context, job_key, directory, request, metadata)
