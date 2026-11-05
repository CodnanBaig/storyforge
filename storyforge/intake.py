from __future__ import annotations

from typing import Callable


def make_brief(*, project_name: str = "First production", niche: str = "Documented mysteries and unusual events",
               mode: str = "short", duration: float = 45, format: str = "9:16") -> dict:
    return {
        "schema_version": "1.0", "project_name": project_name, "niche": niche,
        "content_kind": "documentary", "mode": mode, "duration_seconds": duration,
        "format": format, "fps": 30, "audience": "English-speaking curious adults",
        "language": "English", "tone": "Curious, cinematic, clear; atmospheric without sensational claims",
        "references": [],
        "hook": {"mode": "family", "prefix": "", "max_seconds": 3,
                 "guidance": "Open with the story's specific surprising fact, image, or unresolved question; earn the payoff."},
        "style": {"preset": "midnight-dossier", "status": "provisional", "font": "DejaVu Sans and DejaVu Serif (bundled)",
                  "character_style": "Simple procedural human silhouettes, stable proportions and costume IDs",
                  "reference_interpretation": "Use references for visual direction; verify rights before copying actual assets."},
        "voice": {"provider": "external", "required": True, "voice_id": "", "model_id": "",
                  "direction": "Warm, grounded, expressive narration; natural pauses; no presenter on camera"},
        "research": {"min_sources": 2, "min_independent_sources": 2, "freshness_days": 14,
                     "region": "global", "analytics_file": None},
        "budget": {"max_model_calls": 40, "max_media_jobs": 12, "max_media_cost_usd": 0,
                   "max_media_credits": 0, "max_retries_per_task": 2},
        "release": {"intent": "private_preview", "auto_publish": False},
        "constraints": {"no_presenter": True, "graphic_violence": False, "assets_first": "procedural",
                        "music": "Original or specifically licensed; optional when silence serves the story",
                        "reference_notes": "No references supplied; use provisional style for initial blocking."},
    }


def interactive(input_fn: Callable[[str], str] = input, output_fn: Callable[[str], None] = print) -> dict:
    def ask(prompt: str, default: str = "") -> str:
        value = input_fn(f"{prompt}" + (f" [{default}]" if default else "") + ": ").strip()
        return value or default
    output_fn("StoryForge production brief — saved preferences can be reused next time.")
    name = ask("Project name", "First production")
    niche = ask("What niche or subject should the research focus on?")
    while not niche: niche = ask("Please give a niche, topic, or genre")
    kind = ask("Content: documentary, fiction, or commentary", "documentary")
    mode = ask("Length class: short or long", "short")
    duration = float(ask("Approximate length in seconds", "45" if mode == "short" else "480"))
    format = ask("Format: 9:16, 16:9, or 1:1", "9:16" if mode == "short" else "16:9")
    brief = make_brief(project_name=name, niche=niche, mode=mode, duration=duration, format=format)
    brief["content_kind"] = kind
    brief["audience"] = ask("Who should this reach? Include region if relevant", brief["audience"])
    brief["language"] = ask("Narration language", "English")
    brief["tone"] = ask("Tone and intensity", brief["tone"])
    output_fn("Add any videos, screenshots, character sheets, fonts, palettes, audio, scripts, or asset/project references. Press Enter when finished.")
    while True:
        location = ask("Reference URL or file path (Enter to finish)")
        if not location: break
        notes = ask("What should this reference guide: appearance, movement, pacing, sound, typography, or something else?", "Visual direction")
        brief["references"].append({"location": location, "notes": notes})
    brief["constraints"]["reference_notes"] = ask("Anything else to preserve or avoid? Include character traits and visual limits", "No on-camera presenter; use consistent illustrative characters")
    if brief["references"]: brief["style"]["status"] = "references_supplied"
    brief["hook"]["mode"] = ask("Hook: fixed phrase, repeatable family, or topic-specific? Enter fixed/family/topic", "family")
    if brief["hook"]["mode"] == "fixed": brief["hook"]["prefix"] = ask("Exact recurring opening phrase")
    else: brief["hook"]["guidance"] = ask("Hook examples or guidance", brief["hook"]["guidance"])
    brief["voice"]["provider"] = ask("Voice provider or supplied audio workflow", "external")
    brief["voice"]["voice_id"] = ask("Preferred voice ID/name (Enter to choose during casting)")
    brief["release"]["intent"] = ask("Intended use: private_preview or commercial", "private_preview")
    brief["budget"]["max_media_cost_usd"] = float(ask("Authorized media spending cap in USD", "0"))
    brief["budget"]["max_media_credits"] = float(ask("Authorized use of existing media-provider credits", "0"))
    output_fn("The orchestrator can now research candidates. No views or monetization are guaranteed.")
    return brief
