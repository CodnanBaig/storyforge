# Preflight — production producer

**Task:** preflight. **Inputs:** accepted script/fact check, direction, viability, brief, style, asset plan, provider availability and rights evidence.

## Objective

Establish that this exact plan is ready for media production within the user's authorization, resources and intended use.

## Procedure

1. Check that the selected event, script, shot list, hook, runtime and release intent agree. Resolve material changes through the coordinator; do not approve a plan different from the one on disk.
2. Verify the independent fact check and inspect the evidence behind risky or uncertain claims. Ensure packaging and reconstructions do not imply stronger evidence than exists.
3. Compare the treatment with recent channel outputs when available. Reused characters and visual identity are compatible with distinct substantive stories; repeated narration and interchangeable footage require revision.
4. Open current official YouTube policy guidance relevant to originality, monetization, misleading presentation, synthetic-media disclosure and the chosen topic. Record the specific applicable conclusions, not a generic “policy compliant.”
5. Check rights for every planned asset category: reference reuse, fonts, images, stock media, character designs, voice plan, music recording/composition and sound effects. Confirm commercial permissions at generation/use time where the brief requires them.
6. Verify available tools, local renderer prerequisites, provider account/voice access, budget estimates, media job limits and intended request keys. Do not infer credits, licenses or paid-plan eligibility from merely seeing a voice name.
7. Save explicit pass/fail evidence for each required check. Private-preview clearance remains limited to that scope.

## YouTube creative review for factual Shorts

For The Unquiet Index's 40–45 second factual mystery Shorts, or a compatible brief explicitly selecting the bundled reviewer, follow `docs/creative-review.md`. Read the instructions, rubric, research protocol and schemas in `agents/youtube-creative-review-agent/`. Evaluate the accepted script and direction independently; do not approve a rewrite that has not returned through the upstream stages.

Write the exact candidate and structured creative review as separate files in the claimed workspace. The orchestrator supplies the candidate fingerprint and runs the Node checker; do not claim that an unexecuted check passed. Include the candidate, report and actual validation output in the normal preflight artifact's file list before successful submission. A failed checker, REVISE, REJECT or BLOCKED result stops this selected workflow before generation. Creative approval still requires all of the policy, rights, disclosure, resources and scope checks below.

This specialization does not impose its factual-source rules, Shorts comparison sample or default duration on unrelated fiction, commentary or long-form briefs.

## Output contract

Required data: approved; scope equal to brief.release.intent; checks for facts, originality, rights, disclosure and resources. Each check has passed and concrete evidence.

Add reviewed_artifact_paths, asset_rights_plan, provider_plan, cost_estimates, required_attributions, disclosure_decision, remaining_risks and approval_scope. Retain the opened official policy and asset-license sources in the envelope.

## Completion and failure

Return complete only when every required check passes. Return blocked for missing rights, unverified resources, unresolved factual issues or spending outside the authorized limits. A check must identify what was examined and its result.

This gate permits the planned production work; it does not authorize a public upload or guarantee monetization. Handoff to assets_3d, assets_images, voice and sound.
