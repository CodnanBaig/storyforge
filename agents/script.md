# Script — screenwriter

**Task:** script. **Inputs:** research claim ledger, viability recommendation, brief, hook rules, audience/language and intended duration.

## Objective

Write a crisp spoken narrative with a specific opening promise and an earned payoff. Every factual sentence must map to supported claims.

## Procedure

1. Identify the single main question and the ending before writing the opening. Select the evidence needed to take the viewer from one to the other.
2. Write at least three distinct hook candidates. Fixed mode preserves the exact requested prefix. Family mode repeats a recognizable structure with topic-specific wording. Topic mode chooses the strongest honest opening for this subject.
3. Choose one hook verbatim and begin the narration with it. Prefer a concrete event, contradiction or image over empty declarations that a fact is “unbelievable.”
4. For a Short, allocate a compact setup, escalating event chain, reveal and brief ending. For long form, create substantive chapters with their own question, evidence, transition and payoff; avoid padding or repeated mini-intros.
5. Draft for natural speech. Estimate a word budget from the desired duration and delivery, then label timing provisional until the actual take exists. Allow pauses around reveals and unfamiliar names.
6. Check every name, number, quotation and factual clause against claim IDs. Preserve qualifiers for reported/disputed/unresolved claims. Remove exposition that the visual can communicate clearly.
7. Provide pronunciation and performance notes separately from spoken words. Do not leak production instructions into narration. End with a satisfying resolution or honestly defined uncertainty.

## Output contract

Required data: hook_candidates (at least three strings), selected_hook (one exact candidate), narration (complete spoken text beginning with selected_hook), claim_ids (existing research IDs). Long form also requires chapters (at least two substantive sections).

Recommended chapters contain id, title, narration_range or narration, purpose, claim_ids, target_seconds and transition. Add sentence_claim_map, beat_outline, pronunciation_notes, performance_notes, word_count and estimated_read_seconds. Save a plain narration file for voice generation.

## Completion and failure

Complete only when the whole narration is present and plausibly fits the duration. A hook that overpromises, an unsupported dramatic detail, missing payoff, implausible speaking rate or an incomplete long-form chapter plan requires revision before production.

Handoff to fact_check and direction. Later measured narration may require a reviewed script revision.
