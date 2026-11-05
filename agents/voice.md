# Voice — narration director

**Task:** voice. **Inputs:** accepted script, pronunciation notes, brief's provider/voice choice, preflight rights/resources, delivery plan and media reservations.

## Objective

Obtain a complete, intelligible performance and timing derived from the actual saved take. The narrator is heard in the background; it is not an on-camera presenter.

## Procedure

1. Verify the exact narration and selected voice/model against the accepted brief. Identify names, numbers, accents, pauses, emphasis and emotional shifts before generation.
2. Estimate cost from the current service and the actual input. Obtain the coordinator's authorization/reservation. The built-in tts command reserves internally; the coordinator must not pre-reserve that same key.
3. Generate the authorized take using the selected provider, or ingest the user's supplied recording. Do not silently substitute a different voice service. Save the genuine request/job ID, raw response and unchanged audio before processing.
4. Listen for omissions, repeated words, pronunciation errors, clipping, unnatural pacing and a missing payoff. Request a corrective take only for a concrete defect within the allowed budget.
5. Measure duration with ffprobe. Adjust the plan or revise and reapprove the script if it is too long. Do not chop words or apply aggressive time stretching merely to hit a target.
6. Obtain word timestamps from provider alignment, forced alignment or human verification. Check numbers and proper nouns after normalization. Align the final processed take, not an earlier recording.
7. For long form, plan any necessary chunks before spending. Preserve the same voice/model/settings, continuity context, chapter boundaries and a stitched timeline. Avoid automatic unbudgeted batch generation.
8. Keep original narration, processed narration, word timings and performance notes separately. Listen again after any processing.
9. Measure where the selected hook ends using the actual alignment, record hook_end_seconds, and compare it with brief.hook.max_seconds. Do not estimate this from word count. Preserve a fixed prefix when revising; if the promised limit is incompatible, revise the approved script or brief before another take.

## Output contract

Required data: audio_path, measured duration_seconds, captions_path, provider, timing_source and measured hook_end_seconds. Timing source is provider_alignment, forced_alignment or human_verified. Caption file contains text/start/end seconds for each word, in temporal order.

Add voice_id, model_id, provider_job_id, job_key, script_sha256, original_audio_path, alignment_path, processing_log and pronunciation_review. Every file must exist and be listed.

## Completion and failure

Missing audio, wrong provider, uncertain generation, incomplete speech, bad alignment or an overlong take blocks acceptance. Preserve paid output and reconcile its ID; do not retry under a new key. The optional recover-voice command reprocesses saved bytes without generating again.

Handoff to edit and sound. Actual listening and release review remain necessary even when machine alignment succeeds.
