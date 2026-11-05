import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { reviewCandidate } from './integration.example.mjs';
import { fingerprintInput } from './src/gate.mjs';

async function examples() {
  const [input, report] = await Promise.all([
    'examples/input.template.json', 'examples/review.blocked.json',
  ].map(async (path) => JSON.parse(await readFile(new URL(path, import.meta.url), 'utf8'))));
  return { input, report };
}

test('adapter supplies full instructions, schema, tools and exact fingerprint', async () => {
  const { input, report } = await examples();
  const tools = [{ name: 'read_only_search_placeholder' }];
  const result = await reviewCandidate(input, {
    tools,
    invokeAgent: async (request) => {
      assert.equal(request.input.host_context.input_sha256, fingerprintInput(input));
      assert.notEqual(request.input.candidate, input);
      assert.deepEqual(request.input.candidate, input);
      assert.equal(request.tools, tools);
      assert.match(request.instructions, /Editorial rubric/);
      assert.match(request.instructions, /YouTube research protocol/);
      assert.ok(request.outputSchema.required.includes('input_sha256'));
      return { ...report, reviewed_at: request.input.host_context.now };
    },
  });
  assert.equal(result.validation.valid, true);
  assert.equal(result.validation.creative_approved, false);
});

test('a caller edit during review invalidates the returned report', async () => {
  const { input, report } = await examples();
  const result = await reviewCandidate(input, {
    invokeAgent: async (request) => {
      input.creative.title = 'Changed while the review was in progress';
      return { ...report, reviewed_at: request.input.host_context.now };
    },
  });
  assert.equal(result.validation.valid, false);
  assert.ok(result.validation.errors.some((error) => /Input changed/.test(error)));
});

test('malformed model output never becomes a passing review', async () => {
  const { input } = await examples();
  await assert.rejects(
    reviewCandidate(input, { invokeAgent: async () => 'APPROVED!' }),
    /did not return valid JSON/,
  );
});
