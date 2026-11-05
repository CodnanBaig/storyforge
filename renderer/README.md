# StoryForge renderer

A local TypeScript/React video renderer using **Remotion 4.0.541, Three.js 0.180.0 and React Three Fiber**. It includes four procedural diorama environments, one reusable mannequin character rig, three palettes, measured narration input, local images/audio, and timed captions.

The included 45-second **fictional, silent technical demo** shows the renderer. It has no research, genuine narration, traction evidence or production approval. Every demo frame carries a visible preview label. The landscape example is also 45 seconds to keep inspection practical; production plans can extend to two hours with up to 200 scenes.

## Run on a Mac

Install Node.js 22 or newer and FFmpeg (`brew install node ffmpeg` if you use Homebrew). From the project root:

```bash
cd renderer
npm ci
npm run typecheck
npm run validate -- --props examples/demo-short.json
npm run studio
```

Open the local URL printed by Remotion (normally `http://localhost:3000`). Studio starts with `--no-open`; it does not launch a browser window automatically. Select **StoryShort** or **StoryLong**. Both composition IDs derive dimensions, FPS and exact frame count from the supplied manifest.

To preview an exported plan in Studio:

```bash
npm run studio -- --props ../runs/MY_RUN/render-props.json
```

The renderer uses bundled local fonts. First-time still/video rendering may download Remotion's Chrome Headless Shell. There is no paid media generation or model call in these scripts. Npm installation and browser downloads require network access; renders need enough local CPU/RAM/disk space.

## Inspect before rendering a movie

```bash
npm run stills -- --props examples/demo-short.json --out previews/portrait --scale 0.5
npm run stills -- --props examples/demo-long.json --out previews/landscape --scale 0.5
```

The default is one real PNG near the middle of each scene. `--frames 148,478,808,1152` selects exact frames. `--scale 1` produces full-resolution stills. Each run writes a verification JSON beside the images. These are still checks; they do not verify voice performance, transitions at every frame, lip sync, music rights, factual accuracy or an encoded movie.

For low-level CLI use:

```bash
npx remotion still src/index.ts StoryShort previews/coast.png --props examples/demo-short.json --frame 148 --scale 0.5
npm run bundle
```

If a known installed browser is needed, set `REMOTION_BROWSER_EXECUTABLE` to its actual executable path. Set `REMOTION_GL=angle` (the default) or a Remotion-supported renderer such as `swangle` when the GPU environment requires it. Do not assume identical pixel output across different GPUs/browser versions; all motion and scene randomness are deterministic for a given frame and seed.

## Input contract

Read [CONTRACT.md](CONTRACT.md), [the structural schema](schema/manifest.schema.json) and [the example props](examples/demo-short.json). The root object is `{ "manifest": { ... } }`; it is not the bare manifest. The shared `src/validate.mjs` also checks relationships and timing that JSON Schema cannot express. The Node scripts additionally check local asset existence, symlink containment, and actual narration duration with `ffprobe`.

The sum of scene frame counts is the final video duration. Allocate `Math.round(targetSeconds * fps)` frames for a positive target, and distribute any rounding remainder deliberately across scenes. A 45-second, 30 FPS video has exactly 1,350 frames. Narration may end earlier than the visual timeline; an intentional visual tail is supported. Actual narration and the declared measured duration must be positive, agree within 0.1 seconds, and end no later than the timeline plus 0.05 seconds.

Captions are `{ "text": "A short phrase", "start": 1.20, "end": 2.40 }` in **seconds**, relative to narration beginning at frame zero. Cue times must be ordered, non-overlapping and inside the measured narration. Use real alignment output from the voice pipeline. Use word or short phrase cues; the renderer does not estimate word times from the script. No fake audio is bundled to make a fixture appear finished.

### Templates

| ID | Environment and story role | Shared props |
| --- | --- | --- |
| `lighthouse-coast` | Rocky island, lighthouse, keeper cottage and arriving investigator | seeded rocks, lantern, mannequin |
| `archive-room` | Cutaway archive, desk, shelves, papers and investigator | seeded books, radio, lantern |
| `signal-chamber` | Receiver rings, control desk and listening investigator | animated ring rig, console, mannequin |
| `forest-path` | Pine grove, winding trail and searching investigator | seeded trees/rocks, walking pose |

Each scene accepts `camera: "wide" | "medium" | "detail"`, a `seed`, typography fields, optional `character_id` and optional `image_asset_id`. Camera categories give bounded framing changes; they are not arbitrary director coordinates. Primitive factories and `environmentRegistry` are in `src/scene/`. To add a new environment, implement it there, add the ID to `types.ts`, `validate.mjs` and the schema, then render representative portrait/landscape frames.

Characters are faceless stylized mannequins illustrating the story. They use capsule limbs, sphere heads, configurable coat/skin/trousers, a backpack, and three procedural poses: inspect, listen and walk. This is an intentionally restrained diorama style, not photorealistic anatomy, facial acting, imported skeletal animation or lip sync. Character specifications persist across scenes through `character_id`. A scene can omit the character.

### Styles

`src/styles.ts` defines `midnight-dossier` (navy/teal/amber), `coastal-archive` and `ember-noir`. References should be interpreted into approved palette, lighting, typography, material and composition tokens by the director/style agents. Adding a style requires updating the style registry and schema. The renderer does not inspect URLs or copy a reference channel's identity by itself.

### Local assets and narration

Put assets under `public/media/`, then register paths relative to `public/`:

```json
{
  "assets": [
    {"id": "voice-final", "kind": "audio", "src": "media/voice-final.wav", "provenance": "Approved original narration; consent and provider record in run artifacts"},
    {"id": "document-photo", "kind": "image", "src": "media/document.png", "provenance": "Original generated illustration; job record in run artifacts"}
  ],
  "narration": {"asset_id": "voice-final", "duration_seconds": 43.20, "measured": true},
  "music": null
}
```

This fragment is illustrative, not a runnable audio fixture. Measure the file you actually have. Absolute paths, URLs, traversal and symlinks escaping `public/` are rejected by the scripts. A scene's image asset appears as a small editorial card; image generation is an optional upstream operation. Narration and music use `@remotion/media`; music has a conservative volume range, a fade and simple narration ducking. The renderer does not select/licence music, normalize audio loudness, create voice acting, or guarantee a mix passes audio QA. Add measured/loudness-checked final audio from the production pipeline.

## Export deliberately

For an approved production manifest with `demo: false`, real measured narration and aligned captions:

```bash
npm run validate -- --props path/to/final-props.json
npm run render -- --props path/to/final-props.json --out renders/final-v001.mp4
```

The render script exports H.264/YUV420p with AAC when audio is present, limits render concurrency to two, and refuses to overwrite an existing output. A technical demo export requires the explicit `--allow-demo` flag and retains its visible label. Nothing uploads to YouTube.

`demo: false` is not factual or rights approval. The orchestrator must enforce approved research/script/direction/assets and perform QA on this exact final MP4. Check final duration/resolution, full playback, source-to-claim traceability, measured voice/caption sync, legibility, safe areas, music levels and rights before packaging. The intended cycle is **plan → local assets → stills → revisions → final export → final QA**.

## Implementation notes

- `useCurrentFrame()` and FPS drive every movement. No wall-clock animation, `useFrame`, `Math.random`, CSS transition, remote texture, or runtime model call determines a frame.
- Environments render in `ThreeCanvas`; the composition uses Remotion sequences with one-second premount. Hard scene cuts are intentional. Text entrances, camera movement, lighthouse sweep, small character movement and prop motion are frame derived.
- Portrait typography/caption areas and landscape placement are separate layouts. Inspect each real script; extreme text may still need editorial shortening. Short headlines and concise body text are encouraged even though validation allows longer copy.
- A complete production is larger than this renderer: upstream agents research, write, direct and generate assets/voice; downstream QA evaluates the export. Four template families provide a concrete starting library, not unlimited automatic scene invention.
- Dependencies are pinned in the lockfile. Remotion's licensing terms still apply to commercial use; review them for your organization before deployment. No assertion of license eligibility is made here.

## Verification record

Actual checks from this build are recorded in `VERIFICATION.md` after rendering. Generated `build/`, `node_modules/`, and temporary browser downloads are not part of the source deliverable. The delivered previews, when present, are actual Remotion/Three.js stills, not concept art.
