# Running StoryForge with Codex or Claude

StoryForge supports two ways to run the same pipeline. **Interactive host mode is the recommended starting point:** open the project in Codex or Claude Code, ask it to run StoryForge, and let the main conversation coordinate the specialist agents. **Subprocess mode** uses the installed CLIs as independent workers. Both modes use the same Python state store, role cards, dependency graph and acceptance gates.

The project does not require a new agent-platform subscription or a hosted backend. Model requests and connected media services still use your own accounts and their normal limits. Installation, authentication and service availability are separate from a successful local test.

## 1. Start in the project folder

Use Python 3.11 or newer and the Node version specified by the renderer. From the extracted project folder, check the local tools:

```bash
python3 -m storyforge doctor
```

Open that folder in your preferred coding agent. `AGENTS.md` is the shared operating guide; `CLAUDE.md` adds Claude routing. Project-scoped native worker definitions are already included. Allow the host to apply the project's normal trust controls; the library does not change your global configuration.

Use this first prompt:

> Start StoryForge for a new YouTube video. First ask for my niche, approximate duration, format, and references. Then clarify audience, language, hook style, voice and spending limits only where needed. Research candidate topics, recommend one with evidence, and run the production workflow with the specialist agents. Keep checkpoints and show concrete blockers.

For your mystery channel you might supply:

> The niche is documented mysteries and strange real events. Target about 43 seconds, 1080×1920 at 30 fps, English narration, no on-camera presenter. Use procedural Three.js story characters. I will provide visual references. Use a hook family with fresh wording for each episode. Start with research and a buildable storyboard; confirm the available narration service before any paid media work.

For long form, specify the intended duration independently of the Short. A ten-minute documentary needs a chapter plan, evidence for each chapter, varied shots and a complete narrative—not a repeated Short template.

## 2. Intake and state

The host can collect answers conversationally and write a valid brief, or you can use the terminal intake:

```bash
python3 -m storyforge intake --output brief.json
python3 -m storyforge init --brief brief.json --runs-dir runs
```

Retain the exact run directory printed by `init`. Substitute it for `RUN_DIR` in these examples:

```bash
python3 -m storyforge status RUN_DIR
python3 -m storyforge next RUN_DIR
python3 -m storyforge task RUN_DIR discovery
```

The brief records the niche, duration, format, references and creative decisions. It also records authorized services and limits. A sample brief has no authority to approve spending or publishing. References can be “none; propose a style,” but the host should ask rather than silently choosing a final brand identity.

Each worker receives a compact task packet plus paths to the relevant evidence. Large transcripts, source notes, asset registries and chapter drafts stay in files. This allows later agents to inspect them without copying the whole production history into every context.

## 3. Native specialist agents

The worker map is identical across hosts:

| Task | Codex agent | Claude agent | Responsibility |
| --- | --- | --- | --- |
| `discovery` | `sf_discovery` | `sf-discovery` | Candidate topics and distinct angles |
| `style` | `sf_style` | `sf-style` | Reference interpretation and style bible |
| `research` | `sf_research` | `sf-research` | Claims, sources and uncertainty |
| `viability` | `sf_viability` | `sf-viability` | Audience signals and reach assumptions |
| `script` | `sf_script` | `sf-script` | Hook and complete narration |
| `fact_check` | `sf_fact_check` | `sf-fact-check` | Independent script verification |
| `direction` | `sf_direction` | `sf-direction` | Shots, actions, continuity and assets |
| `preflight` | `sf_preflight` | `sf-preflight` | Readiness, originality, rights and resources |
| `assets_3d` | `sf_assets_3d` | `sf-assets-3d` | Procedural Three.js assets |
| `assets_images` | `sf_assets_images` | `sf-assets-images` | Approved generated or sourced visuals |
| `voice` | `sf_voice` | `sf-voice` | Narration performance and alignment |
| `sound` | `sf_sound` | `sf-sound` | Music, effects and mixing |
| `edit` | `sf_edit` | `sf-edit` | Remotion assembly and timing |
| `render` | `sf_render` | `sf-render` | Reproducible export and file measurements |
| `qa` | `sf_qa` | `sf-qa` | Independent review of the actual film |
| `package` | `sf_package` | `sf-package` | Verified delivery and publishing materials |

### Codex

Current Codex discovers standalone agent TOML files in `.codex/agents/`. Each included file defines a name, description and instructions, and points to the canonical role card. `.codex/config.toml` caps spawned threads at three. Models, permissions and connected tools follow the parent session. These definitions follow the [current official custom-agent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents), checked on 6 November 2026.

A host release may expose a different delegation tool or omit custom-role selection. In that case, the orchestrator gives a normal subagent the same `agents/TASK_ID.md` card and task packet. If delegation is unavailable entirely, it executes the roles sequentially and reports that fact. The artifact protocol remains unchanged.

### Claude Code

Claude workers live in `.claude/agents/`. The files use the [documented subagent frontmatter](https://code.claude.com/docs/en/sub-agents): a name, description, tools, inherited model and turn limit. Most workers have explicit tool lists. Media specialists inherit connected tools because provider names differ between installations. All workers exclude Agent/Task and are instructed not to delegate. No experimental agent-teams configuration is required.

Use the native agent loader if your version supports it; otherwise pass the role card to a normal subagent. Existing permission and organization controls still apply.

## 4. Claims, leases and handoffs

Only the main orchestrator changes shared run state. Before dispatching a worker it claims a ready task:

```bash
python3 -m storyforge claim RUN_DIR research --worker research-agent --model-call
```

The model-call flag reserves a worker launch against the run's invocation cap; omit it only for genuinely manual work that does not dispatch a model. The response contains the task's lease token, workspace, attempt, expiry and `prompt_path`. Pass that emitted prompt file to the worker: it names the exact attempt directory. The standalone `task` command is for inspection and may name the parent task directory instead. The orchestrator maintains the lease while the worker is running:

```bash
python3 -m storyforge heartbeat RUN_DIR research --token TOKEN --lease-seconds 1200
```

After receiving the real result file, it submits using that same token:

```bash
python3 -m storyforge submit RUN_DIR research --file RESULT_JSON --token TOKEN
```

Workers do not submit their own results. A valid lease does not make a bad artifact valid: the core checks the output structure, task semantics and files before advancing the graph. A stale worker cannot use an old token to complete a later attempt.

After an interruption, inspect `status`, then use `resume` to reclaim only expired leases. Use `retry` after a concrete blocker is resolved. If an accepted script or other upstream artifact changes, use `invalidate` so its descendants are recreated. Change the brief through `amend` while no workers are running. These commands preserve attempt budgets; editing state directly is not a valid recovery method.

## 5. Optional subprocess workers

First install and authenticate the desired CLI through its official instructions. `doctor` checks whether the executable is on `PATH`; it does not verify login, credits, connected tools or commercial media rights.

Start one provider per run invocation:

```bash
python3 -m storyforge run RUN_DIR --provider codex --workers 3
```

Or:

```bash
python3 -m storyforge run RUN_DIR --provider claude --workers 3
```

Do not run the subprocess coordinator against tasks already held by native agents. Separate runs may use different providers. The provider can also be changed between attempts when a task is no longer active; accepted artifacts remain the handoff contract.

The native orchestrator is also the broker for new paid-media requests. The subprocess runner has no interactive reservation callback and does not invoke the direct TTS helper automatically. A worker that needs a new paid request must return a blocked artifact with its proposed request and estimate. The native host retries and claims that stage, reserves within the existing authorization (or runs `tts`, which reserves internally), directs generation, reviews the output and submits the result. The subprocess workflow can then continue. Supplied recordings, existing assets and procedural work can proceed without this handoff when no new paid request is needed.

Every emitted worker packet includes only that task's current media ledger records: request fingerprint, provider ID, status, estimates/actual usage and saved file paths. They support reconciliation after interruption. They do not contain the original request body or grant permission to generate again; the orchestrator supplies the exact request file and any fresh-generation authorization separately.

The adapter passes prompts through stdin using an argument array, so reference text is not interpreted as shell code. It starts one worker per invocation and parses the provider's actual terminal result. Partial streams, error results, refusals without structured output and missing final messages fail the invocation. It never retries internally.

Codex uses its [documented non-interactive interface](https://learn.chatgpt.com/docs/non-interactive-mode), JSON events, schema-constrained output, a workspace-write sandbox and disabled recursive agents. Claude uses [print mode with structured output](https://code.claude.com/docs/en/headless), a maximum turn count and excluded delegation tools. No blanket permission allowlist, sandbox bypass or credential extraction is used.

The real artifact is transported inside a JSON string named `artifact_json`. This small wrapper avoids incompatibilities between providers' schema subsets. The adapter decodes it, then the Python core applies the complete StoryForge contract. The wrapper is a transport detail; saved stage artifacts use the normal envelope.

### Limits and accounting

The adapter's default wall-clock limit is 900 seconds per invocation. Its Python API accepts a different `timeout_seconds`. Claude also receives `max_turns`, default 20. Codex currently exposes no corresponding turn-count flag, so that argument cannot impose a Codex internal-turn limit. Use smaller task scopes and wall-clock bounds for expensive work.

The brief's model-call cap counts **worker launches**, not every internal model inference or tool request. Subprocess mode counts automatically; native dispatch must use claim's model-call flag. The host's main conversation and its internal tool/reasoning usage are not measured by that counter. Provider token usage and estimated cost are preserved when reported. An unknown cost stays unknown; it is never rewritten as zero. Neither a CLI estimate nor a preflight estimate guarantees a final bill. See the [Claude CLI reference](https://code.claude.com/docs/en/cli-reference) for provider-specific controls.

Each worker uses its own task directory. On macOS/Linux a timeout terminates its local process group. This does not cancel a job already submitted to a remote media service. Reconcile its provider job ID before approving another take.

## 6. Media-service handoff

An optional direct ElevenLabs adapter is included in `storyforge/voice.py`. Image generation, other voice providers and music services can use the host's connected tools. The transport does not invent APIs or substitute a voice provider. An unavailable provider is a specific blocked production task.

Before a paid request, the orchestrator reserves its exact request:

```bash
python3 -m storyforge reserve-media RUN_DIR voice --token TOKEN --key REQUEST_KEY --provider PROVIDER --request REQUEST_JSON --usd ESTIMATED_USD --credits ESTIMATED_CREDITS
```

It then records the actual provider ID and outcome using `record-media`. A timeout after submission is `uncertain`, not permission to start the same generation again. Reservation checks are application controls; connected tools must follow this protocol. They do not create a technical spending firewall around an independently authenticated service.

### Direct ElevenLabs helper

`synthesize(run, token, ...)` requires an active voice lease, a passed preflight, an approved brief selecting `elevenlabs`, an explicit voice ID, current cost/credit estimates and a locally configured `ELEVENLABS_API_KEY`. It defaults to the selected workflow's `eleven_multilingual_v2` model. It sends the accepted narration in one request to the [official speech-with-timing endpoint](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps).

The helper performs its own reservation. Do not pre-reserve the same key separately: a reused key intentionally refuses generation. It saves the request without credentials, real request ID, raw provider response and exact audio bytes before later processing. It measures audio with ffprobe and derives caption words from the provider's character alignment. It does not trim overlong narration, guess timestamps, or assume character counts are billed credits.

The returned envelope is a draft for normal `submit` validation, and a copy is saved as `media/voice-REQUEST_KEY/voice-result.json`. An unavailable key or decoder is detected before spending. A failed local read retains an uncertain reservation; `recover_saved_response(run, token, job_key=...)` can process already-saved bytes without a key or network call. An omitted provider ID, incomplete alignment or an overlong take blocks acceptance while preserving the audio.

This helper does not automatically split a long script into multiple billed requests. The voice director must plan and authorize chapters/chunks and assemble them through the host workflow when the chosen model's request limit requires that. The preserved character alignment also supports language-specific caption segmentation beyond the helper's whitespace grouping.

## 7. What has and has not been verified

The included adapter tests run real local subprocesses that imitate the CLIs. They cover both output formats, failed/partial results, missing tools, strict JSON decoding, timeouts including child processes, secret-log redaction and paths containing spaces. They consume no API credits.

Current Codex CLI help and official host documentation were inspected while building this version. A paid end-to-end Codex or Claude production was **not** run. The next real production must verify the local CLI version, account access, research tools, narration service, asset rights and renderer on the target computer. Use `python3 -m unittest discover -s tests -p test_adapters.py -v` to rerun transport tests.

Task directories and prompt instructions are not OS security boundaries. Claude's native permissions and any configured sandbox remain responsible for tool access; Codex's worker sandbox supplies its own controls. Diagnostic streams are bounded and redact recognizable secrets, but redaction is best effort. Inspect local diagnostics before sharing them.

## Troubleshooting

| Symptom | Next action |
| --- | --- |
| CLI not found | Install it from the provider's official instructions and ensure the executable is on `PATH`, or use interactive host mode. |
| Authentication or rate-limit error | Resolve it in the normal host account flow, retain the task checkpoint, then retry within the existing budget. |
| New permission required in unattended mode | Return to the interactive host and resolve the specific permission; do not add bypass flags. |
| No structured output or partial stream | Keep the stage incomplete and inspect local diagnostics; no downstream task should run. |
| Lease expired | Confirm the previous worker stopped, run `resume`, then claim a new attempt. |
| A provider job may already exist | Reconcile the saved job ID and reservation before requesting new media. |
| Native custom agent not discovered | Use a normal subagent with the same role card; consult the installed host's current documentation. |
| A schema or CLI flag is rejected | Check the installed version's help against the linked official docs; preserve the artifact contract when updating the transport. |
