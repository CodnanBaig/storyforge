from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import __version__
from .contracts import ValidationError, validate_brief
from .demo import create_demo
from .intake import interactive
from .media import captions_to_srt, validate_video
from .pipeline import TASKS
from .prompts import task_prompt, write_task_packet
from .store import Run, StateError
from .util import ROOT, read_json, write_json


def emit(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), flush=True)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="storyforge", description="Resumable multi-agent video production. Run from the project root.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("intake", help="Ask niche, duration, format, references, and preferences")
    a.add_argument("--output", type=Path, default=Path("brief.json"))
    a = sub.add_parser("init", help="Create a fresh saved run from a validated brief")
    a.add_argument("--brief", type=Path, required=True); a.add_argument("--runs-dir", type=Path, default=Path("runs"))
    a = sub.add_parser("validate-brief"); a.add_argument("file", type=Path)
    sub.add_parser("doctor", help="Inspect local prerequisites without reading credentials")
    a = sub.add_parser("demo", help="Exercise the offline workflow fixture; never generates media")
    a.add_argument("--runs-dir", type=Path, default=Path("runs"))
    for cmd in ("status", "next", "resume", "events"):
        a = sub.add_parser(cmd); a.add_argument("run_dir", type=Path)
    for cmd in ("task", "claim", "submit", "heartbeat", "retry", "invalidate", "reserve-media"):
        a = sub.add_parser(cmd); a.add_argument("run_dir", type=Path); a.add_argument("task_id", choices=list(TASKS))
        if cmd == "task": a.add_argument("--output", type=Path)
        if cmd == "claim":
            a.add_argument("--worker", required=True); a.add_argument("--lease-seconds", type=int, default=1200)
            a.add_argument("--model-call", action="store_true", help="Count this native worker dispatch against the invocation budget")
        if cmd in {"submit", "heartbeat", "reserve-media"}: a.add_argument("--token", required=True)
        if cmd == "submit": a.add_argument("--file", type=Path, required=True)
        if cmd == "heartbeat": a.add_argument("--lease-seconds", type=int, default=1200)
        if cmd == "invalidate": a.add_argument("--reason", required=True)
        if cmd == "reserve-media":
            a.add_argument("--key", required=True); a.add_argument("--provider", required=True)
            a.add_argument("--request", type=Path, required=True)
            a.add_argument("--usd", type=float, required=True); a.add_argument("--credits", type=float, required=True)
    a = sub.add_parser("record-media"); a.add_argument("run_dir", type=Path)
    a.add_argument("--key", required=True); a.add_argument("--provider-job-id")
    a.add_argument("--status", required=True, choices=["submitted", "complete", "failed", "uncertain"])
    a.add_argument("--usd", type=float); a.add_argument("--credits", type=float); a.add_argument("--file", action="append", default=[])
    a = sub.add_parser("amend"); a.add_argument("run_dir", type=Path); a.add_argument("--brief", type=Path, required=True)
    a = sub.add_parser("run", help="Launch bounded Codex or Claude CLI workers using existing authentication")
    a.add_argument("run_dir", type=Path); a.add_argument("--provider", choices=["codex", "claude"], required=True)
    a.add_argument("--workers", type=int, default=3); a.add_argument("--timeout-seconds", type=int, default=900)
    a.add_argument("--model"); a.add_argument("--max-turns", type=int, default=20); a.add_argument("--until", choices=list(TASKS))
    a = sub.add_parser("qa-media"); a.add_argument("video", type=Path); a.add_argument("--brief", type=Path, required=True)
    a.add_argument("--output", type=Path)
    a = sub.add_parser("srt"); a.add_argument("words", type=Path); a.add_argument("--output", type=Path, required=True)
    a = sub.add_parser("export-plan", help="Build a draft renderer manifest from a completed director plan")
    a.add_argument("run_dir", type=Path); a.add_argument("--output", type=Path, required=True)
    a = sub.add_parser("tts", help="Generate one approved ElevenLabs narration with a reserved budget")
    a.add_argument("run_dir", type=Path); a.add_argument("--token", required=True)
    a.add_argument("--voice-id", required=True); a.add_argument("--model-id", default="eleven_multilingual_v2")
    a.add_argument("--key", required=True); a.add_argument("--usd", type=float, required=True); a.add_argument("--credits", type=float, required=True)
    a.add_argument("--api-key-env", default="ELEVENLABS_API_KEY"); a.add_argument("--timeout-seconds", type=int, default=180)
    a = sub.add_parser("recover-voice", help="Reprocess saved narration response without another generation")
    a.add_argument("run_dir", type=Path); a.add_argument("--token", required=True); a.add_argument("--key", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        cmd = args.command
        if cmd == "doctor":
            from .adapters import adapter_available
            emit({"storyforge": __version__, "python": sys.version.split()[0], "python_ok": sys.version_info >= (3, 11),
                  "tools": {name: bool(shutil.which(name)) for name in ("node", "npm", "ffmpeg", "ffprobe")},
                  "adapters": {name: adapter_available(name) for name in ("codex", "claude")},
                  "renderer_installed": (ROOT / "renderer" / "node_modules" / "remotion").exists(),
                  "authentication": "Not inspected. Verify provider authentication in its own CLI.",
                  "note": "Native host mode works without subprocess CLIs. Renderer requires Node dependencies."})
        elif cmd == "intake":
            if args.output.exists(): raise StateError("Intake output already exists; choose a new path to preserve it")
            brief = validate_brief(interactive()); write_json(args.output, brief); emit({"brief": str(args.output.resolve())})
        elif cmd == "validate-brief": validate_brief(read_json(args.file)); emit({"valid": True})
        elif cmd == "init": emit(Run.create(read_json(args.brief), args.runs_dir).status())
        elif cmd == "demo": emit(create_demo(args.runs_dir).status())
        elif cmd == "qa-media":
            report = validate_video(args.video, validate_brief(read_json(args.brief)))
            if args.output: write_json(args.output, report)
            emit(report); return 0 if report["passed"] else 2
        elif cmd == "srt":
            words = read_json(args.words)
            if not isinstance(words, list) or not words: raise StateError("Provide a nonempty aligned word array")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(captions_to_srt(words), encoding="utf-8"); emit({"srt": str(args.output.resolve())})
        else:
            run = Run(args.run_dir)
            if cmd == "status": emit(run.status())
            elif cmd == "next": emit({"ready": run.status()["ready"]})
            elif cmd == "events": emit(run.events())
            elif cmd == "resume": emit({"recovered": run.resume(), "status": run.status()})
            elif cmd == "task":
                prompt = task_prompt(run, args.task_id)
                if args.output:
                    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(prompt, encoding="utf-8")
                    emit({"prompt": str(args.output.resolve())})
                else: print(prompt)
            elif cmd == "claim":
                claim = run.claim(args.task_id, args.worker, lease_seconds=args.lease_seconds, model_call=args.model_call)
                packet = write_task_packet(run, args.task_id, Path(claim["workspace"]))
                emit({**claim, **packet})
            elif cmd == "submit":
                result = run.submit(args.task_id, args.token, read_json(args.file)); emit(result)
                return 0 if result["accepted"] else 2
            elif cmd == "heartbeat": emit(run.heartbeat(args.task_id, args.token, args.lease_seconds))
            elif cmd == "retry": run.retry(args.task_id); emit({"retry": args.task_id})
            elif cmd == "invalidate": emit({"invalidated": run.invalidate(args.task_id, args.reason)})
            elif cmd == "amend": run.amend(read_json(args.brief)); emit({"amended": True, "status": run.status()})
            elif cmd == "reserve-media": emit(run.reserve_media(args.task_id, args.token, job_key=args.key, provider=args.provider,
                   request=read_json(args.request), estimated_usd=args.usd, estimated_credits=args.credits))
            elif cmd == "record-media": emit(run.record_media(args.key, status=args.status, provider_job_id=args.provider_job_id,
                   actual_usd=args.usd, actual_credits=args.credits, files=args.file))
            elif cmd == "run":
                from .runner import run_pipeline
                result = run_pipeline(run, args.provider, workers=args.workers, timeout_seconds=args.timeout_seconds,
                                      model=args.model, max_turns=args.max_turns, until=args.until, on_event=emit)
                emit(result)
                if args.until:
                    passed = any(t["id"] == args.until and t["status"] == "complete" for t in result["tasks"])
                else: passed = result["delivered"]
                return 0 if passed else 2
            elif cmd == "export-plan":
                from .render_bridge import export_plan
                emit(export_plan(run, args.output))
            elif cmd == "tts":
                from .voice import synthesize
                result = synthesize(run, args.token, voice_id=args.voice_id, model_id=args.model_id, job_key=args.key,
                                    estimated_usd=args.usd, estimated_credits=args.credits, api_key_env=args.api_key_env,
                                    timeout_seconds=args.timeout_seconds)
                emit(result); return 0 if result["status"] == "complete" else 2
            elif cmd == "recover-voice":
                from .voice import recover_saved_response
                result = recover_saved_response(run, args.token, job_key=args.key)
                emit(result); return 0 if result["status"] == "complete" else 2
        return 0
    except (ValidationError, StateError, OSError, ValueError, KeyError, TypeError) as ex:
        emit({"error": str(ex), "type": type(ex).__name__}); return 2
    except KeyboardInterrupt:
        emit({"interrupted": True, "next": "Saved task state remains; inspect jobs, then resume expired leases."}); return 130


if __name__ == "__main__": raise SystemExit(main())
