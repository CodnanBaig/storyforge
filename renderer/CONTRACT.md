# Renderer input contract (v1)

Root props are `{ "manifest": <manifest> }`. Composition IDs are `StoryShort` and `StoryLong`; `calculateMetadata` derives FPS, dimensions, and total frames from the manifest, so either composition accepts a custom plan.

```json
{
  "schema_version": "1.0",
  "project_id": "run-id",
  "title": "Video title",
  "demo": true,
  "format": {"width": 1080, "height": 1920, "fps": 30},
  "style_id": "midnight-dossier",
  "characters": [{"id":"explorer","name":"Explorer","coat":"#477D79","skin":"#D7B79A","trousers":"#202E3E","scale":1}],
  "assets": [],
  "scenes": [
    {"id":"scene-01","template":"lighthouse-coast","duration_in_frames":300,"eyebrow":"01 / THE ARRIVAL","headline":"A light across the water","body":"Fictional scene for renderer demonstration.","character_id":"explorer","camera":"wide","seed":1}
  ],
  "narration": null,
  "music": null,
  "captions": []
}
```

Scene templates: `lighthouse-coast`, `archive-room`, `signal-chamber`, `forest-path`. Scenes run in manifest order without overlapping time. Each must have >= 2 frames. Camera: `wide`, `medium`, `detail`. Optional `image_asset_id` places a local image in the scene's editorial panel. All scenes may use a character; characters are story participants, never presenters.

Assets: `{id, kind: "image" | "audio", src: "media/name.ext", provenance?: string}`. `src` is relative to renderer/public, no absolute paths, remote URLs, or path traversal. `narration`: `{asset_id, duration_seconds, measured: true}`; audio starts at frame zero. `music`: `{asset_id, volume: 0.12}`. Captions use seconds: `[{text, start, end}]`; one word or a short phrase per item, non-overlapping in ascending order. These match the Python media agent's timing contract directly.

Production validation (`demo: false`) requires real measured narration with a positive duration no longer than the visual timeline plus 0.05 seconds, and valid captions contained within the audio. Narration may end before the video; an intentional visual tail is supported. The Node scripts additionally probe the actual narration file with `ffprobe` and require it to agree with the declared duration within 0.1 seconds. `demo: true` visibly identifies technical previews/drafts; the included fixtures are silent and fictional. Editorial/fact/rights approvals remain the orchestration layer's responsibility.

Recommended bridge: produce a draft plan using `demo: true` until measured audio and aligned captions exist. Match total scene frames to `Math.round(target_duration_seconds * fps)` (positive half-up rounding) when making the production manifest. At 30 FPS, a 45-second target is 1,350 frames even if the measured narration is 43 seconds. Do not synthesize `measured: true` or captions from word-count estimates.

The schema in schema/manifest.schema.json is authoritative. The runtime checks referenced asset IDs and timing relationships in addition to JSON Schema structural rules.
