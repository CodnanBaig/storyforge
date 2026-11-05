# Command-line guide

Install the CLI using the [installation guide](installation.md), then run `storyforge` from your configured project or one of its subfolders. Project-aware commands find the nearest parent `storyforge.json`; `--project PATH` selects a different project where supported. Explicit input/output file arguments are relative to the directory where you run the command. Setup's `--keep-local` paths are always relative to the selected project root.

`setup` and `start` print concise summaries by default; add `--json` for their structured results. State commands, `info`, and `doctor` return JSON. Intake is interactive, and renderer commands stream npm/Remotion output. Exit `0` means the requested operation succeeded. Exit `2` indicates invalid input, a blocked workflow, or a failed gate; a failed renderer process can return its own nonzero status. An accepted blocked artifact still returns `2` because it does not complete production. For a Python virtual-environment or source installation, `python3 -m storyforge` accepts the same arguments.

## Project setup and diagnostics

```bash
storyforge setup ./my-video-project
cd my-video-project
storyforge info
storyforge doctor
```

`setup [DIRECTORY]` uses the current project when one is found in the current folder or its ancestors; otherwise it sets up the current folder. An explicit directory selects that location. Setup copies the bundled library and editable renderer, installs project-scoped native agents, adds managed sections to existing host instructions, and runs `npm ci` when renderer dependencies need installation. Existing app dependencies and unrelated project instructions remain intact. The full file set and upgrade behavior are described in [installation](installation.md).

| Setup option | Behavior |
| --- | --- |
| `--host both` | Add both Codex and Claude integrations; the default for new projects |
| `--host codex` or `--host claude` | Add only the selected integration |
| `--host none` | Set up resources without adding a host integration |
| `--skip-install` | Scaffold without running npm; rerun setup later to install |
| `--keep-local PATH` | Acknowledge a reviewed local version of a previously managed resource; repeat for each file |
| `--json` | Return the structured setup report, including file lists |

Reruns retain the project's current host selection unless `--host` adds an integration. `--host none` does not remove existing integrations. Setup checks for generated-file conflicts before writing. It preserves changed managed files and reports the paths that need review. A failed npm installation leaves the scaffold available for a later retry. Repeating setup reuses dependencies while the package/lock files and recorded install are current.

When an upgrade overlaps a customized resource, compare and merge the new toolkit changes first. Then acknowledge each file whose local contents you want to retain:

```bash
storyforge setup --keep-local .storyforge/renderer/src/StoryVideo.tsx
```

`--keep-local` preserves the file's exact local bytes and records the current packaged version as its reviewed upstream baseline. An ordinary rerun can then proceed; a later upstream change can produce a new conflict. Paths are project-relative even when setup runs from a subfolder. The option applies only to previously managed resource files, not unmanaged files, `storyforge.json`, the installation record, or managed instruction blocks. Keep custom host instructions outside those blocks. See the [upgrade guide](installation.md#upgrade-without-losing-project-changes) for a clean comparison workspace.

`info [--project PATH]` reports the installed package version, bundled resource location, and selected project's paths. `doctor [--project PATH]` checks the local Python/Node tools, renderer dependencies, and provider CLI availability. Neither command reads credentials or verifies a provider login.

## Start a saved production

```bash
storyforge start
# Or reuse a prepared brief:
storyforge start --brief my-brief.json
```

`start` combines intake and run creation. Without `--brief`, it asks the structured intake questions and saves the validated answers inside a fresh run. With `--brief`, it validates that file and uses its values without repeating the questions. The output includes the actual run directory; `--json` returns the complete structured state. `start` does not launch model workers; give the run to the native host or use the explicit `run` command below.

The configured project's runs directory is the default, normally `.storyforge/runs/`. Without a project, the default is `runs/` beneath the current directory. `--project PATH` selects a project and `--runs-dir PATH` chooses an explicit output location. A run created outside its selected project records the project location so later task packets still use the right toolkit and renderer. If that external run's originating project is no longer available, restore the project or move the run into a configured project before continuing.

### Separate intake and initialization

```bash
storyforge intake --output my-brief.json
storyforge validate-brief my-brief.json
storyforge init --brief my-brief.json
```

Intake asks about niche, documentary/fiction/commentary, duration, aspect ratio, audience, language, tone, references, opening style, voice, release intent, and media limits. It will not overwrite an existing brief. For noninteractive use, copy an example JSON and fill it in.

`init` creates a run from the existing brief and uses the same project-aware runs default; `--runs-dir PATH` overrides it. The saved brief belongs to that run; later changes to the original template do not alter it.

All examples below use `RUN_DIR` as a placeholder. Replace it with the exact directory printed by `start` or `init`, such as `/path/to/project/.storyforge/runs/ACTUAL_RUN_ID`.

## Studio, stills, and movie export

```bash
storyforge studio
storyforge studio --props draft.props.json
storyforge preview
storyforge preview --props draft.props.json --frames 148,478 --scale 0.5
```

`studio` starts the configured renderer's local Remotion Studio server and prints its URL. Open that URL yourself; the command does not launch a browser window. Stop the server with Ctrl+C.

`preview` renders actual PNG stills. Its default props are the bundled Short demonstration in the project's renderer. With no `--frames`, it selects a representative frame from each scene; `--frames` accepts comma-separated zero-based frame numbers. `--scale` defaults to `0.5` and must be greater than zero and at most one. The default output is a new directory under `.storyforge/previews/`; `--out DIRECTORY` chooses another destination, which must be new or empty. Inspect the verification JSON next to the images for the rendered frames and dimensions.

For a final production manifest:

```bash
storyforge render --props final.props.json --out delivery/final-v001.mp4
```

The renderer checks the manifest and local assets, measures actual narration, and refuses to overwrite an existing movie. A production manifest requires genuine narration and aligned captions. A silent technical demonstration needs explicit opt-in:

```bash
storyforge render --props .storyforge/renderer/examples/demo-short.json --out previews/demo-v001.mp4 --allow-demo
```

The demonstration remains visibly labelled. Rendering a file does not complete StoryForge's independent QA or packaging stages. These commands make no model or paid-media calls.

`studio`, `preview`, and `render` accept `--project PATH`. Props and output paths supplied explicitly resolve from your current directory, even when another project is selected. Asset paths inside the manifest still resolve under that renderer's `public/` folder. Read the [renderer contract](../renderer/CONTRACT.md) before authoring custom props. First-time rendering may need a browser download; advanced browser settings are in the [renderer guide](../renderer/README.md).

## Native host orchestration

```bash
storyforge next RUN_DIR
storyforge claim RUN_DIR discovery --worker topic-scout --model-call
```

`claim` returns a lease token, expiry, fresh workspace, prompt file, and result template. Use `--model-call` for actual native worker dispatches so they consume the invocation budget; manual non-model work can omit it. Pass the emitted attempt-specific `prompt_path` and workspace to the specialist worker. Preserve the token in the producer's task record. Submit the completed JSON using the exact token:

```bash
storyforge submit RUN_DIR discovery --token TOKEN --file RUN_DIR/tasks/discovery/attempt-1/result.json
storyforge status RUN_DIR
```

A task can be claimed only after every dependency is complete. The producer can claim several ready tasks and delegate them concurrently. Each agent gets its own attempt directory and should never edit shared state or another worker's files.

For a long native task, refresh its lease before expiry:

```bash
storyforge heartbeat RUN_DIR research --token TOKEN --lease-seconds 1800
```

`task RUN TASK` prints a current prompt without claiming the task. Use it for inspection or planning; a valid lease is still required to submit.

## Bounded subprocess execution

```bash
storyforge run RUN_DIR --provider codex --workers 3 --timeout-seconds 900 --until preflight
storyforge run RUN_DIR --provider claude --workers 3 --max-turns 20
```

Use one command with the provider you have installed and authenticated. The adapter checks for the executable on `PATH`; it does not log in, install the CLI, or discover credentials. `doctor` identifies availability. Web search and media capabilities must be available through that CLI's approved tools or configured MCP connections.

The default concurrency is three, and the allowed range is one to eight. The per-worker timeout is 30–7,200 seconds. `--model` optionally selects an explicit model already available to the provider. The library never assumes a particular paid tier. `--max-turns` constrains Claude; Codex has no equivalent exposed by this adapter, so its wall-clock timeout and invocation cap apply.

`--until preflight` includes the ancestors required for that task and stops there. Omit it to run the full graph. The coordinator continues independent work when one branch blocks, then returns the real saved state. It does not repeatedly retry a failed paid request. Correct the underlying problem, then use `retry` within the saved limits.

The subprocess runner does not broker new paid-media reservations while a worker is running. Such a worker returns a blocked result with the exact proposed request and estimate. Let the native host orchestrator handle that stage: retry and claim it, reserve the request (or use `tts`, which reserves internally), obtain and review the actual media, then submit its result. Resume the subprocess command after the native task is no longer active. New task packets include that task's recorded media job IDs, status, costs, request fingerprint and saved paths so a resumed worker can reconcile existing output. Those records are not authorization to repeat generation, and the coordinator must still supply the original request file when needed.

The JSON schema transport uses a single `artifact_json` string because model providers support different structured-output subsets. The adapter decodes it; the coordinator still validates the complete StoryForge envelope and task relationships.

## Recovery and revisions

```bash
storyforge resume RUN_DIR
storyforge retry RUN_DIR research
storyforge invalidate RUN_DIR script --reason "Changed the opening and payoff"
storyforge amend RUN_DIR --brief revised-brief.json
storyforge events RUN_DIR
```

`resume` reclaims **expired** leases and preserves live workers. A late worker's token cannot overwrite a new attempt. Check provider job records before restarting any generation.

`retry` is for failed or blocked tasks. `invalidate` clears a stage and its descendants, revoking any running descendant leases; stop the old workers too, so they do not continue wasting resources. `amend` updates the run's brief and clears all stages; it refuses while tasks are running. Lifetime attempts and spending records survive all these operations.

If a completed referenced file changes, the coordinator reports its owning stage. Invalidate and resubmit deliberately. Do not edit the SQLite database to hide a mismatch.

## Media reservations and recovery

After a real preflight passes and the voice worker owns a lease:

```bash
storyforge reserve-media RUN_DIR voice --token TOKEN --key narration-take-1 --provider elevenlabs --request voice-request.json --usd 0 --credits 600
```

The numbers above are syntax examples, **not a provider quote**. Supply real estimated usage and the approved credit/spend limits. Existing subscription credits still count as credits. Unknown cost is not zero. This command reserves a request; it does not contact a provider.

Once the provider accepts it, preserve its returned ID:

```bash
storyforge record-media RUN_DIR --key narration-take-1 --status submitted --provider-job-id ACTUAL_PROVIDER_ID
```

If the request times out before a provider ID is returned:

```bash
storyforge record-media RUN_DIR --key narration-take-1 --status uncertain
```

The reservation remains. Reusing its key returns the existing job with `may_generate: false`; it does not authorize another take. Retrieve the job through the provider. After its actual file is saved under the run:

```bash
storyforge record-media RUN_DIR --key narration-take-1 --status complete --provider-job-id ACTUAL_PROVIDER_ID --file media/narration.mp3
```

Supply actual USD/credits with `--usd`/`--credits` only when known. The workflow retains estimates otherwise. File paths are relative to the run. Do not claim completion using a job ID alone.

## Optional ElevenLabs helper

Set `brief.voice.provider` to `elevenlabs`, choose the actual voice ID, and include any approved model ID in the brief before preflight. Keep your API key in the local environment under `ELEVENLABS_API_KEY`; do not put it in a brief, source file, or task output. The helper reads only the named variable and never prints its value.

Once the voice task is claimed, the producer can generate the **accepted script**:

```bash
storyforge tts RUN_DIR --token TOKEN --voice-id ACTUAL_VOICE_ID --key narration-take-1 --usd 0 --credits 600
```

Replace usage numbers with verified estimates, as above. The helper reserves internally; **do not pre-reserve this key**. It submits one request, preserves response headers/bytes, saves the MP3 and original alignment, derives word timings from the provider's character timings, and measures the file with ffprobe. It writes a result draft under `media/voice-JOB_KEY/voice-result.json`. Review and submit that draft through the normal voice task handoff.

The helper refuses a replacement script that differs from the accepted script. Revisions go through script invalidation and the necessary checks. It does not select a voice, certify its rights, or assume that a character count equals billable credits. The current implementation uses the documented [speech-with-timing endpoint](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps).

When a valid response was saved but local processing failed, recover it without reading a key or making another request:

```bash
storyforge recover-voice RUN_DIR --token TOKEN --key narration-take-1
```

If no response was received, inspect the provider's history. A missing or uncertain ID is not invented. Long-form chapter splitting, continuity between takes, final concatenation and global alignment are intentionally left to the voice director; this helper sends one accepted script per request and may be unsuitable for a script beyond the selected model's limit.

## Render planning, captions and encoded checks

```bash
storyforge export-plan RUN_DIR --output draft.props.json
storyforge srt words-final.json --output captions.srt
storyforge qa-media final.mp4 --brief RUN_DIR/brief.json --output technical-qa.json
```

Draft export creates renderer props with `demo: true`. It is useful for blocking and should be visibly labelled. Its arbitrary starter environment fallback must be replaced when it does not match the story. It does not synthesize narration or captions.

SRT conversion expects already aligned words in seconds. It groups small phrases and preserves their measured boundaries. It does not infer timings from text. `qa-media` probes the encoded video for aspect ratio, FPS, duration, pixel format and audio presence. It does not establish intelligibility, absence of clipped speech, or synchronization by itself; the final reviewer must inspect and listen.

Use the project-level `studio`, `preview`, and `render` commands above, or see the renderer's README for lower-level validation and export controls.

## Offline verification

```bash
storyforge doctor
storyforge demo
```

The demo uses synthetic offline artifacts, makes no model or media calls, and stops at preflight. It tests the workflow and handoffs, not editorial truth or reach. It uses the configured runs directory by default; `--runs-dir PATH` selects another location.

To run the development test suite, use `python3 -m unittest discover -s tests -v` from a source checkout. Tests use temporary files and fake CLIs; the media tests use a generated tiny fixture when FFmpeg is available. They are not copied into each configured client project.
