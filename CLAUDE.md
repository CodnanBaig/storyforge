# StoryForge in Claude Code

Follow the project workflow in `AGENTS.md`. This file adds Claude-specific routing; it does not replace the shared production rules or artifact contracts.

## Orchestrator

The main conversation coordinates StoryForge. Read `docs/agent-hosts.md` and use the Python CLI as the authority for readiness, leases, budgets and acceptance. Ask only for missing intake answers. A user can say:

> Start StoryForge. Ask for my niche, duration, format and visual references, then run the production workflow. Keep me informed at major creative decisions and concrete blockers.

## Native subagents

Project workers are defined in `.claude/agents/`. Their names begin with `sf-`; their matching canonical role cards live in `agents/`. Delegate one claimed, ready task per worker. Include its project root, task packet, exact output scope and relevant dependency artifacts. Limit active workers to three by default. The orchestrator owns lease heartbeats and submissions.

Each worker returns the JSON envelope and creates its task's files. It must not call the shared state CLI or recursively delegate. Native subagents inherit the session's permission controls; their prompts and separate contexts are not filesystem sandboxes. If a tool needs an ungranted permission or unavailable service, keep the artifact blocked and return the missing requirement.

Most roles have explicit tool allowlists. Voice, image and sound workers inherit connected tools because provider names vary; they still may use only an approved media reservation. No API credentials belong in prompts or artifacts. Default models follow the parent session. Use the user's model preference when provided.

Use normal subagents with the same role cards if this Claude version cannot load custom definitions. Use sequential roles if no delegation tool is available, and state that limitation. Do not guess host tool names.

## Optional subprocess mode

`python3 -m storyforge run RUN_DIR --provider claude --workers 3` uses independent CLI processes instead of native subagents. Do not start it while native agents hold the same tasks. This mode requires a locally installed, authenticated `claude` CLI. It does not install or authenticate the CLI or automatically grant tools permission.

The adapter uses structured output and a turn limit, removes the Agent/Task tools, and preserves permission settings. The scheduler handles dependencies and returns failed or blocked stages; the main host arranges any permitted retry. New paid-media requests need the native orchestrator's reservation handoff because the subprocess runner has no interactive media broker. See `docs/agent-hosts.md` for costs, isolation and troubleshooting.
