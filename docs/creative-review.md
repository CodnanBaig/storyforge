# YouTube script and creative review

StoryForge includes the portable [YouTube Script and Creative Review Agent](../agents/youtube-creative-review-agent/README.md). Use it for The Unquiet Index's 40–45 second factual mystery Shorts, or a compatible factual Shorts brief that selects this review workflow. It evaluates audience evidence, the script, the visual plan and packaging before media production.

The existing `preflight` worker performs the editorial review; the main host runs the executable checker. There is no additional pipeline stage or worker registration. The package is installed with the toolkit, normally at `.storyforge/agents/youtube-creative-review-agent/`, and needs no npm dependencies. StoryForge's Node 22+ prerequisite covers its runtime.

## Select the workflow

Tell the producer:

> Use the bundled YouTube Script and Creative Review Agent for The Unquiet Index. Follow TOOLKIT_ROOT/docs/creative-review.md during preflight. Review the exact factual script, scene plan and packaging against current YouTube evidence. Run the creative checker before completing preflight and recheck before production. Require both creative approval and the existing policy, rights and budget checks.

The channel's established brief already selects this workflow. For another project, record the selection in its project instructions or brief constraints. This is a host instruction, not a new CLI flag. Preserve the user's approved duration, hook mode, style and release intent. Do not apply the package's factual-source requirements or Shorts sampling rules to fiction, commentary or long-form work without an explicitly adapted review contract.

Read paths from the task packet: `PROJECT_ROOT`, `TOOLKIT_ROOT`, `RUN_DIR` and the claimed attempt workspace. A source checkout uses its own root as the toolkit; an installed project normally uses `.storyforge/`. Do not assume the shell's working directory.

## Prepare the exact candidate

Preflight already receives fact check, direction and viability, plus their upstream script, research and style artifacts. Map those accepted artifacts into the package's [candidate schema](../agents/youtube-creative-review-agent/schemas/input.schema.json). The [input template](../agents/youtube-creative-review-agent/examples/input.template.json) is deliberately incomplete and cannot approve a production.

| Candidate fields | StoryForge input and handling |
| --- | --- |
| `episode_id`, `channel` | Run identity and the actual channel brief. Do not invent a channel handle or audience data. |
| `constraints` | Approved duration bounds, ratio, visual stack and presenter preference. For The Unquiet Index, use 40–45 seconds and 9:16; the storyboard must also equal the run's chosen duration. |
| `research_brief` | Select `recent_trend` or `evergreen` before comparison research; explain audience fit and search seeds. |
| `script.text`, `script.claim_links` | Copy the accepted narration exactly and link factual claims to read sources. Preserve any selected fixed hook. |
| `creative.storyboard` | Map accepted shots: `end_seconds = start_seconds + duration_seconds`. Include concrete visuals/actions and assign the exact spoken words to each scene. Concatenated scene narration must equal the script. |
| Remaining `creative` fields | Proposed title, description, opening frame, payoff, style, sound and captions. Obtain missing creative decisions from the writer/director; do not invent an already approved plan. |
| `sources` | Map `independence_key` to `origin_key`; include actual access time, read confirmation and evidence notes. |
| `recent_episodes`, `channel_analytics` | Use supplied records. Mark analytics unavailable when absent; public competitor counts do not reveal private retention. |
| `rights_context` | Preserve the brief's release intent and the planned rights/provider context. Creative approval grants no license or spending authority. |

Write the completed candidate as `creative-input.json` in the claimed workspace. Set `is_example: false` only for a real candidate. Preserve the accepted inputs; material edits must return through coordinator invalidation and upstream revision.

## Run the independent review and checker

1. The orchestrator fingerprints the saved candidate before review.
2. The preflight worker reads the package's main agent instructions, anchored rubric and research protocol. Supply the computed fingerprint and current time as host context. Give it the host's authorized read-only research tools; a provider connection is not bundled.
3. The worker saves `creative-review.json` using the package's review schema. The report must distinguish observed evidence from inference and record inaccessible material honestly. Missing material evidence means BLOCKED.
4. The orchestrator executes the checker and saves its actual JSON output as `creative-validation.json`. Only exit code 0 and `creative_approved: true` permit this creative handoff. Do not substitute a worker's assertion for execution.

Run these commands **from `TOOLKIT_ROOT`**, replacing the absolute candidate/report paths with those from the task workspace:

```bash
node agents/youtube-creative-review-agent/src/gate.mjs fingerprint /absolute/path/to/creative-input.json
node agents/youtube-creative-review-agent/src/gate.mjs check /absolute/path/to/creative-input.json /absolute/path/to/creative-review.json
```

The native Claude preflight worker does not have a shell tool, so the orchestrator runs these commands. Both native host wrappers already read the canonical preflight role card. A custom model adapter can instead use the package's [integration example](../agents/youtube-creative-review-agent/integration.example.mjs); its `invokeAgent` implementation and research tools are supplied by the host.

Approval requires at least 85/100, specified minimum criterion ratings, all six mandatory gates, sufficient fresh comparison evidence, a matching candidate fingerprint and no major issue or blocker. The approval expires after 24 hours. These are project editorial rules, not YouTube distribution guarantees. The report's success probability and qualified-view forecast remain null.

## Keep the StoryForge envelope

The creative report is a separate document; it is not a replacement for StoryForge's task result. Preserve the normal preflight envelope with `task_id: "preflight"`, its run ID, status, summary, data, files, sources, warnings and blockers.

Before the orchestrator submits a complete result:

- Declare the candidate, report and actual validation output in `files`, using run-relative paths inside the claimed workspace. Include them in the reviewed-artifact record.
- Record the creative decision, candidate fingerprint, score and checker outcome in `data.creative_review` as supplemental evidence. Do not record an unexecuted check as passed.
- Complete the existing facts, originality, rights, disclosure and resources checks with evidence. Keep `scope` equal to the release intent and honor the authorized budget.
- Recheck the exact candidate immediately before production, including after policy review. An expired approval or any change to the candidate stops the handoff until reviewed again.

**Enforcement boundary:** the Node checker is executed by the host/orchestrator. `storyforge submit` does not execute it, and adding a `creative_review` field does not create a new Python acceptance rule. The host must withhold successful preflight submission and media dispatch when this selected workflow has not passed. Python continues to enforce its existing task, dependency, evidence, scope and budget contracts.

Complete this profile's preflight through the native host's claim/task/submit workflow, or a custom orchestrator that actually runs the checker. The stock subprocess `storyforge run` runner automatically submits worker outputs and has no Node-check callback. Running it unattended, including with `--until preflight`, does not enforce this additional creative gate.

| Creative result | Host action |
| --- | --- |
| Valid APPROVE | Continue the existing policy/rights/resources preflight; only complete preflight when all requirements pass. |
| REVISE | Return concrete changes to the writer/director. Invalidate accepted stages through the coordinator, then review the new candidate. |
| REJECT | Stop this draft and choose a supported new angle or topic. |
| BLOCKED, malformed report or failed checker | Preserve the reason in a blocked StoryForge result; resolve missing inputs or evidence before media work. |

Do not edit accepted artifacts in place to bypass invalidation. A proposed rewrite attached to a critique has not itself passed review. The later voice stage still measures actual narration; final QA still inspects the encoded film, captions, audio, facts, rights and exact publishing metadata.

## Verification

From a source checkout, `make test-review-agent` runs the package's synthetic gate and adapter tests without provider calls. From an installed toolkit, run `node --test` inside `agents/youtube-creative-review-agent/`.

The Python setup regression and `scripts/verify_distribution.py` check that the nested reviewer resources survive packaging and installation into an existing project. These tests verify software contracts and resource delivery; they are not a live YouTube trend audit or an end-to-end media production.
