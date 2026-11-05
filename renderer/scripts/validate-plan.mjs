import {args, loadPlan} from './plan.mjs';
try {
  const options = args();
  const {manifest} = await loadPlan(options.props || 'examples/demo-short.json');
  const frames = manifest.scenes.reduce((sum, scene) => sum + scene.duration_in_frames, 0);
  console.log(JSON.stringify({valid: true, project_id: manifest.project_id, demo: manifest.demo, scenes: manifest.scenes.length, frames, duration_seconds: frames / manifest.format.fps, format: manifest.format}, null, 2));
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
