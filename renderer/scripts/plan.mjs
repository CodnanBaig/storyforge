import {readFile, realpath, stat} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {assertManifest} from '../src/validate.mjs';

export const rendererRoot = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
export function args(values = process.argv.slice(2)) {
  const result = {};
  for (let i = 0; i < values.length; i++) {
    const key = values[i];
    if (!key.startsWith('--')) throw new Error(`Unexpected argument: ${key}`);
    if (values[i + 1] && !values[i + 1].startsWith('--')) result[key.slice(2)] = values[++i];
    else result[key.slice(2)] = true;
  }
  return result;
}
export async function loadPlan(propsPath = 'examples/demo-short.json') {
  const props = JSON.parse(await readFile(path.resolve(rendererRoot, propsPath), 'utf8'));
  if (!props.manifest) throw new Error('Props JSON must contain {"manifest": {...}}');
  assertManifest(props.manifest);
  const publicRoot = await realpath(path.join(rendererRoot, 'public'));
  for (const asset of props.manifest.assets) {
    const candidate = await realpath(path.join(publicRoot, asset.src));
    const relative = path.relative(publicRoot, candidate);
    if (relative.startsWith('..') || path.isAbsolute(relative)) throw new Error(`Asset escapes public/: ${asset.id}`);
    if (!(await stat(candidate)).isFile()) throw new Error(`Asset is not a file: ${asset.id}`);
  }
  const narration = props.manifest.narration;
  if (narration) {
    const asset = props.manifest.assets.find((a) => a.id === narration.asset_id);
    const probe = spawnSync('ffprobe', ['-v', 'error', '-select_streams', 'a:0', '-show_entries', 'format=duration:stream=codec_type', '-of', 'json', path.join(publicRoot, asset.src)], {encoding: 'utf8'});
    if (probe.error || probe.status !== 0) throw new Error(`ffprobe could not measure narration; install FFmpeg and verify the audio: ${probe.error?.message ?? probe.stderr}`);
    const media = JSON.parse(probe.stdout);
    const seconds = Number(media.format?.duration);
    if (!media.streams?.some((s) => s.codec_type === 'audio') || !Number.isFinite(seconds) || seconds <= 0) throw new Error('Narration file has no valid audio stream/duration');
    if (Math.abs(seconds - narration.duration_seconds) > 0.1) throw new Error(`Narration measurement mismatch: manifest ${narration.duration_seconds}s; file ${seconds}s`);
    const total = props.manifest.scenes.reduce((s, item) => s + item.duration_in_frames, 0) / props.manifest.format.fps;
    if (seconds > total + 0.05) throw new Error(`Actual narration is longer than the ${total}s timeline`);
  }
  return props;
}
export function browserOptions() {
  return {
    ...(process.env.REMOTION_BROWSER_EXECUTABLE ? {browserExecutable: process.env.REMOTION_BROWSER_EXECUTABLE} : {}),
    chromiumOptions: {gl: process.env.REMOTION_GL || 'angle'},
  };
}
