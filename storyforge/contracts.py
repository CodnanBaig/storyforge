"""Semantic gates. These checks reject incomplete evidence; they cannot prove truth.

JSON Schema files describe interchange. This dependency-free validator also checks
relationships (claims, shots, timing, leases) that JSON Schema alone cannot express.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

from .util import file_hash, frame_count, read_json, safe_path


class ValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def text(x: Any) -> bool:
    return isinstance(x, str) and bool(x.strip())


def url(x: Any) -> bool:
    return isinstance(x, str) and urlparse(x).scheme in {"https", "http"} and bool(urlparse(x).netloc)


def validate_brief(b: Any) -> dict:
    e: list[str] = []
    if not isinstance(b, dict):
        raise ValidationError(["Brief must be an object"])
    for key in ("project_name", "niche", "audience", "language"):
        if not text(b.get(key)):
            e.append(f"{key} must be a nonempty string")
    if b.get("schema_version") != "1.0": e.append("schema_version must be 1.0")
    if b.get("mode") not in {"short", "long"}: e.append("mode must be short or long")
    if b.get("content_kind") not in {"documentary", "fiction", "commentary"}: e.append("content_kind must be documentary, fiction, or commentary")
    if b.get("format") not in {"9:16", "16:9", "1:1"}: e.append("format must be 9:16, 16:9, or 1:1")
    if not number(b.get("duration_seconds")) or not 5 <= b["duration_seconds"] <= 7200:
        e.append("duration_seconds must be between 5 and 7200 for the starter renderer")
    if b.get("fps") not in {24, 25, 30, 50, 60}: e.append("fps must be 24, 25, 30, 50, or 60")
    refs = b.get("references")
    if not isinstance(refs, list): e.append("references must be an array; use [] when intentionally none")
    else:
        for i, r in enumerate(refs):
            if not isinstance(r, dict) or not text(r.get("location")) or not text(r.get("notes")):
                e.append(f"references[{i}] requires location and notes")
    hook = b.get("hook", {})
    if not isinstance(hook, dict): e.append("hook must be an object"); hook = {}
    if hook.get("mode") not in {"fixed", "family", "topic"}: e.append("hook.mode must be fixed, family, or topic")
    if hook.get("mode") == "fixed" and not text(hook.get("prefix")): e.append("fixed hook requires hook.prefix")
    if not number(hook.get("max_seconds")) or not 0 < hook["max_seconds"] <= 15:
        e.append("hook.max_seconds must be > 0 and <= 15")
    for key in ("style", "voice", "budget", "research", "release", "constraints"):
        if not isinstance(b.get(key), dict): e.append(f"{key} must be an object")
    budget = b.get("budget") if isinstance(b.get("budget"), dict) else {}
    for key, maximum in (("max_model_calls", 1000), ("max_media_jobs", 500), ("max_retries_per_task", 10)):
        v = budget.get(key)
        if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= maximum:
            e.append(f"budget.{key} must be an integer in [0, {maximum}]")
    for key in ("max_media_cost_usd", "max_media_credits"):
        if not number(budget.get(key)) or budget[key] < 0: e.append(f"budget.{key} must be nonnegative")
    research = b.get("research") if isinstance(b.get("research"), dict) else {}
    for key in ("min_sources", "min_independent_sources", "freshness_days"):
        if not isinstance(research.get(key), int) or isinstance(research[key], bool) or research[key] < 1:
            e.append(f"research.{key} must be a positive integer")
    release = b.get("release") if isinstance(b.get("release"), dict) else {}
    if release.get("intent") not in {"private_preview", "commercial"}: e.append("release.intent must be private_preview or commercial")
    # This library intentionally contains no publisher. Authorization is handled at upload time.
    if release.get("auto_publish", False) is not False: e.append("auto_publish is unsupported; package for explicit upload")
    if e: raise ValidationError(e)
    return b


def validate_envelope(r: Any, run_id: str, task_id: str, run_dir: Path) -> list[str]:
    e: list[str] = []
    if not isinstance(r, dict): return ["Task output must be a JSON object"]
    for key, expected in (("schema_version", "1.0"), ("run_id", run_id), ("task_id", task_id)):
        if r.get(key) != expected: e.append(f"{key} must equal {expected}")
    if r.get("status") not in {"complete", "blocked"}: e.append("status must be complete or blocked")
    if not text(r.get("summary")): e.append("summary is required")
    if not isinstance(r.get("data"), dict): e.append("data must be an object")
    for key in ("files", "sources", "warnings", "blockers"):
        if not isinstance(r.get(key), list): e.append(f"{key} must be an array")
    for key in ("warnings", "blockers"):
        if isinstance(r.get(key), list) and any(not text(x) for x in r[key]): e.append(f"{key} must contain nonempty strings")
    if r.get("status") == "blocked" and not r.get("blockers"): e.append("Blocked results must explain blockers")
    if r.get("status") == "complete" and r.get("blockers"): e.append("Complete results may not contain unresolved blockers")
    if isinstance(r.get("files"), list):
        for f in r["files"]:
            try: safe_path(run_dir, f)
            except (ValueError, OSError) as ex: e.append(str(ex))
    if isinstance(r.get("sources"), list):
        for i, s in enumerate(r["sources"]):
            if not isinstance(s, dict): e.append(f"sources[{i}] must be an object"); continue
            for k in ("id", "title", "publisher", "accessed_at", "independence_key"):
                if not text(s.get(k)): e.append(f"sources[{i}].{k} is required")
            if not url(s.get("url")): e.append(f"sources[{i}].url must be HTTP(S)")
            if text(s.get("accessed_at")):
                try:
                    stamp = datetime.fromisoformat(s["accessed_at"].replace("Z", "+00:00"))
                    if stamp.tzinfo is None: stamp = stamp.replace(tzinfo=timezone.utc)
                    if stamp.timestamp() > datetime.now(timezone.utc).timestamp() + 86400: e.append("Source access date is in the future")
                except ValueError: e.append("Source accessed_at must be ISO 8601")
    return e


def validate_task(task: str, r: dict, brief: dict, outputs: dict[str, dict], run_dir: Path, *, demo: bool = False) -> list[str]:
    e: list[str] = []
    d = r["data"]
    if r["status"] == "blocked": return []
    if not demo and (d.get("fixture") or d.get("demo")):
        e.append("Fixture artifacts cannot enter a real production run")
    if not demo and task in {"research", "viability", "preflight"}:
        for s in r["sources"]:
            stamp = datetime.fromisoformat(s["accessed_at"].replace("Z", "+00:00"))
            if stamp.tzinfo is None: stamp = stamp.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - stamp).total_seconds() / 86400
            if age_days > brief["research"]["freshness_days"]:
                e.append(f"Source {s['id']} was not rechecked within research.freshness_days")

    def need(k: str, typ: type = str) -> Any:
        v = d.get(k)
        if not isinstance(v, typ) or (typ is str and not text(v)):
            e.append(f"data.{k} must be {typ.__name__}")
        return v

    def path(k: str) -> Path | None:
        v = need(k)
        if not isinstance(v, str): return None
        if v not in r["files"]: e.append(f"data.{k} must be declared in files")
        try: return safe_path(run_dir, v)
        except (ValueError, OSError) as ex: e.append(str(ex)); return None

    def checks(keys: tuple[str, ...]) -> None:
        c = need("checks", dict)
        if isinstance(c, dict):
            for k in keys:
                item = c.get(k)
                if not isinstance(item, dict) or item.get("passed") is not True or not text(item.get("evidence")):
                    e.append(f"checks.{k} requires passed=true and concrete evidence")

    def packaging(value: Any, label: str) -> bool:
        good = isinstance(value, dict) and text(value.get("title")) and text(value.get("description")) and isinstance(value.get("credits"), list)
        if not good: e.append(f"{label} needs title, description and credits for independent review")
        return good

    if task == "discovery":
        candidates = need("candidates", list)
        chosen = need("selected_id")
        if isinstance(candidates, list):
            ids = [c.get("id") for c in candidates if isinstance(c, dict)]
            if len(candidates) < 3: e.append("Discovery needs at least 3 candidate angles")
            if len(set(ids)) != len(candidates): e.append("Candidate IDs must be unique")
            if chosen not in ids: e.append("selected_id must identify a candidate")
            for c in candidates:
                if not isinstance(c, dict) or not text(c.get("title")) or not text(c.get("angle")):
                    e.append("Each candidate needs id, title, angle")
                elif not demo and (not isinstance(c.get("source_urls"), list) or not c["source_urls"] or not all(url(u) for u in c["source_urls"])):
                    e.append("Each real candidate needs actual source_urls")
    elif task == "research":
        claims = need("claims", list)
        sources = r["sources"]
        ids = {s["id"] for s in sources}
        if len(ids) != len(sources): e.append("Source IDs must be unique")
        if not demo and brief["content_kind"] != "fiction":
            if len(sources) < brief["research"]["min_sources"]: e.append("Not enough sources")
            if len({s["independence_key"] for s in sources}) < brief["research"]["min_independent_sources"]:
                e.append("Not enough independent source groups")
        if not claims: e.append("Claim ledger cannot be empty")
        if isinstance(claims, list):
            claim_ids: list[str] = []
            for c in claims:
                if not isinstance(c, dict): e.append("Each claim must be an object"); continue
                if not text(c.get("id")) or not text(c.get("text")): e.append("Each claim needs id and text")
                else: claim_ids.append(c["id"])
                if c.get("status") not in {"confirmed", "reported", "disputed", "explained", "unresolved", "fictional"}: e.append("Invalid claim status")
                fictional = brief["content_kind"] == "fiction" and c.get("status") == "fictional"
                if not demo and c.get("status") == "fictional" and not fictional: e.append("Fictional claims require brief.content_kind=fiction")
                refs = c.get("source_ids")
                if not isinstance(refs, list) or not set(refs).issubset(ids) or (not demo and not fictional and not refs):
                    e.append("Each claim must reference existing source IDs")
            if len(set(claim_ids)) != len(claim_ids): e.append("Claim IDs must be unique")
    elif task == "viability":
        if d.get("recommendation") not in {"go", "revise", "reject"}: e.append("recommendation must be go/revise/reject")
        if d.get("recommendation") != "go": e.append("Selected topic needs revision or replacement before scripting")
        if d.get("confidence") not in {"low", "medium", "high"}: e.append("confidence must be low/medium/high")
        evidence = need("evidence", list)
        if not demo and d.get("confidence") in {"medium", "high"} and not evidence:
            e.append("Medium/high confidence viability requires concrete evidence; lower confidence when signals are unavailable")
        components = need("score_components", dict)
        if isinstance(components, dict):
            for k in ("demand", "competition_gap", "hook", "visual_potential", "source_quality", "production_fit"):
                if k not in components or (components[k] is not None and (not number(components[k]) or not 0 <= components[k] <= 5)):
                    e.append(f"score_components.{k} must be null (unknown) or a subjective 0–5 score")
        if any(k in d for k in ("guaranteed_views", "virality_probability")): e.append("Unsupported reach guarantees are not allowed")
    elif task == "style":
        palette = need("palette", dict)
        need("font"); need("characters", list); need("asset_rules", list)
        if isinstance(palette, dict):
            for value in palette.values():
                if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value): e.append("Palette values must be #RRGGBB")
    elif task == "script":
        narration = need("narration")
        hooks = need("hook_candidates", list)
        chosen = need("selected_hook")
        if isinstance(hooks, list) and (len(hooks) < 3 or chosen not in hooks): e.append("Provide 3 hook candidates and select one verbatim")
        if isinstance(narration, str) and isinstance(chosen, str) and not narration.startswith(chosen): e.append("Narration must start with selected_hook")
        if brief["hook"]["mode"] == "fixed" and isinstance(chosen, str) and not chosen.startswith(brief["hook"]["prefix"]):
            e.append("Hook does not preserve the fixed prefix")
        ids = need("claim_ids", list)
        known = {c["id"] for c in outputs["research"]["data"]["claims"]}
        if isinstance(ids, list) and (not set(ids).issubset(known) or not ids): e.append("Script must cite existing claim IDs")
        if isinstance(narration, str):
            wpm = len(narration.split()) * 60 / brief["duration_seconds"]
            if not demo and not 70 <= wpm <= 220: e.append("Script word budget is implausible for target duration (70–220 WPM heuristic); revise or specify a longer format")
        if brief["mode"] == "long":
            chapters = need("chapters", list)
            if isinstance(chapters, list) and len(chapters) < 2: e.append("Long form needs at least 2 substantive chapters")
    elif task == "fact_check":
        if d.get("approved") is not True: e.append("Independent fact check did not pass")
        if need("issues", list): e.append("Unresolved factual issues remain")
        verified = need("verified_claim_ids", list)
        if isinstance(verified, list) and not set(outputs["script"]["data"]["claim_ids"]).issubset(verified):
            e.append("Every scripted claim needs independent verification")
    elif task == "direction":
        shots = need("shots", list)
        target = d.get("target_duration_seconds")
        if not number(target) or abs(target - brief["duration_seconds"]) > 1 / brief["fps"]:
            e.append("Director duration must match the brief")
        if not shots: e.append("Shot plan cannot be empty")
        if isinstance(shots, list):
            end = 0.0
            ids: set[str] = set()
            for s in shots:
                if not isinstance(s, dict): e.append("Shot must be an object"); continue
                if not text(s.get("id")) or s["id"] in ids: e.append("Shot IDs must be present and unique")
                else: ids.add(s["id"])
                for k in ("purpose", "action", "camera", "environment"):
                    if not text(s.get(k)): e.append(f"Shot {s.get('id')} requires {k}")
                start, duration = s.get("start_seconds"), s.get("duration_seconds")
                if not number(start) or not number(duration) or duration <= 0: e.append("Shots need numeric start and positive duration"); continue
                if abs(start - end) > 1 / brief["fps"]: e.append("Shots must cover the timeline contiguously; bake transition overlap into durations")
                end = start + duration
            if abs(end - brief["duration_seconds"]) > 1 / brief["fps"]: e.append("Shot durations do not cover the brief")
    elif task == "preflight":
        if d.get("approved") is not True: e.append("Preflight not approved")
        if d.get("scope") != brief["release"]["intent"]: e.append("Preflight scope differs from requested release intent")
        checks(("facts", "originality", "rights", "disclosure", "resources"))
        if not demo and not r["sources"]: e.append("Preflight needs current official policy/license sources")
        if not demo:
            domains = [urlparse(s["url"]).hostname or "" for s in r["sources"]]
            if not any(host == "support.google.com" or host == "youtube.com" or host.endswith(".youtube.com") for host in domains):
                e.append("Preflight requires at least one current official YouTube policy source")
    elif task in {"assets_3d", "assets_images"}:
        assets = need("assets", list)
        if d.get("not_needed") is not True and not assets: e.append("Provide assets or explicitly explain not_needed")
        if isinstance(assets, list):
            for a in assets:
                if not isinstance(a, dict) or not text(a.get("id")) or not text(a.get("path")) or not text(a.get("rights")):
                    e.append("Each asset needs id, path and rights")
                else:
                    if a["path"] not in r["files"]: e.append("Asset path must be declared in files")
                    try: safe_path(run_dir, a["path"])
                    except (ValueError, OSError) as ex: e.append(str(ex))
    elif task == "voice":
        audio = path("audio_path"); captions = path("captions_path"); need("provider")
        planned_provider = brief.get("voice", {}).get("provider")
        if not demo and planned_provider not in {None, "", "external", "supplied"} and d.get("provider") != planned_provider:
            e.append("Narration provider differs from the approved brief; do not silently substitute")
        if not demo:
            for key in ("voice_id", "model_id"):
                planned = brief.get("voice", {}).get(key)
                if planned and d.get(key) != planned: e.append(f"Narration {key} differs from the approved brief")
        duration = d.get("duration_seconds")
        if not number(duration) or duration <= 0 or duration > brief["duration_seconds"] + 0.05:
            e.append("Narration duration must be measured, positive, and fit target")
        hook_end = d.get("hook_end_seconds")
        if not demo and (not number(hook_end) or hook_end <= 0 or hook_end > brief["hook"]["max_seconds"] + 0.05 or (number(duration) and hook_end > duration)):
            e.append("Measured hook_end_seconds must fit the agreed hook.max_seconds and actual narration")
        if not demo and d.get("timing_source") not in {"forced_alignment", "provider_alignment", "human_verified"}:
            e.append("Captions require actual aligned narration; estimated timings cannot pass")
        if captions:
            try:
                words = read_json(captions)
                if not isinstance(words, list) or not words: e.append("Caption word list cannot be empty")
                else:
                    previous = 0.0
                    for w in words:
                        if not isinstance(w, dict) or not text(w.get("text")) or not number(w.get("start")) or not number(w.get("end")):
                            e.append("Caption words need text/start/end seconds"); break
                        if w["start"] < previous - 0.01 or w["end"] <= w["start"] or (number(duration) and w["end"] > duration + 0.1):
                            e.append("Caption timings overlap, reverse, or exceed narration")
                        previous = w["end"]
            except (ValueError, OSError) as ex: e.append(f"Invalid captions: {ex}")
        if audio and not demo:
            from .media import probe_media
            try:
                probe = probe_media(audio)
                if not any(s.get("codec_type") == "audio" for s in probe["streams"]): e.append("Narration file has no audio stream")
                measured = float(probe["format"]["duration"])
                if number(duration) and abs(measured-duration) > 0.25: e.append("Narration duration differs from actual media probe")
            except (ValueError, OSError, RuntimeError, KeyError) as ex: e.append(f"Cannot verify narration: {ex}")
    elif task == "sound":
        if not isinstance(d.get("music"), list) or not isinstance(d.get("sfx"), list): e.append("music and sfx must be arrays")
        if not d.get("music") and not d.get("sfx") and d.get("intentional_silence") is not True:
            e.append("Explain intentional_silence or provide sound assets")
        for item in d.get("music", []) + d.get("sfx", []):
            if not isinstance(item, dict) or not text(item.get("path")) or not text(item.get("rights")): e.append("Sound assets need path and rights")
            else:
                if item["path"] not in r["files"]: e.append("Sound paths must be declared in files")
                try: safe_path(run_dir, item["path"])
                except (ValueError, OSError) as ex: e.append(str(ex))
    elif task == "edit":
        if not demo: packaging(d.get("packaging_draft"), "data.packaging_draft")
        manifest = path("manifest_path")
        if manifest:
            try:
                m = read_json(manifest)
                if isinstance(m, dict) and "manifest" in m: m = m["manifest"]
                if not isinstance(m, dict): e.append("Edit manifest must be an object")
                elif not m.get("scenes"): e.append("Edit manifest needs scenes")
                else:
                    if not demo and m.get("demo") is not False: e.append("A demo/draft manifest cannot complete a production edit")
                    fmt = m.get("format", {})
                    if fmt.get("fps") != brief["fps"]: e.append("Manifest FPS differs from brief")
                    total = sum(s["duration_in_frames"] for s in m["scenes"])
                    if total != frame_count(brief["duration_seconds"], brief["fps"]): e.append("Manifest frame total differs from target")
                    narration = m.get("narration")
                    if not demo and (not isinstance(narration, dict) or narration.get("measured") is not True):
                        e.append("Production manifest needs measured narration")
                    elif not demo and abs(narration.get("duration_seconds", 0)-outputs["voice"]["data"]["duration_seconds"]) > 0.05:
                        e.append("Manifest narration differs from verified voice artifact")
                    if not demo and not m.get("captions"): e.append("Production manifest needs aligned captions")
            except (ValueError, OSError) as ex: e.append(f"Invalid edit manifest: {ex}")
    elif task == "render":
        video = path("video_path"); path("probe_path")
        if video and not demo:
            from .media import validate_video
            e.extend(validate_video(video, brief)["errors"])
    elif task == "qa":
        if d.get("approved") is not True: e.append("Final QA not approved")
        checks(("visual", "audio", "captions", "facts", "rights", "originality", "disclosure"))
        if not demo and packaging(d.get("reviewed_packaging"), "data.reviewed_packaging"):
            draft = outputs.get("edit", {}).get("data", {}).get("packaging_draft")
            if d["reviewed_packaging"] != draft:
                e.append("QA must approve the exact editor packaging draft; revise it upstream before approving changed copy")
        report_path = path("technical_report_path")
        if report_path:
            try:
                report = read_json(report_path)
                if not isinstance(report, dict) or report.get("passed") is not True or report.get("errors") != []:
                    e.append("Technical report must actually pass with no errors")
            except (ValueError, OSError) as ex: e.append(f"Cannot read technical QA report: {ex}")
    elif task == "package":
        need("title"); need("description"); need("credits", list)
        delivery = need("delivery_files", list)
        if isinstance(delivery, list):
            for f in delivery:
                if f not in r["files"]: e.append("Every delivery file must be declared in files")
                try: safe_path(run_dir, f)
                except (ValueError, OSError) as ex: e.append(str(ex))
        if not delivery: e.append("Delivery package cannot be empty")
        if not demo:
            approved = outputs.get("qa", {}).get("data", {}).get("reviewed_packaging")
            if packaging(approved, "QA-reviewed packaging"):
                for key in ("title", "description", "credits"):
                    if d.get(key) != approved[key]: e.append(f"Final {key} differs from the independently reviewed packaging")
                if approved.get("thumbnail_path") != d.get("thumbnail_path"):
                    e.append("Final thumbnail differs from the independently reviewed packaging")
        if not demo and isinstance(delivery, list):
            rendered = outputs.get("render", {}).get("data", {}).get("video_path")
            if not rendered: e.append("Verified rendered video is missing from upstream context")
            else:
                expected_hash = file_hash(safe_path(run_dir, rendered))
                found = False
                for f in delivery:
                    try:
                        if file_hash(safe_path(run_dir, f)) == expected_hash: found = True
                    except (ValueError, OSError): pass
                if not found: e.append("Delivery must include the verified rendered video or a byte-identical copy")
    return e
