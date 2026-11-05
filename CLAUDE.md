# StoryForge in Claude Code

In a configured project, follow its StoryForge entry point at `TOOLKIT_ROOT/WORKFLOW.md`, normally `.storyforge/WORKFLOW.md`, then the toolkit's canonical `AGENTS.md`. Use `storyforge info` to resolve the configured paths. In the source checkout, follow the root `AGENTS.md` directly. Preserve all other project instructions. This file adds Claude-specific routing; it does not replace the shared production rules or artifact contracts.

## Orchestrator

The main conversation coordinates StoryForge. Run `storyforge info`, read `docs/agent-hosts.md` beneath the returned toolkit root, and use the CLI as the authority for readiness, leases, budgets and acceptance. Ask only for missing intake answers. A user can say:

> Start StoryForge using .storyforge/WORKFLOW.md. Ask for my niche, duration, format and references, then run the production workflow. Keep me informed at major creative decisions and concrete blockers.

## Native subagents

Project workers are defined in the project root's `.claude/agents/`. Their names begin with `sf-`; their matching canonical role cards live in `TOOLKIT_ROOT/agents/`. The claimed task packet identifies `PROJECT_ROOT`, `TOOLKIT_ROOT`, `RENDERER_ROOT`, and `RUN_DIR`. Delegate one claimed, ready task per worker with that packet, its exact output scope, and relevant dependency artifacts. Limit active workers to three by default. The orchestrator owns lease heartbeats and submissions.

Each worker returns the JSON envelope and creates its task's files. It must not call the shared state CLI or recursively delegate. Native subagents inherit the session's permission controls; their prompts and separate contexts are not filesystem sandboxes. If a tool needs an ungranted permission or unavailable service, keep the artifact blocked and return the missing requirement.

Most roles have explicit tool allowlists. Voice, image and sound workers inherit connected tools because provider names vary; they still may use only an approved media reservation. No API credentials belong in prompts or artifacts. Default models follow the parent session. Use the user's model preference when provided.

Use normal subagents with the same role cards if this Claude version cannot load custom definitions. Use sequential roles if no delegation tool is available, and state that limitation. Do not guess host tool names.

## Optional subprocess mode

`storyforge run RUN_DIR --provider claude --workers 3` uses independent CLI processes instead of native subagents. Do not start it while native agents hold the same tasks. This mode requires a locally installed, authenticated `claude` CLI. It does not install or authenticate the CLI or automatically grant tools permission.

The adapter uses structured output and a turn limit, removes the Agent/Task tools, and preserves permission settings. The scheduler handles dependencies and returns failed or blocked stages; the main host arranges any permitted retry. New paid-media requests need the native orchestrator's reservation handoff because the subprocess runner has no interactive media broker. See the toolkit's `docs/agent-hosts.md` for costs, isolation and troubleshooting.
