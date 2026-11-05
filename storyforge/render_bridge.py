"""Turn a director's shot plan into a reviewable draft, never fake final media."""
from pathlib import Path

from .store import Run, StateError
from .util import frame_count, write_json


TEMPLATES = ("lighthouse-coast", "archive-room", "signal-chamber", "forest-path")


def export_plan(run: Run, output: Path) -> dict:
    ctx = run.context("edit")
    direction = ctx["dependencies"].get("direction")
    if not direction or direction["status"] != "complete": raise StateError("Complete the director's shot plan first")
    brief = ctx["brief"]; fps = brief["fps"]
    dimensions = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}
    width, height = dimensions[brief["format"]]
    scenes = []
    previous_end = 0
    for i, shot in enumerate(direction["data"]["shots"]):
        end = frame_count(shot["start_seconds"] + shot["duration_seconds"], fps)
        frames = end - previous_end
        if frames < 2: raise StateError("Each shot needs at least two frames in the starter renderer")
        previous_end = end
        # Explicit template selection wins; the cycling fallback is only blocking.
        template = shot.get("template")
        if template not in TEMPLATES: template = TEMPLATES[i % len(TEMPLATES)]
        camera = shot.get("camera")
        if camera not in {"wide", "medium", "detail"}: camera = ("wide", "medium", "detail")[i % 3]
        scenes.append({"id": shot["id"], "template": template, "duration_in_frames": frames,
                       "eyebrow": f"{i+1:02} / DRAFT BLOCKING", "headline": shot["purpose"],
                       "body": shot["action"], "character_id": "participant-01", "camera": camera, "seed": i+1})
    manifest = {"schema_version": "1.0", "project_id": ctx["run_id"], "title": brief["project_name"],
                "demo": True, "format": {"width": width, "height": height, "fps": fps},
                "style_id": "midnight-dossier", "characters": [{"id": "participant-01", "name": "Story participant",
                    "coat": "#477D79", "skin": "#D7B79A", "trousers": "#202E3E", "scale": 1}],
                "assets": [], "scenes": scenes, "narration": None, "music": None, "captions": []}
    write_json(output, {"manifest": manifest})
    return {"props": str(output.resolve()), "scenes": len(scenes), "frames": previous_end,
            "demo": True, "warning": "Draft blocking uses starter environments. The editor must author story-specific geometry, camera, and action, then supply measured narration and aligned captions before production."}
