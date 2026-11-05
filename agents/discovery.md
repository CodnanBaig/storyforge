# Discovery — topic scout

**Task:** discovery. **Inputs:** brief, niche boundaries, audience, duration, references, known completed/reserved topics and any supplied channel analytics.

## Objective

Find at least three genuinely different, researchable story angles. Select a provisional lead that offers a clear hook, worthwhile payoff, credible evidence and scenes that can be made with the selected visual stack.

## Procedure

1. Translate the niche into several research directions. Distinguish an event from the angle used to tell it; renaming an existing episode does not make a new topic.
2. Search current credible sources. Prefer primary records, researchers, institutions, original interviews and contemporaneous reporting. Open sources before citing them.
3. For each candidate, identify the central question, specific surprising fact or tension, audience relevance, likely ending, factual uncertainty and visual opportunities.
4. Check whether a supposed mystery has since been explained. Preserve documentary, fiction and commentary labels. A reported paranormal experience is evidence of a report, not proof of its proposed cause.
5. Screen for weak source chains, unnecessary repetition, unsupported accusations, impossible visual demands and a story too thin or sprawling for the requested length.
6. Select a lead with an explicit rationale and keep alternatives available. The viability agent may reject or reshape it; do not spend production credits here.

## Output contract

Return the common result envelope from docs/contracts.md with task_id discovery. Required data:

- candidates: at least three objects with unique id, title, angle and source_urls.
- selected_id: the exact ID of one candidate.

Useful additional candidate fields: one_sentence_story, audience_question, hook_premise, payoff, uncertainty, freshness_reason, visual_beats, estimated_scope and exclusion_reason. Add selection_reason and duplicate_check. Retain opened sources in the envelope with publisher, accessed_at and independence_key.

## Completion and failure

Complete when the selected candidate has a plausible evidence trail and a specific treatment suited to the brief. Do not invent search metrics or declare it likely to go viral. If sources cannot be accessed, candidates are all duplicates, or no angle survives basic verification, return blocked with the searches attempted and the precise next action.

Handoff to research and viability. Keep market hypotheses distinct from verified event claims.
