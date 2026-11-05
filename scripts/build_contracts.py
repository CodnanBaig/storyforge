"""Regenerate public JSON interchange schemas and example briefs.

The executable semantic validator remains storyforge/contracts.py. Regenerate
these only when changing the public contract, and review both together.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from storyforge.intake import make_brief
from storyforge.util import write_json

S = {"type": "string", "minLength": 1}
N = {"type": "number"}
A = {"type": "array"}
O = {"type": "object"}
string_list = {"type": "array", "items": S}
source = {"type": "object", "required": ["id", "url", "title", "publisher", "accessed_at", "independence_key"],
          "properties": {k: S for k in ["id", "title", "publisher", "independence_key"]} | {
              "url": {"type": "string", "format": "uri", "pattern": "^https?://"},
              "accessed_at": {"type": "string", "format": "date-time"}}, "additionalProperties": True}

brief = make_brief()
props = {
    "schema_version": {"const": "1.0"}, "project_name": S, "niche": S,
    "content_kind": {"enum": ["documentary", "fiction", "commentary"]},
    "mode": {"enum": ["short", "long"]}, "duration_seconds": {"type": "number", "minimum": 5, "maximum": 7200},
    "format": {"enum": ["9:16", "16:9", "1:1"]}, "fps": {"enum": [24, 25, 30, 50, 60]},
    "audience": S, "language": S, "tone": S,
    "references": {"type": "array", "items": {"type": "object", "required": ["location", "notes"], "properties": {"location": S, "notes": S}, "additionalProperties": True}},
    "hook": {"type": "object", "required": ["mode", "max_seconds"], "properties": {
        "mode": {"enum": ["fixed", "family", "topic"]}, "prefix": {"type": "string"},
        "max_seconds": {"type": "number", "exclusiveMinimum": 0, "maximum": 15}, "guidance": S},
        "allOf": [{"if": {"properties": {"mode": {"const": "fixed"}}}, "then": {"required": ["prefix"], "properties": {"prefix": S}}}]},
    "style": O, "voice": O,
    "research": {"type": "object", "required": ["min_sources", "min_independent_sources", "freshness_days"],
        "properties": {k: {"type": "integer", "minimum": 1} for k in ["min_sources", "min_independent_sources", "freshness_days"]}},
    "budget": {"type": "object", "required": list(brief["budget"]), "properties": {
        "max_model_calls": {"type": "integer", "minimum": 0, "maximum": 1000, "description": "Worker process invocations, not provider-internal LLM turns"},
        "max_media_jobs": {"type": "integer", "minimum": 0, "maximum": 500},
        "max_retries_per_task": {"type": "integer", "minimum": 0, "maximum": 10},
        "max_media_cost_usd": {"type": "number", "minimum": 0}, "max_media_credits": {"type": "number", "minimum": 0}}},
    "release": {"type": "object", "required": ["intent"], "properties": {"intent": {"enum": ["private_preview", "commercial"]}, "auto_publish": {"const": False}}},
    "constraints": O,
}
required = [k for k in props if k != "tone"]
write_json(ROOT / "schemas/brief.schema.json", {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://storyforge.local/schemas/brief.schema.json", "title": "StoryForge Production Brief", "type": "object", "required": required, "properties": props, "additionalProperties": True})

def obj(properties): return {"type": "object", "required": list(properties), "properties": properties, "additionalProperties": True}
checks = {"type": "object", "additionalProperties": obj({"passed": {"type": "boolean"}, "evidence": S})}
task_fields = {
    "discovery": {"candidates": {"type": "array", "minItems": 3, "items": obj({"id": S, "title": S, "angle": S, "source_urls": string_list})}, "selected_id": S},
    "style": {"palette": O, "font": S, "characters": A, "asset_rules": string_list},
    "research": {"claims": {"type": "array", "minItems": 1, "items": obj({"id": S, "text": S, "status": {"enum": ["confirmed", "reported", "disputed", "explained", "unresolved", "fictional"]}, "source_ids": string_list})}},
    "viability": {"score_components": obj({k: {"type": ["number", "null"], "minimum": 0, "maximum": 5} for k in ["demand", "competition_gap", "hook", "visual_potential", "source_quality", "production_fit"]}), "recommendation": {"enum": ["go", "revise", "reject"]}, "confidence": {"enum": ["low", "medium", "high"]}, "evidence": A},
    "script": {"hook_candidates": {"type": "array", "minItems": 3, "items": S}, "selected_hook": S, "narration": S, "claim_ids": string_list},
    "fact_check": {"approved": {"type": "boolean"}, "issues": A, "verified_claim_ids": string_list},
    "direction": {"target_duration_seconds": N, "shots": {"type": "array", "minItems": 1, "items": obj({"id": S, "start_seconds": N, "duration_seconds": N, "purpose": S, "action": S, "camera": S, "environment": S})}},
    "preflight": {"approved": {"type": "boolean"}, "scope": {"enum": ["private_preview", "commercial"]}, "checks": checks},
    "assets_3d": {"assets": A}, "assets_images": {"assets": A},
    "voice": {"audio_path": S, "duration_seconds": N, "captions_path": S, "provider": S, "hook_end_seconds": N, "timing_source": {"enum": ["forced_alignment", "provider_alignment", "human_verified"]}},
    "sound": {"music": A, "sfx": A}, "edit": {"manifest_path": S, "packaging_draft": obj({"title": S, "description": S, "credits": A})}, "render": {"video_path": S, "probe_path": S},
    "qa": {"approved": {"type": "boolean"}, "checks": checks, "technical_report_path": S, "reviewed_packaging": obj({"title": S, "description": S, "credits": A})},
    "package": {"title": S, "description": S, "credits": A, "delivery_files": string_list},
}
schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://storyforge.local/schemas/task-result.schema.json",
    "title": "StoryForge Task Result", "type": "object", "required": ["schema_version", "run_id", "task_id", "status", "summary", "data", "files", "sources", "warnings", "blockers"],
    "properties": {"schema_version": {"const": "1.0"}, "run_id": S, "task_id": {"enum": list(task_fields)}, "status": {"enum": ["complete", "blocked"]},
                   "summary": S, "data": O, "files": string_list, "sources": {"type": "array", "items": source}, "warnings": string_list, "blockers": string_list},
    "allOf": [{"if": {"properties": {"task_id": {"const": task}, "status": {"const": "complete"}}}, "then": {"properties": {"data": {"$ref": f"#/$defs/{task}"}}}} for task in task_fields],
    "$defs": {task: obj(fields) for task, fields in task_fields.items()}, "additionalProperties": True}
write_json(ROOT / "schemas/task-result.schema.json", schema)
write_json(ROOT / "schemas/words.schema.json", {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "array", "minItems": 1, "items": obj({"text": S, "start": {"type": "number", "minimum": 0}, "end": {"type": "number", "exclusiveMinimum": 0}})})
write_json(ROOT / "examples/brief-mystery-short.json", brief)
long = make_brief(project_name="Long-form science story", niche="Strange natural phenomena explained through evidence", mode="long", duration=480, format="16:9")
long["tone"] = "Curious documentary with clear explanations and chapter-level payoffs"
write_json(ROOT / "examples/brief-science-long.json", long)
fiction = make_brief(project_name="Original eerie fiction", niche="Original quiet horror stories, atmospheric and non-graphic", duration=60)
fiction["content_kind"] = "fiction"; fiction["hook"]["mode"] = "topic"
write_json(ROOT / "examples/brief-fiction-short.json", fiction)
fixed = make_brief(project_name="One overlooked fact", niche="Surprising documented everyday science")
fixed["hook"].update(mode="fixed", prefix="Here is one fact you might have missed.")
write_json(ROOT / "examples/brief-fixed-hook.json", fixed)
print("Generated 3 schemas and 4 example briefs.")
