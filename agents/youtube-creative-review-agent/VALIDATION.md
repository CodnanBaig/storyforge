# Validation record

Version 1.0.0 · 6 November 2026

**18 of 18 automated tests passed:** 15 deterministic-gate tests and 3 orchestration-adapter tests. Runtime inspected: Node.js v24.22.1. The package uses Node built-ins and declares Node.js 18 or later; other runtime versions were not separately exercised.

Command: `node --test`

## Verified behavior

- A complete synthetic approval record passes only creative handoff; media and publication authorization remain false.
- Empty templates and malformed or missing review output cannot approve an episode.
- Weighted totals, critical rating floors, unresolved major issues and failed mandatory checks are enforced.
- Reviews are tied to the complete candidate fingerprint, including script, storyboard, packaging and rights context.
- Stale approvals and stale comparison observations are rejected for handoff.
- Recent-trend and evergreen windows, channel diversity, ordinary comparison observations and comparable durations are checked.
- Numerical success probabilities and qualifying-view forecasts are rejected by this version's contract.
- Invalid source URLs and unresolved evidence references produce a denial rather than an accidental approval.
- The storyboard narration must match the script and the estimated total required runtime must fit the chosen storyboard end.
- CLI commands produce JSON and meaningful exit codes.
- The integration adapter supplies instructions, rubric, protocol, schema and input fingerprint, preserves a request snapshot, detects caller changes during review and rejects malformed model output.

## Scope of the tests

The approval fixtures contain explicitly artificial observations and source declarations for testing record consistency. They are not actual researched videos, editorial approvals or predictions. They are not delivered as usable production candidates.

The tests did not call an LLM, retrieve live YouTube data, generate media or spend service credits. A project must supply its existing agent/model adapter and research tools. Live tool access and model-backed editorial quality require evaluation in that connected project.

The checker cannot independently prove source truth, actual viewing/reading, accurate copied metrics, originality, licensing or eventual YouTube outcomes. Those judgments remain part of the independent research/editorial review and the separate policy stage.
