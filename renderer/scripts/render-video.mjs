import {mkdir, stat} from 'node:fs/promises';
import path from 'node:path';
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {args, browserOptions, loadPlan, rendererRoot} from './plan.mjs';

try {
  const options = args();
  if (!options.props || !options.out) throw new Error('Usage: npm run render -- --props path/to/props.json --out renders/video.mp4 [--allow-demo]');
  const props = await loadPlan(options.props);
  if (props.manifest.demo && !options['allow-demo']) throw new Error('Demo plan: pass --allow-demo to export a visibly labeled technical preview.');
  const outputLocation = path.resolve(rendererRoot, options.out);
  if (await stat(outputLocation).then(() => true, () => false)) throw new Error(`Refusing to overwrite ${outputLocation}; use a new output filename.`);
  await mkdir(path.dirname(outputLocation), {recursive: true});
  const id = props.manifest.format.height > props.manifest.format.width ? 'StoryShort' : 'StoryLong';
  const serveUrl = await bundle({entryPoint: path.join(rendererRoot, 'src/index.ts'), publicDir: path.join(rendererRoot, 'public')});
  const composition = await selectComposition({serveUrl, id, inputProps: props, ...browserOptions()});
  let last = -1;
  await renderMedia({serveUrl, composition, inputProps: props, outputLocation, codec: 'h264', audioCodec: 'aac', pixelFormat: 'yuv420p', concurrency: 2, ...browserOptions(), onProgress: ({progress}) => {
    const p = Math.floor(progress * 10) * 10;
    if (p !== last) {last = p; console.log(`Render ${p}%`);}
  }});
  console.log(`Rendered ${outputLocation}`);
  console.log('Run production QA on this exact export before packaging or publishing.');
} catch (error) {
  console.error(error.stack || error.message);
  process.exitCode = 1;
}
