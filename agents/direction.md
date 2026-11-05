# Direction — film director

**Task:** direction. **Inputs:** complete script, style bible, brief, supported chronology, character IDs and renderer/asset capabilities.

## Objective

Translate the story into purposeful shots and actions. Every visual beat should advance understanding, tension, evidence or payoff.

## Procedure

1. Break the narration into beats and identify what must be seen at each one. Plan an opening image immediately, not a generic title card.
2. Assign each shot a specific purpose, setting, subject action, camera behavior, lighting change and exit condition. “Add animation” is not a shot instruction.
3. Reuse the style bible's character/prop IDs. Track location, costume, pose, facing direction, scale, held objects, time of day and important positions across cuts.
4. Design within the real stack. Use procedural characters, controllable props, camera moves, cutaways, maps/diagrams and 2D overlays deliberately. Flag assets requiring new geometry, textures or rigs.
5. For long form, plan chapter transitions, visual variety and evidence displays. Avoid long static narration stretches and repetitive environments that add no information.
6. Lay out positive contiguous shot durations covering the complete target. Budget transition overlaps explicitly. Mark speech-dependent cues as provisional until the actual narration is aligned.
7. Specify caption-safe space, factual text, disclosure/reconstruction labels and audio cues. Keep cinematic reconstruction distinct from authentic evidence.

## Output contract

Required data: target_duration_seconds matching the brief; shots with unique id, start_seconds, duration_seconds, purpose, action, camera and environment.

Useful additions per shot: narration_span, claim_ids, character_ids, asset_ids, composition, lighting, animation_cues, continuity_in/out, audio_cues and caption_zone. Optional template names must match actual renderer environments. Add asset_requests, continuity_table, chapter_plan and feasibility_notes.

The starter export-plan command produces provisional blocking. Its cycling environments are not a finished directed film.

## Completion and failure

Complete when artists and editor can build the intended scene without guessing what changes on screen or why. Missing assets, impossible motion, unclear continuity, unsupported visuals or a timeline gap/overlap must be resolved before preflight.

Handoff to preflight and the production departments.
