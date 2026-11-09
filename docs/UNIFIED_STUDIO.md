# StoryForge Studio — unified production workflow

Profile: unified_studio_v1 | Host: Codex or Claude Code | Coordinator: StoryForge SQLite

This is the single production workflow combining StoryForge v0.2's durable state, provenance, policies and rendering with Codex Shorts Studio's evidence-led niche discovery, constrained visual choices, explicit owner approvals, local narration plan and creative/technical reviews. It is NOT a third controller, a hosted service, or a claim that a final audiovisual episode was produced.

## 1. Activation in a configured Mac project

Prerequisites: Python 3.11+, Node 22+, npm, ffmpeg/ffprobe, an authenticated Codex host with working research tools and authorized narration/asset capabilities. No OpenToonz, Friction or Synfig desktop app is required. Existing Kokoro can provide local TTS if its runtime is available. Blender remains optional for shots requiring authored 3D.

Install StoryForge once from its public repository using the existing installation guide, then configure a project:

    storyforge setup ./video-workspace --host codex
    cd video-workspace
    storyforge doctor

Prepare a brief from an existing valid example or from StoryForge's interactive intake. Set its constraints.workflow_profile to "unified_studio_v1" and save it as my-brief.json. The rest of the brief retains StoryForge's required audience, format, duration, content kind, release intent, hook and budget settings.

    storyforge start --brief my-brief.json
    storyforge status .storyforge/runs/ACTUAL_RUN_ID
    storyforge gates .storyforge/runs/ACTUAL_RUN_ID

Replace ACTUAL_RUN_ID with the directory printed by start. Start a Codex session in the project root and instruct it to read AGENTS.md and this guide in the installed toolkit (.storyforge/docs/UNIFIED_STUDIO.md), resume the existing run, dispatch only ready native worker tasks, and report the next human gate when reached. For an existing episode or channel, reuse approved project inputs and avoid repeating settled creative questions.

The Python CLI persists state, verifies handoffs and can manage subprocess workers; it does not independently browse the web, generate Kokoro audio, render new custom assets or approve creative choices. Those actions require the host and appropriate tools.

## 2. The four real human checkpoints

The niche, visual, script and final gates are stored with an accepted stage artifact hash, choice ID, evidence string and timestamp in StoryForge's SQLite run. Source edits or task invalidation revoke relevant approvals. Only a trusted human-facing host should issue approval commands after the owner explicitly chooses.

| Gate | Available after | What owner sees | Which work is blocked |
| --- | --- | --- | --- |
| niche | accepted discovery | at least 3 candidate IDs; sourced market evidence, premise, risk and feasibility | research and viability |
| visual | accepted style | 3 buildable looks, actually rendered proof still/clip, reference comparison and motion limits | direction |
| script | accepted script | exactly worded narration, hook options, factual support, final-payoff promise | preflight and all later production |
| final | accepted package and QA | real MP4, captions, claim ledger, rights and source evidence, QA report and metadata | delivery status until explicitly acknowledged |

Commands (only after actual explicit decisions):

    storyforge gates RUN_DIR
    storyforge approve-gate RUN_DIR niche --choice candidate-2 --evidence "Owner chose candidate-2 after reviewing options"
    storyforge approve-gate RUN_DIR visual --choice look-3 --evidence "Owner approved look-3 and viewed its proof"
    storyforge approve-gate RUN_DIR script --choice approve --evidence "Owner approved exact script text"
    storyforge approve-gate RUN_DIR final --choice approve --evidence "Owner watched final video and approved release package"

These are examples, not permission to run them. The CLI stores declared decisions and does not authenticate an individual. Production never auto-publishes; final approval is not authorization to upload unless independently granted.

The discovery selected_id is the scout's provisional preference. The niche gate decision is authoritative and can select any candidate ID. Research and viability must include data.selected_candidate_id matching the owner choice. A changed choice after downstream work began requires invalidating affected stages before repeating approval. This prevents quiet drift away from the selected premise.

## 3. Actual stages and evidence

| Stage | Agent responsibility | Required evidence |
| --- | --- | --- |
| 0: Intake and capabilities | Check saved channel profile, duration, aspect, language, format, rights, renderer and selected local tools | validated brief, working tool checks, no invented provider |
| 1: Niche discovery | Compare at least 12 niche clusters for a new channel when appropriate; or 3 episode angles for an established channel; sample recent 7/30/90-day videos where accessible | URLs, timestamps, visible observations, sampled limitations, candidate IDs |
| 2: Style discovery | Three deliberately different constrained aesthetics; build them in actual Remotion/Three.js/SVG rather than impossible photorealistic mockups | 3 stable concept IDs, real render proof files, palette, dimensions and constraints |
| 3: Source research | Verify user-selected angle, original/primary sources and current story resolution | claim ledger with independent source grouping and disputed/unknown markers |
| 4: Reach viability | Demand, competition gaps, differentiation, script/hook potential, production fit and source quality | six justified rubric dimensions; missing data stays null, not a view forecast |
| 5: Scriptwriting | Three distinct hooks, 40–45-second spoken Short where selected, one coherent arc, clear payoff and truthful framing | exact narration, selected hook, estimated reading pace, claim crosslinks |
| 6: Independent fact checking | Validate numbers, chronology, sources and visual implications | reviewer notes; BLOCK on central unsupported factual claims |
| 7: Direction | Storyboard from locked script, planned narration and approved style | scene purpose, visible actions, character/prop IDs, frames, camera, transitions and per-line timing |
| 8: Preflight | Validate rights, actual resources, originality and current YouTube rules, creative readability and budget | policy sources, source-linked checks and real checker results if creative-review profile is used |
| 9: Asset work | Reusable rigs, original props, maps, scene geometry, approved images and textures | local assets, inspectable render proof, identities, origin/rights ledger |
| 10: Voice and sound | Approved-script Kokoro or other authorized narration, word alignment, music and effects | actual audio files, measured duration, pronunciation and rights; no silent placeholders |
| 11: Edit | Film follows the audio, with independent character/scene motion rather than a slideshow | editable Remotion project, shot manifest, captions and exact packaging draft |
| 12: Render | Full MP4 from actual local assets using FFmpeg/Remotion; render samples first to control Mac resource load | video, duration/aspect/fps/audio streams and technical report |
| 13: Independent QA | Inspect whole Short audiovisually, opening hook, scene rhythm, transition, character movement, captions, fact interpretation and mix | frame/timecoded defect list, actual film hash, evidence of review |
| 14: Packaging | Assemble verified video, subtitle file, sources, rights, metadata, thumbnail, source project and QA reports | immutable reviewed deliverable set; never auto-upload |
| 15: Analytics learning | After authorized publication, compare meaningful 24h / 72h / 7d retention and conversion metrics, don't invent private figures | timestamped observations, hypotheses and suggestions for the next iteration |

These map onto the existing StoryForge sixteen-task graph and its supporting producer/reviewer roles. The phases above are operating concepts, NOT a second state machine. Only accepted artifacts in StoryForge state advance tasks.

## 4. Code-first animation, without separate desktop animators

Default layer stack: React SVG primitives and Remotion for deterministic 2D acting; Three.js for depth, procedural geometry, lighting and 3D camera work; FFmpeg for final media checks. The starter Actor2D module offers idle, walk, run, point, look, react and crouch actions with stable parameters: action, x_from, x_to, y, scale and facing.

A scene may optionally include:

    "actor_2d": {
      "action": "walk",
      "x_from": 0.12,
      "x_to": 0.65,
      "y": 0.75,
      "scale": 0.95,
      "facing": 1
    }

Frame timing is deterministic, so rendering frame 102 before frame 10 yields the same visual as rendering sequentially. The first SVG puppet is intentionally a simple reproducible character, not an automatic drawing/rigging engine. Reuse versioned character/prop/action IDs, but build new visual assets when the narrative needs them. Animating a whole image moving left/right is insufficient when the scene requires human interaction or a reveal.

PixiJS, GSAP, Rough.js and optional Blender may be considered after a proof shows they address a real unmet requirement. They are not mandatory dependency bloat. Any external service/asset requires explicit rights, capability and budget checks.

## 5. Quality checks and release decisions

The film's opening frame and first two seconds should immediately establish a specific tension, question or surprise. Every narrated beat should have corresponding visible action; preserve the payoff and avoid filler. Validate accurate captions, dialogue/number pronunciation, original authorship and non-repetitive montage content.

A successful script/creative rubric is an editorial readiness assessment, never a scientifically valid virality probability or guaranteed monetization. The bundled StoryForge factual Shorts creative-review checker must actually be executed by the host when the corresponding profile is selected; the Python submit path alone does not execute its Node checker.

QA must confirm the encoded MP4 visually and aurally. The review should cover the beginning, all important scenes, every factual on-screen element, transitions and ending. FFprobe metadata cannot establish that animation is emotionally effective or facts are true. Report any missing capability and block rather than fabricating success.

## 6. Resuming, cost and consistency

Only the StoryForge SQLite state store is authoritative; do not also run the standalone Codex Shorts Studio controller. Resume a stored run with status, next and the actual run directory instead of starting from scratch. Task leases prevent late workers from modifying a reassigned stage. File and upstream hashes are audited. Invalidating an upstream stage clears dependent results and corresponding human approvals.

Use existing installed tools where possible. Keep node_modules separate in the renderer workspace, preview reduced-resolution shots before full render, cap concurrent workers on a 16 GB Mac and preserve caches/assets unless the owner explicitly authorizes deletion. Do not claim zero-cost AI inference just because the visual renderer is free; Codex usage and optional third-party credits have their own limits.

A Short is complete only with a reproducible actual narrated and checked MP4 plus editable project, caption timing, sources, rights notes, credits, final metadata and independent QA evidence. Until then call it a prototype or blocked run. A normal ready-to-publish package is not a published video.

## 7. Verification boundary

The new code can be regression-tested offline: gate status, approval persistence and invalidation, style-proof file checks, manifest argument validation, and frame-derived actor source. These tests cannot confirm the quality of a full film. Before claiming end-to-end production readiness, run a real episode on the target Mac with working Codex, sources, Kokoro/audio and renderer, and have an independent reviewer watch and listen to the encoded result.
