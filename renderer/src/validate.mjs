export const TEMPLATES = ['lighthouse-coast', 'archive-room', 'signal-chamber', 'forest-path'];
export const STYLE_IDS = ['midnight-dossier', 'coastal-archive', 'ember-noir'];

/** Shared browser/Node validation. Media probing belongs to scripts/validate-plan.mjs. */
export function validateManifest(value) {
  const errors = [];
  const object = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
  const check = (ok, message) => { if (!ok) errors.push(message); };
  const str = (v) => typeof v === 'string' && v.trim().length > 0;
  const finite = (v) => typeof v === 'number' && Number.isFinite(v);
  const color = (v) => typeof v === 'string' && /^#[0-9a-fA-F]{6}$/.test(v);
  if (!object(value)) return ['manifest must be an object'];
  const m = value;
  check(m.schema_version === '1.0', 'schema_version must be 1.0');
  check(str(m.project_id), 'project_id is required');
  check(str(m.title), 'title is required');
  check(typeof m.demo === 'boolean', 'demo must be an explicit boolean');
  check(STYLE_IDS.includes(m.style_id), 'unknown style_id');
  const f = m.format ?? {};
  for (const axis of ['width', 'height']) {
    check(Number.isInteger(f[axis]) && f[axis] >= 320 && f[axis] <= 3840 && f[axis] % 2 === 0,
      `format.${axis} must be an even integer from 320 to 3840`);
  }
  check(Number.isInteger(f.fps) && f.fps >= 24 && f.fps <= 60, 'format.fps must be an integer from 24 to 60');
  const characters = Array.isArray(m.characters) ? m.characters : [];
  const assets = Array.isArray(m.assets) ? m.assets : [];
  const scenes = Array.isArray(m.scenes) ? m.scenes : [];
  const captions = Array.isArray(m.captions) ? m.captions : [];
  for (const key of ['characters', 'assets', 'scenes', 'captions']) {
    check(Array.isArray(m[key]), `${key} must be an array`);
  }
  const uniqueIds = (items, kind) => {
    const ids = new Set();
    items.forEach((item, i) => {
      check(object(item) && str(item.id), `${kind}[${i}].id is required`);
      if (object(item)) {
        check(!ids.has(item.id), `duplicate ${kind} id: ${item.id}`);
        ids.add(item.id);
      }
    });
    return ids;
  };
  const characterIds = uniqueIds(characters, 'characters');
  uniqueIds(assets, 'assets');
  uniqueIds(scenes, 'scenes');
  characters.forEach((c, i) => {
    if (!object(c)) return;
    check(str(c.name), `characters[${i}].name is required`);
    for (const key of ['coat', 'skin', 'trousers']) check(color(c[key]), `characters[${i}].${key} must be #RRGGBB`);
    check(finite(c.scale) && c.scale >= 0.5 && c.scale <= 2, `characters[${i}].scale must be 0.5–2`);
  });
  assets.forEach((a, i) => {
    if (!object(a)) return;
    check(['image', 'audio'].includes(a.kind), `assets[${i}].kind must be image or audio`);
    check(str(a.src) && !a.src.startsWith('/') && !a.src.includes('\\') && !a.src.includes(':') &&
      !a.src.includes('?') && !a.src.includes('#') && !a.src.includes('%') &&
      a.src.split('/').every((part) => part !== '..' && part !== '.' && part.length > 0),
      `assets[${i}].src must be a safe public-relative file path`);
    if (a.provenance !== undefined) check(str(a.provenance), `assets[${i}].provenance must be nonempty`);
  });
  const requireAsset = (id, kind, context) => check(assets.some((a) => a?.id === id && a.kind === kind), `${context} must reference a registered ${kind} asset`);
  check(scenes.length > 0 && scenes.length <= 200, 'scenes must contain 1–200 entries');
  scenes.forEach((s, i) => {
    if (!object(s)) return;
    check(TEMPLATES.includes(s.template), `scenes[${i}].template is unsupported`);
    check(Number.isInteger(s.duration_in_frames) && s.duration_in_frames >= 2,
      `scenes[${i}].duration_in_frames must be an integer >= 2`);
    for (const key of ['eyebrow', 'headline', 'body']) check(typeof s[key] === 'string', `scenes[${i}].${key} must be a string`);
    check(typeof s.headline === 'string' && s.headline.length <= 100, `scenes[${i}].headline must be <= 100 characters`);
    check(typeof s.body === 'string' && s.body.length <= 240, `scenes[${i}].body must be <= 240 characters`);
    check(['wide', 'medium', 'detail'].includes(s.camera), `scenes[${i}].camera is unsupported`);
    check(Number.isInteger(s.seed), `scenes[${i}].seed must be an integer`);
    if (s.character_id !== undefined) check(characterIds.has(s.character_id), `scenes[${i}] references an unknown character`);
    if (s.image_asset_id !== undefined) requireAsset(s.image_asset_id, 'image', `scenes[${i}].image_asset_id`);
  });
  const totalFrames = scenes.reduce((sum, s) => sum + (s?.duration_in_frames ?? 0), 0);
  const timelineSeconds = totalFrames / f.fps;
  check(finite(timelineSeconds) && timelineSeconds > 0 && timelineSeconds <= 7200, 'timeline must be positive and at most 2 hours');
  if (m.narration !== null) {
    check(object(m.narration), 'narration must be null or an object');
    if (object(m.narration)) {
      requireAsset(m.narration.asset_id, 'audio', 'narration.asset_id');
      check(m.narration.measured === true, 'narration.measured must be true after real media measurement');
      check(finite(m.narration.duration_seconds) && m.narration.duration_seconds > 0 && m.narration.duration_seconds <= timelineSeconds + 0.05,
        'narration duration must be positive and no longer than the timeline (+0.05s tolerance)');
    }
  }
  if (m.music !== null) {
    check(object(m.music), 'music must be null or an object');
    if (object(m.music)) {
      requireAsset(m.music.asset_id, 'audio', 'music.asset_id');
      check(finite(m.music.volume) && m.music.volume >= 0 && m.music.volume <= 0.5, 'music.volume must be 0–0.5');
    }
  }
  let end = 0;
  captions.forEach((c, i) => {
    if (!object(c)) { errors.push(`captions[${i}] must be an object`); return; }
    check(str(c.text) && c.text.length <= 120, `captions[${i}].text must contain 1–120 characters`);
    check(finite(c.start) && finite(c.end) && c.start >= 0 && c.start >= end - 0.001 && c.end > c.start,
      `captions[${i}] must have positive, ordered, non-overlapping times`);
    check(c.end <= (m.narration?.duration_seconds ?? timelineSeconds) + 0.05, `captions[${i}] extends beyond narration/timeline`);
    end = c.end;
  });
  if (m.demo === false) {
    check(object(m.narration), 'production manifests require measured narration');
    check(captions.length > 0, 'production manifests require captions aligned to the narration');
  }
  return errors;
}

export function assertManifest(value) {
  const errors = validateManifest(value);
  if (errors.length) throw new Error(`Invalid render manifest:\n${errors.map((e) => `- ${e}`).join('\n')}`);
  return value;
}
