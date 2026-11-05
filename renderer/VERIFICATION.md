# Renderer verification — 6 November 2026

## Outcome

**Compilation, bundling, manifest validation and eight representative still renders passed.** The eight PNGs were visually inspected for typography, geometry, character continuity and framing. They are real Remotion/Three.js output from the included fictional, silent technical demonstration.

This is proof of the starter scene renderer. A fully narrated episode, music/caption playback, complete movie encoding and frame-by-frame production review were not performed in this build.

## Executed checks

| Check | Result |
| --- | --- |
| Project dependencies | Installed successfully; production versions pinned in `package-lock.json`. |
| TypeScript | `npm run typecheck` passed, including the final font-loader change. |
| Bundle | `npm run bundle` passed; subsequent API bundles of the final source also succeeded. |
| Portrait manifest | Four scenes, 1,350 frames / 45 seconds, 1080×1920, 30 FPS, `demo: true`. |
| Landscape manifest | Four scenes, 1,350 frames / 45 seconds, 1920×1080, 30 FPS, `demo: true`. |
| Browser metadata | Both compositions selected successfully with their manifest-derived dimensions and duration. |
| Actual PNGs | Four 540×960 portrait stills and four 960×540 landscape stills, rendered at scale 0.5. |
| Visual inspection | Headlines, body copy, draft labels, all four environments and the consistent character are visible. No text collisions or missing character geometry were found. |

Nine direct assertions against `src/validate.mjs` passed: silent draft accepted; deliberate visual tail accepted; missing production narration rejected; overlong narration rejected; captions beyond audio rejected; overlapping captions rejected; traversal rejected; unknown character rejected; null manifest returns validation errors.

The production-plan assertion used in-memory metadata, not a real narration file. It does not establish runtime audio playback.

## Actual output files

| Environment | Frame | Portrait | Landscape |
| --- | --- | --- | --- |
| Lighthouse coast | 148 | [StoryShort-00148.png](previews/portrait/StoryShort-00148.png) | [StoryLong-00148.png](previews/landscape/StoryLong-00148.png) |
| Archive room | 478 | [StoryShort-00478.png](previews/portrait/StoryShort-00478.png) | [StoryLong-00478.png](previews/landscape/StoryLong-00478.png) |
| Signal chamber | 808 | [StoryShort-00808.png](previews/portrait/StoryShort-00808.png) | [StoryLong-00808.png](previews/landscape/StoryLong-00808.png) |
| Forest path | 1152 | [StoryShort-01152.png](previews/portrait/StoryShort-01152.png) | [StoryLong-01152.png](previews/landscape/StoryLong-01152.png) |

The archive/forest portrait framing intentionally crops some outer scenery while retaining the character and key props. A review found outer grid strips extending beyond the signal chamber's round platform; their lengths were changed to fit the platform's chords, then the two affected stills were rendered again.

## Font fix

The first component-injected `@font-face` approach failed with `NetworkError` during font readiness and could produce missing text without the explicit failure gate. File hashes, FontTools and an isolated FontFace test confirmed that both bundled font binaries were intact. HTTP tracing confirmed the correct local resource paths and successful responses.

`Fonts.tsx` now caches one promise per document, fetches the local bytes, loads `FontFace` objects from their ArrayBuffers and registers them once before releasing the render handle. Failed loading still calls `cancelRender`; system-font substitution is not treated as success. All eight accepted stills use this loader and show the intended typefaces.

## Hosted verification conditions

Normal browser startup encountered Node `os.networkInterfaces()` / `uv_interface_addresses` failure and a proxy timeout downloading Chrome Headless Shell. A normal npm installation supplied Chromium 153 and SwiftShader for verification only. An archive ownership operation was unsupported, so the same local browser archives were extracted with `chown: false`, outside the deliverable source.

An environment-only adapter supplied the already verified IPv4 loopback when interface enumeration failed and pointed the normal render scripts at that browser with Remotion's `swangle` setting. It did not modify project dependencies, Remotion source or permission controls. The optional browser binary/adapter is not a runtime dependency and is excluded from the source archive. Chromium logged its software-WebGL fallback warning; the completed stills were inspected rather than assuming that warning was harmless.

## Reproduce on the target machine

From `renderer/`, with Node.js 22+ and FFmpeg installed:

```bash
npm ci
npm run typecheck
npm run validate -- --props examples/demo-short.json
npm run stills -- --props examples/demo-short.json --frames 148,478,808,1152 --out previews/portrait --scale 0.5
npm run stills -- --props examples/demo-long.json --frames 148,478,808,1152 --out previews/landscape --scale 0.5
npm run studio
```

Remotion can download its supported browser on a normally connected machine. `REMOTION_BROWSER_EXECUTABLE` and `REMOTION_GL` are optional documented overrides. Studio was not started in this session; no live Studio URL is claimed.

## Remaining production checks

Representative stills do not verify every frame, transitions, actual narration, captions, pronunciation, music balance, complete movie encoding or the accuracy and rights of a future story. Production QA must inspect the entire encoded film and its actual source/rights records. The landscape demonstration is 45 seconds; it is a layout proof, not a completed long-form documentary.

Environment: hosted Linux; Node 24.22.1, npm 11.9.0, TypeScript 5.9.3, React 19.1.0, Remotion 4.0.541, Three.js 0.180.0 and React Three Fiber 9.3.0. No paid generation provider was called and nothing was published.
