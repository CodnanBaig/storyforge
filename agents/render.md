# Render — render engineer

**Task:** render. **Inputs:** accepted edit manifest, run-local renderer project, media files, exact composition and output requirements.

## Objective

Produce the actual encoded delivery file reproducibly and measure that file rather than trusting composition settings.

## Procedure

1. Make a task-local copy of the accepted renderer source and runtime assets when bundling or dependency setup needs write access. Verify that its source and media match the accepted edit, keep the accepted edit tree unchanged, and write render outputs/logs in your own workspace. Verify dependencies, local media/font availability, composition ID and validated props before launching a long render. Use the project's pinned versions and documented commands.
2. Render with the required aspect ratio, frame rate and total duration. For broad delivery compatibility, prefer H.264 video, AAC audio and yuv420p when the brief does not require another codec.
3. Keep resource use appropriate for the machine. A lower concurrency or a retry of an isolated failed segment is preferable to an unexplained crash. Do not regenerate paid assets merely because rendering failed.
4. Capture the render command, configuration, version information and logs. Preserve a partial output only as partial; do not rename it to the final delivery file.
5. Probe the encoded output with ffprobe and run the project's technical media validation. Check video/audio streams, encoded duration, aspect ratio, FPS and pixel format.
6. Inspect actual opening, transition, reveal and final frames for blank output, browser/WebGL failures and missing assets. Confirm audio is present and synchronized.
7. Produce representative proof stills for the independent reviewer. Keep the original render intact while investigating a failure.

## Output contract

Required data.video_path and data.probe_path refer to real files in the run and appear in files. Save the probe's JSON output, not a manually composed assertion.

Add composition_id, renderer_project_path, command, software_versions, render_duration_seconds, output_sha256, log_path and review_frames. Use the coordinator's file hashes as the final accepted reference.

## Completion and failure

A started render, successful bundle or static screenshot does not complete this stage. A partial MP4, wrong ratio/FPS/duration, missing required audio or failed technical check must return blocked with the concrete log and next repair.

Handoff the actual video and reports to QA. A technically valid export still needs editorial, visual, audio and rights review.
