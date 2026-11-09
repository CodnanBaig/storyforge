import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {validateManifest} from '../src/validate.mjs';

const fixture = JSON.parse(fs.readFileSync(new URL('../examples/unified-2d-demo.json', import.meta.url), 'utf8'));
const base = fixture.manifest ?? fixture;

test('a deterministic 2D action plan has valid scene coordinates and action names', () => {
  assert.deepEqual(validateManifest(base), []);
  assert.equal(base.demo, true, 'example should remain labelled a silent demo');
});

test('reject unknown 2D actions', () => {
  const candidate = structuredClone(base);
  candidate.scenes[0].actor_2d.action = 'teleport';
  const errors = validateManifest(candidate);
  assert.ok(errors.some((e) => e.includes('actor_2d.action')));
});

test('reject out-of-range actor coordinates and invalid scales', () => {
  const candidate = structuredClone(base);
  candidate.scenes[0].actor_2d.x_from = -0.2;
  candidate.scenes[0].actor_2d.scale = 0;
  const errors = validateManifest(candidate);
  assert.ok(errors.some((e) => e.includes('actor_2d.x_from')));
  assert.ok(errors.some((e) => e.includes('actor_2d.scale')));
});
