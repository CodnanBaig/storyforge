"""Deterministic offline fixture: demonstrates state, not fake completed production."""
from pathlib import Path

from .intake import make_brief
from .store import Run


def create_demo(runs_dir: Path, *, project_root: Path | None = None) -> Run:
    brief = make_brief(project_name="Offline workflow demonstration", niche="Fictional mystery: a lighthouse without a light")
    brief["content_kind"] = "fiction"
    brief["budget"]["max_model_calls"] = 0
    brief["budget"]["max_media_jobs"] = 0
    run = Run.create(brief, runs_dir, demo=True, project_root=project_root)
    rid = run.status()["run_id"]
    hook = "At midnight, the lighthouse went dark."
    script = hook + " The keeper climbed the stairs, carrying the only working torch. Every window reflected an empty sea. But upstairs, a small green signal flashed from inside a locked drawer. He opened it. The light stopped. There was no lamp inside, only an old brass key, still warm. Then, far below, the front door unlocked. This is an original fictional scene, made to demonstrate the production workflow."
    outputs = {
        "discovery": {"candidates": [{"id": f"c{i}", "title": title, "angle": "Original fictional technical demonstration", "source_urls": []}
                       for i, title in enumerate(["The silent lighthouse", "The missing echo", "The sealed room"], 1)], "selected_id": "c1"},
        "style": {"palette": {"background": "#08131D", "teal": "#49CCBB", "accent": "#E5B56E"}, "font": "system sans-serif",
                  "characters": [{"id": "keeper", "costume": "navy coat", "geometry": "low-poly procedural mannequin"}],
                  "asset_rules": ["No presenter", "Stable proportions", "No realistic archival claim", "Frame-driven animation"]},
        "research": {"claims": [{"id": "fiction-1", "text": "The keeper finds a warm key in an unlit lighthouse.", "status": "fictional", "source_ids": []}]},
        "viability": {"score_components": {"demand": None, "competition_gap": None, "hook": 4, "visual_potential": 4, "source_quality": None, "production_fit": 5},
                      "recommendation": "go", "confidence": "low", "evidence": [], "caveat": "Fixture scores test the contract, not audience demand."},
        "script": {"hook_candidates": [hook, "The locked drawer was blinking.", "He heard the door unlock below him."], "selected_hook": hook,
                   "narration": script, "claim_ids": ["fiction-1"], "chapters": []},
        "fact_check": {"approved": True, "issues": [], "verified_claim_ids": ["fiction-1"], "review_basis": "Fictional continuity fixture; no historical claims"},
        "direction": {"target_duration_seconds": 45, "shots": [
            {"id": f"s{i+1}", "start_seconds": i*9, "duration_seconds": 9, "purpose": purpose,
             "action": action, "camera": "Slow frame-driven push", "environment": "Procedural lighthouse diorama"}
            for i, (purpose, action) in enumerate([("Hook", "Beacon extinguishes"), ("Orient", "Keeper climbs stairs"), ("Escalate", "Light leaks from drawer"), ("Reveal", "Warm brass key is found"), ("Payoff", "Door unlocks below")])]},
    }
    for task_id, data in outputs.items():
        claim = run.claim(task_id, "offline-fixture")
        result = run.submit(task_id, claim["token"], {"schema_version": "1.0", "run_id": rid, "task_id": task_id,
                     "status": "complete", "summary": "Offline fixture — no research, generation, or billing occurred.",
                     "data": {**data, "fixture": True}, "files": [], "sources": [],
                     "warnings": ["Demonstration only; cannot be released as researched content"], "blockers": []})
        if not result["accepted"]: raise RuntimeError(f"Demo contract failure: {result}")
    claim = run.claim("preflight", "offline-fixture")
    run.submit("preflight", claim["token"], {"schema_version": "1.0", "run_id": rid, "task_id": "preflight", "status": "blocked",
               "summary": "Fixture stops before production", "data": {"fixture": True}, "files": [], "sources": [], "warnings": [],
               "blockers": ["This is an offline fixture. Start a real brief for live research, verified rights, actual narration and rendered delivery."]})
    return run
