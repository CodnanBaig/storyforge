# Verification record

Version: **0.2.0**. This record distinguishes executed local checks from live production work. The installation checks below cover the new package workflow; the existing visual proofs remain the renderer's original reviewed scene checks.

## Installable package and project setup

The wheel and source distribution were built from the canonical repository assets. The distribution verifier compared the hashes of all **130 bundled resource files**, checked exclusion fixtures, rebuilt a wheel from the source distribution, and verified reproducible wheel bytes. The source-built and source-distribution-built wheels were identical.

Both wheels were installed noneditably into fresh Python environments after their temporary build checkouts had been deleted. Each installed package resolved its own resources, generated real worker task packets, initialized an existing project with all 32 native worker definitions, preserved the original app package file and instructions, and completed an idempotent setup rerun.

An additional clean installed environment ran the normal `storyforge setup` command in an existing-app fixture. npm installed the renderer's locked dependencies. Repeating setup from a project subdirectory created or updated zero files and reused those dependencies. `storyforge start --brief` reused a saved brief, and a task packet requested from outside that project retained the correct project toolkit and renderer paths.

The installed project's renderer passed TypeScript checking, validation of both included portrait/landscape manifests, and Remotion bundling. This validates the copied source and local dependency setup; it is not a new narrated-video production or full animation review.

Reproduce the separate distribution check with development build dependencies installed:

```bash
python3 scripts/verify_distribution.py --output-dir dist/verification
```

No package was published to PyPI or npm. The supported public installation uses the repository's Git URL.

## Python coordinator and provider transports

**114 tests passed** in the final substantive Python test run. The default discovery command found 115 tests and skipped the opt-in distribution test; the full distribution verifier was executed separately and passed as described above. The suite covers:

- Concurrent claims and exclusive task ownership.
- Expired lease recovery, stale-token rejection and live-worker preservation.
- Dependency gates, retry caps, invalidation and retained lifetime budgets.
- Brief fingerprint changes, completed-file tampering, traversal and escaping symlinks.
- Transactional media reservations, idempotency and duplicate uncertain requests under different job keys.
- Task-scoped media recovery context survives retries, preserving actual provider IDs and saved paths.
- Real contract validation through the bounded worker coordinator.
- Fake Codex/Claude CLIs executed as real subprocesses, with strict structured results, partial/failure rejection, timeouts, process-tree cleanup and secret-log redaction.
- Cooperative cancellation of a running fake CLI.
- Nineteen ElevenLabs transport/alignment tests using mocked HTTP and synthetic bytes; no real key or live generation.
- Actual ffprobe inspection of a small FFmpeg-generated test clip.
- Caption boundary conversion, provider consistency, measured hook limits, genuinely passing technical reports and delivery of the verified video.
- Final metadata must match the exact independently reviewed packaging.
- Resource lookup in source and installed layouts, including incomplete-installation errors.
- Existing-project preservation, project-path validation, safe setup reruns, source credential/cache exclusions, native wrappers, and file/directory collisions.
- Upgrading unchanged resources, preserving local customizations, conflict preflight, and explicit acknowledgment of a reviewed local merge without overwriting it.
- Project discovery from subfolders, saved-brief reuse, external run origins, literal renderer argument paths, dependency fingerprints, and actionable install failures.

Run the suite with:

```bash
python3 -m unittest discover -s tests -v
```

The media fixture tests skip when FFmpeg is unavailable. All of them executed in this build environment.

## Workflow and renderer handoff

The offline demonstration was executed. It completed seven synthetic planning stages and deliberately blocked at preflight. It made zero worker/model calls, reserved zero media jobs and did not claim delivery.

Its actual shot plan was exported to Remotion props and passed the Node renderer validator: **5 scenes, 1,350 frames, 45 seconds, 1080×1920 at 30 fps**. The resulting manifest remains a labelled silent draft; this verifies interchange rather than factual or media production.

All sixteen pipeline tasks resolve to role cards and native Codex/Claude wrappers. Codex TOML definitions were parsed. The source includes eighteen role cards in total: sixteen executable stages, the producer and an advisory post-publication analyst.

## Renderer

TypeScript checking and Remotion bundling passed with pinned dependencies. **Eight actual PNGs were rendered and visually reviewed**: four procedural Three.js environments in portrait and landscape. The bundled-font loading issue was fixed before those previews were accepted; a small platform-grid overhang was corrected and the two affected stills regenerated. The renderer's [verification record](../renderer/VERIFICATION.md) gives the exact files, dimensions, conditions and remaining limits. These are silent fictional starter-scene proofs, not completed narrated episodes.

The landscape demo is a short technical sample of the landscape layout. A complete long-form documentary was not produced in this build. Longer productions need authored chapters, assets, measured narration and final review.

## Live integrations still requiring an authorized production run

The tests did **not** call a paid Codex/Claude model, live ElevenLabs synthesis, an image generator, YouTube upload API, or a channel-analytics account. The optional CLI worker transports require installed/authenticated provider CLIs and permitted research/media tools. The ElevenLabs helper requires a genuine authorized key, selected voice, current estimates and sufficient approved budget.

A live end-to-end video has not been certified by these tests. The first production should use the user's real niche, references and account capabilities, then inspect the entire narrated export and actual release rights. Passing these technical checks does not guarantee source truth, performance, licensing clearance, audience reach or monetization.
