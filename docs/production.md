# Production playbook

## Convert references into buildable rules

The art director extracts a palette, typography system, geometry style, proportions, material treatment, lighting, camera behavior, transitions, caption treatment, and a character/prop registry. Each rule needs a practical implementation in Three.js or Remotion. Separate the visible goal from the technique: a reference's soft atmosphere might become fog, a controlled palette and a slow light move without requiring cinematic fluid simulation.

Create a visual proof using actual scene code and representative rendered frames. Test a full body, face/silhouette, hand-held prop, environment scale, overlay text and a transition. Record any approximation. The initial proof establishes what this stack can actually reproduce before an entire film is built around it.

### Asset tiers

| Tier | Typical content | Production approach |
| --- | --- | --- |
| Procedural | Mannequins, buildings, rooms, trees, maps, arrows, simple vehicles and props | Parameterized Three.js primitives and exact vector/HTML overlays |
| Reusable model | A custom character, recognizable vehicle, complex object | Authorized local glTF/GLB with inspectable materials, scale and animation |
| Raster illustration | A detailed scene illustration or texture | Authorized generation/reference workflow with identity and rights records |
| Specialized | Facial acting, elaborate hair/clothes, fluid simulation, realistic crowds | Explicit extra asset/tool work and cost assessment before promising it |

The included renderer demonstrates the first tier with four scene factories. It is a starting vocabulary. The asset artist and editor extend it for each story instead of substituting an unrelated lighthouse, archive or forest for every niche.

## Director's shot plan

Every shot needs its narrative purpose, visible action, camera, setting, participants/props, text, sound cue, timing, claim IDs when factual, and continuity notes. The required machine contract is intentionally smaller; richer production fields belong beside it.

Prefer actions that can be rendered deterministically: a person turns toward a light, a door pivots, a chart reveals scale, a camera tracks past a foreground prop, a labeled timeline advances, or a beam exposes an object. Camera motion alone is rarely enough to make a scene meaningful. Use detailed shots where detail reveals evidence; use wide shots where geography or isolation matters.

Transitions have duration too. The pipeline's shot timeline is contiguous; include any overlap in the final accounting. A 45-second composition at 30 fps has exactly 1,350 frames. Do not accidentally add transition time outside that total.

## Asset production and integration

The 3D and image artists work in separate task folders against the same style bible and shot list. They deliver code or actual local files, a usage map, stable IDs, rights evidence, and a renderability check. The 3D artist records scale, material palette and polygon/texture considerations. The image artist records generation job IDs and the character/costume/location anchors used to preserve continuity.

The editor integrates task-local patches into a run-local renderer copy. Asset workers do not race to modify shared timeline code. Copy approved runtime assets into `public/` and reference them locally. Preserve original files separately from cropped, compressed or transformed copies. Do not use network-dependent media URLs in a final render if reproducibility matters.

## Voice acting

The voice director supplies pronunciation, emotional intent, pacing, pauses, stress and chapter continuity. Choose an authorized voice and record its actual provider ID and model. A reference voice is not permission to clone or impersonate it.

Generate the approved script with one planned take, then listen. Save the original file, provider ID, exact text and settings exposed by the selected API. Fix an actual omission, timing problem, pronunciation error or performance issue within the budget; do not generate indefinitely in search of an undefined improvement.

Measure the selected hook's end from actual alignment and save `hook_end_seconds`. If it exceeds the agreed limit, preserve any fixed phrase while revising the approved script or brief. The final reviewer checks this opening boundary in playback.

The optional ElevenLabs helper makes one approved-script request and preserves timing output from the provider. It requires the configured provider, a matching voice/model when the brief specifies them, preflight, a task lease and budget. It does not establish commercial rights. Native host connectors can be used through the same media-ledger procedure when the helper is not suitable.

For long form, plan chapter or paragraph takes with connective context and consistent settings. Measure every take. After assembling them, offset their alignments into the final audio timeline, verify the transcript, and remeasure the combined audio. Never reset timestamps to zero for every chapter in the final captions file.

## Sound and captions

Choose a specific licensed recording or original sound bed. Save source, license, creator, attribution, modifications and evidence. A title containing “no copyright” is not sufficient permission. Silence is acceptable when it is intentional and documented.

Keep music and effects beneath narration, use deliberate fades, and listen on small speakers as well as headphones when practical. A house starting target around −17 LUFS integrated with true peaks at or below −1 dBTP can guide a spoken mix; it is not a universal platform requirement or a substitute for listening. Measure the encoded output and preserve separate stems.

Captions come from the final voice track's actual alignment. Verify names, numbers, omissions, language-specific word boundaries and timing after any speed change or edit. Group short semantic phrases. Keep text clear of platform controls and important visual evidence. The starter renderer's safe zones are adjustable; inspect portrait and landscape separately instead of simply resizing the same layout.

## Deterministic animation

Use Remotion's current frame and video configuration for motion and timing. A random-access frame must look the same whether it is rendered first or after another frame. Seed procedural variation; avoid unseeded randomness, wall-clock timers, or simulation history. ThreeCanvas integrates Remotion's frame context with React Three Fiber; ordinary playback-only `useFrame` animation is unsuitable for deterministic export. [Remotion Three.js integration](https://www.remotion.dev/docs/three).

Use local fonts with known rights or a documented system stack. Font choice can change layout across machines. Preview the actual rendering environment and preserve any exact font files if their license allows it. Do not call a font “fixed” when it is a platform-dependent fallback.

## Review and delivery

Inspect real rendered frames at the opening, every scene boundary, the reveal and the ending, plus frames where text or action is dense. Then watch/listen to the encoded movie. Check no missing geometry, clipped text, identity drift, black frames, accidental UI, silent narration, wrong soundtrack, bad pronunciation, stale captions or unsupported implication.

Technical checks inspect the encoded duration, ratio, FPS, pixel format and audio stream. Independent editorial checks inspect the content. Review titles, thumbnails and description as well as the movie. Commercial permissions and required disclosures must reflect the actual final assets and account state at generation time.

Draft audience-facing metadata in the edit stage, before QA. The final packager assembles the exact reviewed title, description, credits and thumbnail; it cannot introduce a new claim after that review.

Deliver the MP4, captions, approved script, claim/source ledger, credits/rights notes, metadata, QA reports and an editable project with its local assets and lockfile. Distinguish `private_preview` from commercially cleared material. A completed package is prepared for an authorized upload; it is not evidence of an upload or platform approval.
