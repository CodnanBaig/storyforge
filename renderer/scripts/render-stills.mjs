import {mkdir, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import {args, browserOptions, loadPlan, rendererRoot} from './plan.mjs';

try {
  const options = args();
  const props = await loadPlan(options.props || 'examples/demo-short.json');
  const manifest = props.manifest;
  const id = manifest.format.height > manifest.format.width ? 'StoryShort' : 'StoryLong';
  const scale = Number(options.scale || 0.5);
  if (!Number.isFinite(scale) || scale <= 0 || scale > 1) throw new Error('--scale must be >0 and <=1');
  const out = path.resolve(rendererRoot, options.out || 'previews');
  await mkdir(out, {recursive: true});
  const serveUrl = await bundle({entryPoint: path.join(rendererRoot, 'src/index.ts'), publicDir: path.join(rendererRoot, 'public'), onProgress: (p) => {if (p === 100) console.log('Bundle ready.');}});
  const onBrowserLog = (log) => {if (log.type === 'error' || log.type === 'warning') console.warn(`[browser ${log.type}] ${log.text}`);};
  const composition = await selectComposition({serveUrl, id, inputProps: props, onBrowserLog, ...browserOptions()});
  console.log(`Selected ${id}: ${composition.width}×${composition.height}, ${composition.durationInFrames} frames.`);
  let offset = 0;
  const defaultFrames = manifest.scenes.map((scene) => {
    const f = offset + Math.floor(scene.duration_in_frames * 0.45); offset += scene.duration_in_frames; return f;
  });
  const frames = options.frames ? String(options.frames).split(',').map(Number) : defaultFrames;
  const records = [];
  for (const frame of frames) {
    if (!Number.isInteger(frame) || frame < 0 || frame >= composition.durationInFrames) throw new Error(`Invalid frame: ${frame}`);
    const output = path.join(out, `${id}-${String(frame).padStart(5, '0')}.png`);
    await renderStill({serveUrl, composition, inputProps: props, output, frame, imageFormat: 'png', scale, onBrowserLog, ...browserOptions()});
    records.push({frame, output, width: Math.round(composition.width * scale), height: Math.round(composition.height * scale)});
    console.log(`Rendered ${output}`);
  }
  await writeFile(path.join(out, `${id}-verification.json`), JSON.stringify({project_id: manifest.project_id, demo: manifest.demo, kind: 'actual-remotion-stills', frames: records}, null, 2));
} catch (error) {
  console.error(error.stack || error.message);
  process.exitCode = 1;
}
