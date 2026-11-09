from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .contracts import ValidationError, validate_brief
from .demo import create_demo
from .intake import interactive
from .media import captions_to_srt, validate_video
from .pipeline import TASKS
from .prompts import task_prompt, write_task_packet
from .store import Run, StateError
from .util import read_json, write_json


def emit(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), flush=True)


def setup_summary(result: dict) -> None:
    print(f"StoryForge {__version__} project prepared\n\nProject:  {result['project_root']}")
    print(f"Renderer: {result['renderer_root']}")
    print("Agents:   " + (", ".join(result["hosts"]) or "none selected"))
    dependency_status = result["renderer_dependencies"]["status"].replace("_", " ")
    print(f"Renderer dependencies: {dependency_status}")
    print(f"Files: {len(result['created'])} created, {len(result['updated'])} updated, {len(result['unchanged'])} unchanged")
    for warning in result["warnings"]:
        print(f"Note: {warning}")
    if result["renderer_dependencies"]["status"] == "skipped":
        print("\nRerun storyforge setup without --skip-install before opening the renderer.")
    workflow = (Path(result["toolkit_root"]) / "WORKFLOW.md").relative_to(Path(result["project_root"]))
    print(f'\nOpen this project in Codex or Claude and say:\n  "Start StoryForge using {workflow.as_posix()}."')
    print("\nUseful commands:\n  storyforge start    Collect a brief and create a saved run\n  storyforge studio   Open the video editor\n  storyforge preview  Render demo preview frames\n  storyforge doctor   Check local readiness", flush=True)


def start_summary(result: dict) -> None:
    print(f"Created production: {result['run_id']}\n\nRun:   {result['path']}\nBrief: {result['brief']}")
    print(f"Ready tasks: {', '.join(result['ready'])}")
    print(f"\nContinue in Codex or Claude:\n  Continue StoryForge run {result['path']}. Use the saved brief.\n", flush=True)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="storyforge", description="Install, prepare and run a resumable multi-agent video studio in any project.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("setup", help="Add StoryForge agents and a renderer to a new or existing project")
    a.add_argument("directory", type=Path, nargs="?", help="Project directory (default: current project or current directory)")
    a.add_argument("--host", choices=["both", "codex", "claude", "none"],
                   help="Agent hosts to add (both for new projects; preserve existing selection on reruns)")
    a.add_argument("--skip-install", action="store_true", help="Prepare files without downloading renderer dependencies")
    a.add_argument("--keep-local", type=str, action="append", default=[], metavar="PATH",
                   help="Acknowledge an already reviewed local merge for one managed resource, preserving its bytes (repeatable; project-relative)")
    a.add_argument("--json", action="store_true", help="Return structured setup details and the complete file inventory")
    for command in ("info", "doctor"):
        a = sub.add_parser(command, help="Show package/project paths" if command == "info" else "Inspect local prerequisites and show setup next steps")
        a.add_argument("--project", type=Path, help="A directory within the project (default: current directory)")
    a = sub.add_parser("start", help="Ask for a production brief and create a saved run")
    a.add_argument("--brief", type=Path, help="Use an existing validated brief instead of asking questions")
    a.add_argument("--project", type=Path)
    a.add_argument("--runs-dir", type=Path, help="Override the project's saved-runs directory")
    a.add_argument("--json", action="store_true", help="Return structured saved-run state")
    for command in ("studio", "preview", "render"):
        a = sub.add_parser(command, help={"studio": "Open the project's Remotion Studio server",
                                         "preview": "Render preview stills in the project's renderer",
                                         "render": "Render a video from an explicit props file"}[command])
        a.add_argument("--project", type=Path)
        a.add_argument("--props", type=Path, required=command == "render")
        if command in {"preview", "render"}:
            a.add_argument("--out", type=Path, required=command == "render", help="Output directory for stills, or output video filename")
        if command == "preview":
            a.add_argument("--frames", help="Comma-separated frame numbers; defaults to one frame per scene")
            a.add_argument("--scale", type=float, default=0.5)
        if command == "render":
            a.add_argument("--allow-demo", action="store_true", help="Permit a visibly labeled technical demonstration export")
    a = sub.add_parser("intake", help="Ask niche, duration, format, references, and preferences")
    a.add_argument("--output", type=Path, default=Path("brief.json"))
    a = sub.add_parser("init", help="Create a fresh saved run from a validated brief")
    a.add_argument("--brief", type=Path, required=True); a.add_argument("--runs-dir", type=Path,
                   help="Defaults to the project's saved-runs directory, or ./runs without setup")
    a = sub.add_parser("validate-brief"); a.add_argument("file", type=Path)
    a = sub.add_parser("demo", help="Exercise the offline workflow fixture; never generates media")
    a.add_argument("--runs-dir", type=Path)
    for cmd in ("status", "next", "resume", "events", "gates"):
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
    a = sub.add_parser("approve-gate", help="Record an explicit owner decision for a finished stage")
    a.add_argument("run_dir", type=Path); a.add_argument("gate", choices=["niche", "visual", "script", "final"])
    a.add_argument("--choice", required=True); a.add_argument("--evidence", required=True)
    a.add_argument("--actor", default="human-owner")
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
        if cmd == "setup":
            from .project import find_project
            from .scaffold import setup_project
            from .workspace import install_renderer, selected_project
            directory = args.directory.expanduser() if args.directory is not None else Path.cwd()
            existing = find_project(directory) if directory.exists() else None
            if args.directory is None and existing is not None:
                directory = existing.root
            host = args.host
            if host is None:
                if existing and existing.root == directory.resolve():
                    hosts = set(existing.config["hosts"])
                    host = "both" if hosts == {"codex", "claude"} else next(iter(hosts), "none")
                else:
                    host = "both"
            result = setup_project(directory, host=host, keep_local=args.keep_local)
            project = selected_project(Path(result["project_root"]), required=True)
            assert project is not None
            result["renderer_dependencies"] = {"status": "skipped"} if args.skip_install else install_renderer(project)
            result["next"] = ["Open Codex or Claude in this project and ask it to start StoryForge.",
                              "Run storyforge start for terminal intake, or storyforge studio for the editor.",
                              "Run storyforge doctor to check local readiness."]
            emit(result) if args.json else setup_summary(result)
        elif cmd == "info":
            from .workspace import project_info
            emit(project_info(args.project))
        elif cmd == "doctor":
            from .workspace import doctor
            emit(doctor(args.project))
        elif cmd == "start":
            from .workspace import default_runs_dir, selected_project
            project = selected_project(args.project)
            runs = default_runs_dir(args.runs_dir, args.project)
            brief = validate_brief(read_json(args.brief) if args.brief else interactive())
            run = Run.create(brief, runs, project_root=project.root if project else None)
            result = {**run.status(), "brief": str(run.path / "brief.json"),
                      "next": f"Open your agent host and ask it to continue StoryForge run {run.path}. Use the saved brief; no need to repeat intake."}
            emit(result) if args.json else start_summary(result)
        elif cmd in {"studio", "preview", "render"}:
            from .workspace import renderer_command
            return renderer_command(cmd, start=args.project, props=args.props,
                                    output=getattr(args, "out", None), frames=getattr(args, "frames", None),
                                    scale=getattr(args, "scale", 0.5), allow_demo=getattr(args, "allow_demo", False))
        elif cmd == "intake":
            if args.output.exists(): raise StateError("Intake output already exists; choose a new path to preserve it")
            brief = validate_brief(interactive()); write_json(args.output, brief); emit({"brief": str(args.output.resolve())})
        elif cmd == "validate-brief": validate_brief(read_json(args.file)); emit({"valid": True})
        elif cmd in {"init", "demo"}:
            from .workspace import default_runs_dir, selected_project
            project = selected_project()
            runs = default_runs_dir(args.runs_dir)
            options = {"project_root": project.root if project else None}
            emit((Run.create(read_json(args.brief), runs, **options) if cmd == "init" else create_demo(runs, **options)).status())
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
            elif cmd == "gates": emit({"gates": run.status()["gates"]})
            elif cmd == "approve-gate": emit(run.approve_studio_gate(args.gate, args.choice, args.evidence, args.actor))
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
        details = {"conflicts": ex.conflicts} if hasattr(ex, "conflicts") else {}
        emit({"error": str(ex), "type": type(ex).__name__, **details}); return 2
    except KeyboardInterrupt:
        emit({"interrupted": True, "next": "Project files and saved run state remain. Inspect active jobs before resuming production."}); return 130


if __name__ == "__main__": raise SystemExit(main())
