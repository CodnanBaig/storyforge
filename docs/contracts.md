# Artifact contracts and validation

`schemas/brief.schema.json` and `schemas/task-result.schema.json` define portable JSON structures. `storyforge/contracts.py` supplies executable semantic checks. Additional fields are welcome for rich production notes; required fields must keep their documented types.

## Result envelope

```json
{
  "schema_version": "1.0",
  "run_id": "the-actual-run-id",
  "task_id": "research",
  "status": "complete",
  "summary": "Concrete result and important limits",
  "data": {},
  "files": [],
  "sources": [],
  "warnings": [],
  "blockers": []
}
```

`complete` requires a passing task gate and no blockers. `blocked` requires at least one actionable blocker and does not unlock children. Files are nonempty files inside the run directory, named with relative paths. Traversal, absolute paths, and symlinks escaping the run are rejected. The coordinator calculates hashes; the agent does not get to assert a file exists by inventing its checksum.

Sources use `id`, `url`, `title`, `publisher`, `accessed_at`, and `independence_key`. Add excerpts, section locators, event/report dates, limitations, and archive links when useful. `accessed_at` is ISO 8601. Independent reporting groups matter; syndicated copies share an independence key. An independent reviewer still has to read and evaluate the sources.

## Required data by stage

| Task | Required `data` fields | Gate |
| --- | --- | --- |
| `discovery` | `candidates`, `selected_id` | At least 3 distinct candidates with title, angle and real source URLs; selected ID exists |
| `style` | `palette`, `font`, `characters`, `asset_rules` | Valid hex palette, explicit reusable visual rules |
| `research` | `claims` | ID, text, status and valid source IDs per claim; enough independent sources for factual work |
| `viability` | `score_components`, `recommendation`, `confidence`, `evidence` | Scores are subjective 0–5 or null; `go` to proceed; no unsupported reach guarantees |
| `script` | `hook_candidates`, `selected_hook`, `narration`, `claim_ids`; `chapters` for long form | Three hooks; chosen hook opens narration; fixed prefix preserved; claims exist; plausible word budget |
| `fact_check` | `approved`, `issues`, `verified_claim_ids` | All script claims covered; no unresolved issues |
| `direction` | `target_duration_seconds`, `shots` | Unique shot IDs; purpose, action, camera, environment; positive contiguous timings cover target |
| `preflight` | `approved`, `scope`, `checks` | Facts, originality, rights, disclosure and resources have passing evidence; intended use matches brief |
| `assets_3d`, `assets_images` | `assets`; `not_needed` when intentional | Actual files and rights per asset, or an explicit reason none are required |
| `voice` | `audio_path`, `duration_seconds`, `captions_path`, `provider`, `timing_source`, `hook_end_seconds` | Audio stream is real; measured duration and hook fit; alignment is actual; caption words are monotonic |
| `sound` | `music`, `sfx`; `intentional_silence` when no sound bed | Files and rights, or deliberate silence |
| `edit` | `manifest_path`, `packaging_draft` | Real production manifest, correct frame count, measured narration matching voice artifact, captions; exact title/description/credits drafted for review |
| `render` | `video_path`, `probe_path` | Actual encoded file has expected ratio, FPS, duration, pixel format, required audio |
| `qa` | `approved`, `checks`, `technical_report_path`, `reviewed_packaging` | Visual, audio, captions, facts, rights, originality and disclosure reviewed; technical report actually passes; exact metadata draft approved |
| `package` | `title`, `description`, `credits`, `delivery_files` | Actual verified film included; final title/description/credits and thumbnail match reviewed packaging |

Checks have the form `{"passed": true, "evidence": "What was inspected, where, and the result"}`. Evidence is a review record, not a mathematical proof of legality or quality. Save the actual screenshots, source notes and media reports the reviewer relied on when appropriate.

## Important nested types

- `claims`: `{id, text, status, source_ids}`. Status is `confirmed`, `reported`, `disputed`, `explained`, `unresolved`, or `fictional`. Fictional claims without sources are permitted only in an explicitly fictional brief. Real background facts still require sources.
- `score_components`: `demand`, `competition_gap`, `hook`, `visual_potential`, `source_quality`, `production_fit`. Unknown is `null`, not zero. The score is a prioritization rubric, not a view forecast.
- `shots`: `{id, start_seconds, duration_seconds, purpose, action, camera, environment}`. Optional `template` can choose a starter renderer environment. The director's textual camera plan can be richer than the starter camera enum.
- Asset records: `{id, path, rights}`. Add original source, creator, license URL, permission evidence, generator/model and version as appropriate.
- Narration word timing: `[{text, start, end}]` in seconds. `timing_source` is `forced_alignment`, `provider_alignment`, or `human_verified`. Estimated word timings cannot complete a real voice stage.
- `hook_end_seconds` is the actual aligned end of the selected opening, bounded by the narration and the agreed `hook.max_seconds`. A changed voice or model must also match any concrete choice saved in the brief.
- `packaging_draft` and `reviewed_packaging` contain `title`, `description`, `credits`, and optional `thumbnail_path`. The editor drafts them before QA. QA approves that exact object; the package stage copies it rather than introducing new claims after review.
- Sound records: `{path, rights}` with optional gain, offset, trim and attribution data.

## Budgets and authorization

`max_model_calls` caps subprocess worker starts and native dispatches made with `claim --model-call`. Native hosts must include that flag when delegating actual model workers. `max_media_jobs`, `max_media_cost_usd`, and `max_media_credits` cap reserved media requests. `max_retries_per_task` allows additional attempts after the first. The whole-run counters and past charges survive invalidation. The producer's own reasoning and provider-internal turns are not counted by the dispatch counter. Provider invoice costs and inner model usage can differ from known estimates.

No preflight record grants permission to purchase or publish beyond the user's actual request. A commercial review assesses the planned and actual rights; it is not a platform approval. A private preview does not silently become commercially cleared later.

## Drafts and fixtures

`storyforge demo` creates synthetic artifacts through direction and blocks at preflight. Its state is marked as a fixture. It does not call a model, search provider, voice service, or image generator. A fixture is not a researched episode. The renderer's demo manifest is similarly visible as a silent technical demonstration. Real runs reject fixture-tagged artifacts and draft edit manifests.

Frame conversion uses positive round-half-up (`floor(seconds * fps + 0.5)`), matching JavaScript `Math.round`. The visual timeline follows the brief. Measured narration may end earlier when a visual tail is deliberate; captions remain within the real narration.
