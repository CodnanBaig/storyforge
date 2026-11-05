# Edit — Remotion editor

**Task:** edit. **Inputs:** direction, accepted visual assets, measured narration/word timing, music/effects, style bible and renderer contracts.

## Objective

Assemble a reproducible, story-specific timeline whose visuals, captions and sound follow the real narration.

## Procedure

1. Work in a run-local renderer copy inside your assigned workspace. Integrate accepted component patches and media using stable asset IDs. Keep the reusable library and other workers' outputs unchanged.
2. Use the actual narration to set beat boundaries and visual reveal cues. Verify the final frame count against the brief, including any transition overlap.
3. Author scene action, camera and lighting deliberately. The starter export-plan environments are draft blocking; replace generic or irrelevant shots with the director's actual story treatment.
4. Copy render-time media and fonts into the local public assets area. Preserve provenance and hashes so the source of each copy can be checked. Avoid downloads during rendering.
5. Use frame-derived animation throughout. Keep scene registrations and reusable components editable. Read the renderer's actual manifest schema; do not invent prop names or assume unsupported features.
6. Build captions from the final measured word timings. Use concise semantic phrases, appropriate line lengths and aspect-ratio-safe positions. Check the opening, names, numbers, fast speech and reveal timing.
7. Add licensed sound cues and intelligible mixing. Keep source stems separate. Apply required reconstruction/disclosure labels at relevant moments without filling the story with internal production metadata.
8. Typecheck/bundle and inspect representative actual frames. Preview the narration with the timeline. Fix clipping, overlap, empty frames, unexplained static holds and continuity errors before export.
9. Prepare the audience-facing packaging draft now: exact title, description, credits, and optional real thumbnail path. Save it as data.packaging_draft so independent QA can review the actual final wording before delivery. The package agent assembles those approved values; it does not introduce new claims afterwards.

## Output contract

Required data.manifest_path points to the actual renderer props/manifest JSON and is listed in files. Required data.packaging_draft contains title, description and credits, plus thumbnail_path when a thumbnail exists. Production manifests must have demo false, the correct format/FPS/frame total, measured narration matching the accepted voice artifact and aligned captions. Convert positive seconds to frames with round-half-up, matching JavaScript Math.round. The narration may finish before the visual timeline when the tail is intentional.

Add renderer_project_path, entry_point, composition_id, asset_map, narration_copy_hash, edit_decisions, preview_paths and known_limits. Include the complete run-local source and assets needed to reproduce the edit.

## Completion and failure

An exported draft manifest is not a completed edit. Missing media, silent placeholder narration, unaligned captions, unresolved imports, unsupported props or a mismatched frame count blocks the stage.

Handoff to render with exact commands, project location, composition ID and assets.
