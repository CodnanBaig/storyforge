# Command-line guide

Run commands from the extracted project root using Python 3.11+. Optional editable installation provides a `storyforge` executable with the same arguments. Commands return JSON where practical. Exit `0` means the requested operation succeeded; exit `2` means invalid input, a blocked workflow, or a failed gate. An accepted blocked artifact still returns `2` because it does not complete production.

## Intake and initialization

```bash
python3 -m storyforge intake --output my-brief.json
python3 -m storyforge validate-brief my-brief.json
python3 -m storyforge init --brief my-brief.json --runs-dir runs
```

Intake asks about niche, documentary/fiction/commentary, duration, aspect ratio, audience, language, tone, references, opening style, voice, release intent, and media limits. It will not overwrite an existing brief. For noninteractive use, copy an example JSON and fill it in.

`init` prints the actual run directory. Replace `runs/RUN_ID` in the examples below with that value. The saved brief belongs to that run; later changes to the original template do not alter it.

## Native host orchestration

```bash
python3 -m storyforge next runs/RUN_ID
python3 -m storyforge claim runs/RUN_ID discovery --worker topic-scout --model-call
```

`claim` returns a lease token, expiry, fresh workspace, prompt file, and result template. Use `--model-call` for actual native worker dispatches so they consume the invocation budget; manual non-model work can omit it. Pass the emitted attempt-specific `prompt_path` and workspace to the specialist worker. Preserve the token in the producer's task record. Submit the completed JSON using the exact token:

```bash
python3 -m storyforge submit runs/RUN_ID discovery --token TOKEN --file runs/RUN_ID/tasks/discovery/attempt-1/result.json
python3 -m storyforge status runs/RUN_ID
```

A task can be claimed only after every dependency is complete. The producer can claim several ready tasks and delegate them concurrently. Each agent gets its own attempt directory and should never edit shared state or another worker's files.

For a long native task, refresh its lease before expiry:

```bash
python3 -m storyforge heartbeat runs/RUN_ID research --token TOKEN --lease-seconds 1800
```

`task RUN TASK` prints a current prompt without claiming the task. Use it for inspection or planning; a valid lease is still required to submit.

## Bounded subprocess execution

```bash
python3 -m storyforge run runs/RUN_ID --provider codex --workers 3 --timeout-seconds 900 --until preflight
python3 -m storyforge run runs/RUN_ID --provider claude --workers 3 --max-turns 20
```

Use one command with the provider you have installed and authenticated. The adapter checks for the executable on `PATH`; it does not log in, install the CLI, or discover credentials. `doctor` identifies availability. Web search and media capabilities must be available through that CLI's approved tools or configured MCP connections.

The default concurrency is three, and the allowed range is one to eight. The per-worker timeout is 30–7,200 seconds. `--model` optionally selects an explicit model already available to the provider. The library never assumes a particular paid tier. `--max-turns` constrains Claude; Codex has no equivalent exposed by this adapter, so its wall-clock timeout and invocation cap apply.

`--until preflight` includes the ancestors required for that task and stops there. Omit it to run the full graph. The coordinator continues independent work when one branch blocks, then returns the real saved state. It does not repeatedly retry a failed paid request. Correct the underlying problem, then use `retry` within the saved limits.

The subprocess runner does not broker new paid-media reservations while a worker is running. Such a worker returns a blocked result with the exact proposed request and estimate. Let the native host orchestrator handle that stage: retry and claim it, reserve the request (or use `tts`, which reserves internally), obtain and review the actual media, then submit its result. Resume the subprocess command after the native task is no longer active. New task packets include that task's recorded media job IDs, status, costs, request fingerprint and saved paths so a resumed worker can reconcile existing output. Those records are not authorization to repeat generation, and the coordinator must still supply the original request file when needed.

The JSON schema transport uses a single `artifact_json` string because model providers support different structured-output subsets. The adapter decodes it; the coordinator still validates the complete StoryForge envelope and task relationships.

## Recovery and revisions

```bash
python3 -m storyforge resume runs/RUN_ID
python3 -m storyforge retry runs/RUN_ID research
python3 -m storyforge invalidate runs/RUN_ID script --reason "Changed the opening and payoff"
python3 -m storyforge amend runs/RUN_ID --brief revised-brief.json
python3 -m storyforge events runs/RUN_ID
```

`resume` reclaims **expired** leases and preserves live workers. A late worker's token cannot overwrite a new attempt. Check provider job records before restarting any generation.

`retry` is for failed or blocked tasks. `invalidate` clears a stage and its descendants, revoking any running descendant leases; stop the old workers too, so they do not continue wasting resources. `amend` updates the run's brief and clears all stages; it refuses while tasks are running. Lifetime attempts and spending records survive all these operations.

If a completed referenced file changes, the coordinator reports its owning stage. Invalidate and resubmit deliberately. Do not edit the SQLite database to hide a mismatch.

## Media reservations and recovery

After a real preflight passes and the voice worker owns a lease:

```bash
python3 -m storyforge reserve-media runs/RUN_ID voice --token TOKEN --key narration-take-1 --provider elevenlabs --request voice-request.json --usd 0 --credits 600
```

The numbers above are syntax examples, **not a provider quote**. Supply real estimated usage and the approved credit/spend limits. Existing subscription credits still count as credits. Unknown cost is not zero. This command reserves a request; it does not contact a provider.

Once the provider accepts it, preserve its returned ID:

```bash
python3 -m storyforge record-media runs/RUN_ID --key narration-take-1 --status submitted --provider-job-id ACTUAL_PROVIDER_ID
```

If the request times out before a provider ID is returned:

```bash
python3 -m storyforge record-media runs/RUN_ID --key narration-take-1 --status uncertain
```

The reservation remains. Reusing its key returns the existing job with `may_generate: false`; it does not authorize another take. Retrieve the job through the provider. After its actual file is saved under the run:

```bash
python3 -m storyforge record-media runs/RUN_ID --key narration-take-1 --status complete --provider-job-id ACTUAL_PROVIDER_ID --file media/narration.mp3
```

Supply actual USD/credits with `--usd`/`--credits` only when known. The workflow retains estimates otherwise. File paths are relative to the run. Do not claim completion using a job ID alone.

## Optional ElevenLabs helper

Set `brief.voice.provider` to `elevenlabs`, choose the actual voice ID, and include any approved model ID in the brief before preflight. Keep your API key in the local environment under `ELEVENLABS_API_KEY`; do not put it in a brief, source file, or task output. The helper reads only the named variable and never prints its value.

Once the voice task is claimed, the producer can generate the **accepted script**:

```bash
python3 -m storyforge tts runs/RUN_ID --token TOKEN --voice-id ACTUAL_VOICE_ID --key narration-take-1 --usd 0 --credits 600
```

Replace usage numbers with verified estimates, as above. The helper reserves internally; **do not pre-reserve this key**. It submits one request, preserves response headers/bytes, saves the MP3 and original alignment, derives word timings from the provider's character timings, and measures the file with ffprobe. It writes a result draft under `media/voice-JOB_KEY/voice-result.json`. Review and submit that draft through the normal voice task handoff.

The helper refuses a replacement script that differs from the accepted script. Revisions go through script invalidation and the necessary checks. It does not select a voice, certify its rights, or assume that a character count equals billable credits. The current implementation uses the documented [speech-with-timing endpoint](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps).

When a valid response was saved but local processing failed, recover it without reading a key or making another request:

```bash
python3 -m storyforge recover-voice runs/RUN_ID --token TOKEN --key narration-take-1
```

If no response was received, inspect the provider's history. A missing or uncertain ID is not invented. Long-form chapter splitting, continuity between takes, final concatenation and global alignment are intentionally left to the voice director; this helper sends one accepted script per request and may be unsuitable for a script beyond the selected model's limit.

## Render planning, captions and encoded checks

```bash
python3 -m storyforge export-plan runs/RUN_ID --output draft.props.json
python3 -m storyforge srt words-final.json --output captions.srt
python3 -m storyforge qa-media final.mp4 --brief runs/RUN_ID/brief.json --output technical-qa.json
```

Draft export creates renderer props with `demo: true`. It is useful for blocking and should be visibly labelled. Its arbitrary starter environment fallback must be replaced when it does not match the story. It does not synthesize narration or captions.

SRT conversion expects already aligned words in seconds. It groups small phrases and preserves their measured boundaries. It does not infer timings from text. `qa-media` probes the encoded video for aspect ratio, FPS, duration, pixel format and audio presence. It does not establish intelligibility, absence of clipped speech, or synchronization by itself; the final reviewer must inspect and listen.

See the renderer's own README for preview, validation, stills, and explicit movie export commands.

## Offline verification

```bash
python3 -m storyforge doctor
python3 -m storyforge demo --runs-dir runs
python3 -m unittest discover -s tests -v
```

The demo uses synthetic offline artifacts, makes no model or media calls, and stops at preflight. It tests the workflow and handoffs, not editorial truth or reach. Tests use temporary files and fake CLIs; the media tests use a generated tiny fixture when FFmpeg is available.
