# Architecture and extension

## One producer, many specialized workers

The producer owns the brief, state machine, task allocation, and integration. Workers own task-local output folders and return a JSON envelope. Both native host delegation and the optional subprocess executor use the same SQLite state. This avoids two disconnected workflows where the interactive host claims completion but the CLI cannot resume it.

The installed coordinator defines the graph; its source is `storyforge/pipeline.py`. Producers inspect readiness through `storyforge status` and `storyforge next`, so an initialized client project does not need a copy of the Python source. Sixteen roles are primary tasks. The producer and post-publication analyst are supporting roles. The graph permits parallel work, but exact concurrency depends on the host's capacity; having sixteen roles never means sixteen simultaneous processes are required.

| Layer | Responsibilities | Source |
| --- | --- | --- |
| Distribution | Bundled resources for normal and editable installations | `resources.py`, package build configuration |
| Project | Discovery, contained paths, safe resource and host setup | `project.py`, `scaffold.py` |
| Brief | User inputs, defaults, reuse, validation | `intake.py`, `contracts.py` |
| Graph | Dependencies, ready nodes, descendants | `pipeline.py` |
| State | Leases, history, fingerprints, media ledger | `store.py` |
| Host worker | Scoped context, role and result packet | `prompts.py` |
| Model transport | Codex/Claude subprocesses and structured output | `adapters.py` |
| Coordinator | Bounded concurrent task launch | `runner.py` |
| Media | Actual streams, duration, aligned subtitles | `media.py`, optional `voice.py` |
| Renderer bridge | Draft blocking from approved shot structure | `render_bridge.py` |
| Video | Geometry, frame-based animation, sound, layout | `renderer/` |

## Installed package and project resources

The Python package is named `storyforge-video` and exposes the `storyforge` executable. Its runtime uses the standard library. A normal wheel includes the non-Python production resources beneath `storyforge/_resources`; the build copies them from the repository's canonical asset folders. An editable developer install resolves those canonical folders directly. Generated caches, node dependencies, production runs, and credentials are excluded from the distribution.

`storyforge setup` creates a client project's `storyforge.json` and copies the toolkit beneath `.storyforge/`. The renderer is a project-owned npm workspace inside that directory. Its package and lockfile are independent of a React or Next.js application's root dependencies. Python package installation does not run npm or install host CLIs; setup handles renderer dependencies unless `--skip-install` is selected.

`storyforge info` reports the selected project and all resolved paths. Project discovery walks upward for `storyforge.json`. Task packets carry `PROJECT_ROOT`, `TOOLKIT_ROOT`, `RENDERER_ROOT`, and `RUN_DIR` explicitly, so a worker can read the appropriate local role card and renderer even when the Python package lives elsewhere. A run created at an external output location retains its originating project in saved metadata. Moving it beneath a configured project selects that new project; a missing external origin raises a recovery error. Standalone runs without a project can still use the installation's bundled resources. Mutable production files belong in the selected run or project, not in the installed package.

Setup records managed file hashes in `.storyforge/installation.json`. A rerun can refresh an owned file only when doing so preserves local changes; conflicting unmanaged or edited files require review. Host instructions are added in managed sections while surrounding text remains intact. Existing host settings are preserved, and setup does not alter global host configuration. Writes reject paths escaping the project and symlink redirects. These checks prevent accidental replacement of application code during ordinary setup; they do not sandbox later model workers.

Upgrading the CLI and updating a project's copied toolkit are separate operations. An upgrade makes a newer bundled library available; rerunning setup applies eligible changes to that project. Current runs retain their state and artifacts. Custom renderers, role cards, and instructions stay visible for deliberate merge decisions.

## Files and authority

A run contains `brief.json`, `state.sqlite3`, `tasks/`, `artifacts/`, `media/`, `delivery/`, and `logs/`. SQLite is the authoritative state. Each accepted artifact is also saved as a readable JSON snapshot. The canonical snapshot includes its input fingerprint and the hashes of files it references. A previously accepted file changing on disk blocks new work until the responsible stage is invalidated.

Each claim returns a token, expiry, and fresh `tasks/TASK/attempt-N/` directory. A worker writes only there. The producer submits its result with that token. Stale tokens cannot complete a reassigned task. Long-running native workers must heartbeat or claim a sufficiently long bounded lease. The subprocess coordinator sets a lease longer than its wall-clock timeout.

These folders and tokens coordinate trusted local agents. They are not an operating-system security boundary. Agents must retain the host's normal permissions and avoid unrelated files. Run potentially untrusted third-party code only in a separate sandbox or container appropriate to your environment.

## Dependency invalidation

Changing a research conclusion can alter the script, narration, captions, shots, edit, and final package. `invalidate research` therefore clears research and all its descendants, while preserving unrelated style work. Changing the brief through `amend` clears the entire graph. Old snapshots remain for diagnosis and comparison. Attempts, worker invocation counts, and media expenditure are retained so revisions cannot silently reset budgets.

The current implementation fingerprints all accepted files before claiming or submitting more work. For very large projects this may become expensive. A future content-addressed object store could reduce repeated reads. Do not remove integrity checks without replacing their guarantees.

## Media ledger and uncertain requests

Reserve a distinct, descriptive job key before generation. The reservation includes a hash of the provider request and its estimated cost/credits. Reusing a key for the same request returns the existing job and prohibits another generation. Reusing it for different content is rejected.

Record the actual provider job/request ID as soon as it is available. If a request times out before an ID arrives, mark it uncertain with no invented ID. Its budget stays reserved. Recover it from the provider's job history before deciding on a corrective take. A new job key is not a substitute for checking an uncertain request.

The ledger enforces limits for calls made through it. An agent issuing an unrelated API request outside the workflow is outside this enforcement. Review tool permissions and provider-side quotas when running unattended. Estimates are not guaranteed invoice amounts; reconcile actual charges when known. The code never turns unknown charges into zero.

## Long-form production

Keep a single story bible and asset identity registry, then divide the film into chapters with explicit rhetorical purposes. Section-level voice takes can be revised independently. Preserve the order and IDs of takes, the silence between them, and their measured offsets. After concatenation, transform each word's local alignment into the film's global timebase. Verify the final audio duration and transcript before locking the edit.

The coordinator currently treats voice and edit as one task each; the assigned host can manage chapter-level subtasks inside the task workspace. A future implementation can expand chapters into graph nodes for distributed work. Do not present this future expansion as already implemented. The single-request TTS helper deliberately does not cut text automatically at arbitrary character counts.

Render stills and short scene ranges to evaluate the design before an expensive full export. For very long 3D films, choose renderer concurrency to fit RAM and GPU capability and consider chapter renders. The included generic manifest remains deterministic across random-access frames.

## Add a role

1. Add a unique `Task` and dependencies to `pipeline.py`; check for a cycle and identify its invalidation path.
2. Add the role card to `agents/`, then native wrappers to `.codex/agents/` and `.claude/agents/`.
3. Specify its result shape and semantic gate in `contracts.py`; update `scripts/build_contracts.py` and regenerate public schemas.
4. Add a realistic failure and recovery test. Avoid a test that merely repeats the implementation.
5. Start new runs with the revised graph. Existing runs do not silently migrate task definitions in this release.

## Add a provider

Add a narrowly scoped helper with an explicit callable interface. It must check credentials without printing them, validate user intent and the approved script, reserve before making a paid request, preserve provider IDs and original response/media, handle timeout without automatic regeneration, and return actual artifacts. Test the transport using fakes before an authorized live run. Keep provider model identifiers in the brief/config, not as assumed universal defaults.

## Add visual assets or scenes

Use the renderer's character palette/proportions and stable IDs as the continuity contract. Add reusable geometry or scene factories to its registry. A scene gets time from Remotion's current frame; an arbitrary render frame must not depend on prior playback. Do not animate with wall-clock timers, mutable simulation history, or unseeded randomness.

The editor integrates asset-agent patches into a run-local renderer copy, uses local public assets, then validates and renders it. Multiple workers never edit the same `Root.tsx` concurrently. Keep source and resulting media in the delivery package so a scene can be revised without recreating the whole episode.
