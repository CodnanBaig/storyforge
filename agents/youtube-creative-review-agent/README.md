# YouTube Script and Creative Review Agent

A strict independent editor for **The Unquiet Index** and other original factual animated Shorts projects. It reviews a researched script and visual plan **before media production**, researches comparable YouTube videos, and returns **APPROVE, REVISE, REJECT or BLOCKED**.

The package contains an agent definition, research protocol, anchored scoring rubric, JSON input/output contracts, a dependency-free Node.js gate, integration example and tests. The gate is executable; the creative research is performed by the LLM agent and the web tools supplied by your project. No LLM provider, paid search service or account is silently configured.

## Add it to your project

1. Extract this folder into a dedicated location such as `agents/youtube-creative-review-agent/`. Preserve your existing project instructions.
2. Register `youtube-script-creative-review-agent.md` as the reviewer's system instructions. Load the rubric and research protocol as referenced context, or use `integration.example.mjs`, which includes them automatically.
3. Give this reviewer read-only web search/open and public YouTube metadata/video/transcript access as available. Pass owner-supplied analytics only when authorized. The reviewer must record inaccessible evidence honestly.
4. Map your episode record to `examples/input.template.json`. Fill the fields, supply a complete script/storyboard and source packet, and set `is_example` to false only for a real candidate.
5. Run the reviewer with the output schema in `schemas/review.schema.json`. Save the exact candidate and JSON report.
6. Run the deterministic check. Only a valid APPROVE proceeds to your existing policy, licensing and authorization gate.

### Local commands

Requires Node.js 18 or later. There are no npm dependencies to install. Run from this package directory:

```bash
node --test
node src/gate.mjs fingerprint candidate.json
node src/gate.mjs check candidate.json review.json
```

`fingerprint` returns the SHA-256 the host must provide to the reviewer. It does not approve anything. `check` exits **0 only for a current, valid creative APPROVE**; all other outcomes exit 1. Both `media_authorized` and `publication_authorized` stay false.

The supplied template and BLOCKED example intentionally cannot authorize a real episode:

```bash
node src/gate.mjs check examples/input.template.json examples/review.blocked.json
```

Expect a nonzero exit. This is a demonstration of a stopped handoff, not a current trend audit.

## Connect your existing orchestration

The supplied `integration.example.mjs` exports `reviewCandidate(candidate, { invokeAgent, tools })`. `invokeAgent` is the adapter you provide for your existing LLM/orchestrator. It must execute the supplied research tools and return the final structured JSON. This package does not assume a particular agent SDK.

```js
import { reviewCandidate } from './agents/youtube-creative-review-agent/integration.example.mjs';
import { assertCreativeApproved } from './agents/youtube-creative-review-agent/src/gate.mjs';

const { report, validation } = await reviewCandidate(candidate, {
  invokeAgent: project.runStructuredAgent,
  tools: project.readOnlyResearchTools,
});

await project.saveReview(candidate, report);

if (!validation.creative_approved) {
  // APPROVE with an invalid record also stops here.
  return project.routeReviewResult(report, validation);
}

// Recheck the current candidate immediately before the production handoff.
assertCreativeApproved(candidate, report);
await project.requireExistingPolicyRightsAndBudgetApproval(candidate);
// Detect any candidate edit made during the policy stage before production.
assertCreativeApproved(candidate, report);
await project.startMediaProduction(candidate);
```

The `project.*` methods are integration points in your application, not functions supplied by this package. Preserve the exact approved candidate as an immutable production input. A filename or episode ID alone is not enough to bind an approval to the script actually rendered.

### Routing rules

| Result | Pipeline action |
|---|---|
| APPROVE + valid gate | Send the exact reviewed version to existing policy/rights/budget review |
| REVISE | Return specific changes to the writer/storyboard agent, then submit a new version |
| REJECT | Stop this draft; select a supported new angle or another case |
| BLOCKED | Complete missing research, factual support or inputs; no media work yet |
| Malformed output or failed checker | Stop handoff and repair the review record; never assume approval |

Default to two revision cycles. A rewritten script is a new candidate, not an automatically approved attachment to an earlier critique. Do not treat missing evidence as proof a topic is weak.

## How strict it is

Approval requires **85/100**, with hook, payoff, visual storytelling and originality each rated at least **4/5** and no other criterion below **3/5**. All six mandatory checks must pass and no blocker or major issue may remain. Ratings need anchored reasons and evidence; a polished script cannot average its way past a factual or payoff failure.

The score covers demand, hook, clarity, narrative, payoff, visuals, originality, packaging, audio/captions and channel fit. It is **editorial readiness**, not a probability. This version deliberately requires numerical success probability and qualified-view forecast to remain null.

The review expires after 24 hours. Research observations used to approve must be within seven days of the review. Changes anywhere in the candidate invalidate its fingerprint. These are configurable-by-version project rules, not YouTube requirements; update the agent, schemas, gate and tests together if you change them.

## Trend research without misleading conclusions

`recent_trend` requires six relevant videos across three channels, within 90 days, including two within 30 days. `evergreen` permits a 180-day sample with two within 90 days. Both require at least two ordinary recent uploads, so the sample is not exclusively selected for exceptional performance. Counted comparisons must match the language and format and run between half the target minimum and 1.5 times its maximum. Declare the mode in the candidate before research.

The reviewer distinguishes public counts from qualifying views, compares age/format context, records counterevidence and cannot invent another channel's retention or conversion. Metadata-only inspection must not be described as watching the video. A sparse or inaccessible evidence packet produces BLOCKED rather than a fabricated trend forecast.

## Relationship to the existing Mystery Shorts workflow

Use this order: **research and draft → creative review → policy/rights/authorization review → production → actual-video QA and policy review**.

The existing policy review remains responsible for licensing, AI disclosure, advertiser suitability and authorized resources. Private noncommercial previews can still be eligible under that review. This agent never upgrades a preview to commercial clearance or approves publishing. It does not change the existing trial limit or schedule.

Runtime, sound and animation are planned at this stage. `timing.estimated_min_seconds` and `estimated_max_seconds` mean the estimated total screen time needed for narration, deliberate pauses and the ending hold, at plausible speaking speeds. The storyboard records the chosen export runtime. Explain the assumptions in `timing.method`; a voice-only duration is insufficient. A preproduction approval does not claim that ungenerated audio has been heard or that the final render has been inspected. Measure actual voice length and review the actual exported film later.

## What the code can and cannot check

The gate checks the recorded structure, rating arithmetic, decisions, evidence identity/freshness, required fields, timing plan and matching input fingerprint. It cannot independently prove that a source was read, a view count was accurately copied, a story is true, an asset is licensed, an editorial judgment is sound or YouTube will distribute/monetize the film.

Host-provided provenance and the reviewer's actual research are therefore essential. Keep evidence receipts where your research tools support them. Do not expose a self-certified JSON report as a verified audience prediction.

## Files

- `youtube-script-creative-review-agent.md` — complete agent instructions.
- `references/rubric.md` — anchored ratings and anti-inflation rules.
- `references/research-protocol.md` — sampling, verification and inference limits.
- `references/sources.md` — official platform guidance informing the design.
- `schemas/` — machine-readable candidate and review contracts.
- `src/gate.mjs` — deterministic checker and programmatic exports.
- `integration.example.mjs` — provider-neutral orchestration adapter.
- `examples/` — unfilled candidate and deliberately blocked review.
- `tests/` — synthetic contract tests; their data is not real trend evidence.

Version 1.0.0 · Prepared 6 November 2026.
