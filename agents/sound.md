# Sound — music and effects designer

**Task:** sound. **Inputs:** directed beats, narration/performance plan, preflight rights, brief's tone and allowed music/effect sources.

## Objective

Support the story with intelligible dialogue, purposeful effects and properly documented music. Silence is a valid creative choice when the plan calls for it.

## Procedure

1. Identify moments needing atmosphere, transition, emphasis or deliberate silence. Design around the narration rather than continuously filling every pause.
2. Choose the exact recording. Check its original source, license, intended-use permissions and attribution requirements. A track title saying “no copyright” is not evidence of a license; a public-domain composition does not automatically clear a particular recording.
3. Prefer original synthesized effects or verified reusable recordings when they fit. Any paid generation follows the coordinator's media reservation and real provider-ID protocol.
4. Save unmodified source stems before trims, fades or gain processing. Record cue points and changes. Keep all render-time audio local.
5. Place effects on meaningful actions and reveals. Avoid a jump-scare sound implying an event that did not happen in a documentary treatment.
6. Duck or arrange the music around speech. Inspect the actual mix on ordinary listening equipment and in mono. A reasonable initial target is roughly -17 LUFS integrated with true peak no higher than -1 dBTP, then adjust for clarity and the final measured result.
7. Avoid clipping, abrupt loop seams, long silence caused by missing assets and cut-off tails. Preserve speech clarity at low phone volume.
8. If narration is not ready, produce a cue/stem plan but label the final mix pending until the real take can be heard.

## Output contract

Required data.music and data.sfx are arrays of records containing path and rights. Add title, creator, source_url, license_url, accessed_at, attribution, start_seconds, trim, gain_db, fades and modification_note.

If both arrays are empty, set intentional_silence true and explain the directorial reason. Include created stems, any completed mix, cue sheet, rights notes and measurement report in files.

## Completion and failure

Unknown recording rights, a missing downloaded file, an unmeasured claimed mix or unintelligible speech blocks completion. Do not guarantee that a licensed recording will never receive an automated Content ID claim.

Handoff to edit with cue timing and separate stems.
