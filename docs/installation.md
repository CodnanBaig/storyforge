# Install StoryForge in your projects

Install the CLI once, then run `storyforge setup` in each project where you want to make videos. Your project gets its own editable renderer, production library, and saved runs. The installed Python package supplies the coordinator and a complete copy of the starter resources.

## 1. Install the CLI

You need Python **3.11 or newer**, Git, and pipx. On macOS, the [official pipx instructions](https://pipx.pypa.io/latest/how-to/install-pipx.html) use:

```bash
brew install pipx
pipx ensurepath
```

Open a new terminal so the updated `PATH` is available, then install StoryForge:

```bash
pipx install git+https://github.com/CodnanBaig/storyforge.git
storyforge --version
```

The GitHub repository is public; this HTTPS install does not need a GitHub token. Pipx keeps the Python application in an isolated environment and exposes the `storyforge` command. Git must be on `PATH` for [pip's Git URL installation](https://pip.pypa.io/en/stable/topics/vcs-support/).

The Python distribution is named **`storyforge-video`**. It is installed from this repository; no package with that name has been published to PyPI or npm by this project. Role cards, schemas, templates, examples, host definitions, renderer source, fonts, and the renderer lockfile are included in the installation. A retained source checkout is unnecessary for ordinary use.

### Use a virtual environment instead

If you prefer a per-project Python environment:

```bash
mkdir my-video-project
cd my-video-project
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install git+https://github.com/CodnanBaig/storyforge.git
storyforge setup
```

Activate that environment before subsequent `storyforge` commands. On Windows PowerShell, the activation command is `.venv\Scripts\Activate.ps1`. An editable install is only needed when developing StoryForge's own Python source.

## 2. Set up a project

Install Node **22 or newer** with npm before normal setup. To create a new workspace:

```bash
storyforge setup ./my-video-project
cd my-video-project
```

To use an existing application or video project:

```bash
cd path/to/your-project
storyforge setup
```

Setup copies project resources, adds the selected host integrations, and installs the renderer dependencies using its lockfile. It keeps those dependencies in `.storyforge/renderer/`; the application's root `package.json` and lockfile are untouched.

| Option | Effect |
| --- | --- |
| `--host both` | Install Codex and Claude integrations; the default for a new project |
| `--host codex` | Add Codex integration |
| `--host claude` | Add Claude Code integration |
| `--host none` | Create the production library without adding host integration; existing integrations are retained |
| `--skip-install` | Copy files without running npm or downloading dependencies |
| `--keep-local PATH` | Keep a reviewed local version of a previously managed resource during an upgrade; repeat for multiple files |

For example:

```bash
storyforge setup ./my-video-project --host claude
```

For offline scaffolding, use `--skip-install`. When dependencies become available, run setup again. A successful existing dependency install is reused while its package and lock files are unchanged. Setup without a directory also works from subfolders of an existing project. It preserves that project's host selection on reruns. Setup does not start paid generation or authenticate to any service.

### What setup creates

| Path | Contents |
| --- | --- |
| `storyforge.json` | Project configuration, selected hosts, and resource paths |
| `.storyforge/WORKFLOW.md` | Producer instructions with this project's paths |
| `.storyforge/agents/` | Canonical specialist role cards |
| `.storyforge/docs/`, `schemas/`, `templates/`, `examples/` | Guides, contracts, production templates, and sample briefs |
| `.storyforge/renderer/` | Editable React, Remotion, and Three.js source, fonts, and npm lockfile |
| `.storyforge/runs/` | Location for future runs, media, state, and delivery packages |
| `.storyforge/installation.json` | File ownership and hashes used for safe setup reruns |
| `AGENTS.md` and/or `CLAUDE.md` | A managed StoryForge section alongside your existing instructions |
| `.codex/agents/` and/or `.claude/agents/` | Project-scoped worker definitions |

Setup adds ignore rules for generated production data and dependencies. Commit the configuration, instructions, library, and renderer source when they belong in your project. Keep generated videos, source recordings, and private research out of public repositories unless you deliberately choose to share them.

Existing instruction text, app files, custom agent definitions, and Codex settings are preserved. Ordinary local resource changes are retained on a same-version rerun. If a new toolkit resource overlaps those changes, or an unmanaged file occupies a needed path with different contents, setup reports the conflict before applying generated-file changes. Keep personal instructions outside StoryForge's managed block markers. There is no automatic force overwrite. Selecting a different host later adds its integration; it does not remove an existing integration.

## 3. Check the project and open it in your host

```bash
storyforge info
storyforge doctor
```

`info` shows the package and project paths. `doctor` checks local prerequisites and offers next steps; it does not read credentials or certify that an account has access to a model or media service.

| Capability | Needed for |
| --- | --- |
| Python 3.11+ | CLI, brief validation, saved state, and task coordination |
| Node 22+ and npm | Renderer dependency installation, Studio, stills, and movie exports |
| FFmpeg and ffprobe | Measuring real narration and inspecting encoded media |
| Codex or Claude Code | Conversational producer and specialist agents |
| Authenticated `codex` or `claude` CLI | Optional subprocess-worker mode |
| Live search and approved media tools or supplied assets | Research, narration, images, music, and a complete production |

Open the project folder in Codex or Claude Code and ask:

> Start StoryForge using .storyforge/WORKFLOW.md. Ask for my niche, approximate length, format, and references, then help me choose a topic and create the video with the specialist agents. Reuse answers I have already provided and keep the run resumable.

The host collects the brief and coordinates model work. For terminal intake alone, use `storyforge start`; it saves the brief in a new run and prints the run directory. It does not automatically launch model workers. Continue in the host with that run, or use the explicit [`run` command](CLI.md#bounded-subprocess-execution).

## 4. Preview the included scenes

```bash
storyforge studio
```

Open the printed local URL and select `StoryShort` or `StoryLong`. For real PNG previews without opening Studio:

```bash
storyforge preview
```

The default preview uses the fictional, silent 45-second Short demonstration and creates a new output folder under `.storyforge/previews/`. To inspect the landscape layout:

```bash
storyforge preview --props .storyforge/renderer/examples/demo-long.json
```

The first render may download Remotion's Chrome Headless Shell. These scripts make no model or paid media calls. See the [renderer guide](../renderer/README.md) for supported browser settings and local asset handling. In a configured project its renderer lives at the path shown by `storyforge info`.

## Upgrade without losing project changes

For an installation made from the GitHub URL above:

```bash
pipx upgrade storyforge-video
cd path/to/your-project
storyforge setup
storyforge doctor
```

The CLI installation and each project's copied resources are separate. Upgrading the CLI does not silently replace a project's custom scenes or prompts. Setup compares its file ownership records and refreshes eligible project resources. Review any reported conflicts before deciding which changes to retain.

If an upgrade conflicts with a customized resource, create a separate clean copy for comparison:

```bash
storyforge setup ../storyforge-upgrade-review --skip-install
```

Review the new version and merge the changes you want into your existing project. Then acknowledge each reviewed file whose local contents should remain:

```bash
storyforge setup --keep-local .storyforge/renderer/src/StoryVideo.tsx
```

Replace the example path with the actual conflict path; repeat `--keep-local` for multiple files. These paths are relative to the selected project root, even if you run setup from a subfolder. Setup preserves those files byte for byte and updates their recorded upstream baseline to the installed toolkit version. Subsequent reruns retain your customization; a later overlapping upstream change will require review again.

The acknowledgement applies only to previously managed resource files. It cannot adopt unrelated unmanaged files, bypass project configuration or installation-record checks, or accept edits inside managed instruction blocks. Keep custom host instructions outside those blocks. Keep your run data and installation record; deleting them is not a conflict-resolution step.

For reproducible installations, [pip supports an explicit Git commit](https://pip.pypa.io/en/stable/topics/vcs-support/#git) after the URL's `@`. Use a real full commit hash from this repository. A commit-pinned install intentionally stays at that revision until you choose another one.

### Moving from the v0.1 editable checkout

Install v0.2 with pipx, open a new terminal, and check `storyforge --version`. If the old virtual environment is active, deactivate it so the intended executable is selected. Keep the old checkout and runs until you have copied or archived anything you need. Set up your new project normally; existing run paths can still be supplied explicitly to the CLI. Setup does not move old productions or rewrite their saved artifacts.

## Troubleshooting

| Problem | Action |
| --- | --- |
| `pipx` or `storyforge` is not found | Run `pipx ensurepath`, open a new terminal, and inspect `pipx list`. For a virtual-environment install, activate that environment. |
| Python is too old | Select a Python 3.11+ interpreter using pipx's `--python` option when installing. |
| Git URL installation cannot find Git | Install Git and confirm `git --version` works in the same terminal. |
| Setup reports missing Node/npm or dependency installation fails | Resolve the reported runtime/network problem and rerun setup. Files already scaffolded remain available. |
| Setup reports a modified-file conflict | Compare with a clean setup, merge the changes you want, then acknowledge eligible reviewed files with `setup --keep-local PATH` as shown above. |
| `doctor` cannot find a project | Run `storyforge setup` in the intended folder, or pass `--project path/to/project` to a project-aware command. |
| Codex agents are disabled in existing settings | Review that setting through your normal host controls; setup preserves your choice. Normal subagent or sequential role execution remains available. |
| Renderer browser download fails | Follow the reported network error or configure an existing compatible browser as described in the renderer guide. |
| A model or media service is unavailable | Configure it in the chosen host or supply approved media; local setup cannot grant service access. |

Use `storyforge COMMAND --help` for the options supported by the installed version. The [pipx CLI reference](https://pipx.pypa.io/stable/reference/cli.html) covers environment management and upgrades.
