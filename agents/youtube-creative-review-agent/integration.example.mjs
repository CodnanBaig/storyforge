import { readFile } from 'node:fs/promises';
import { fingerprintInput, validateReview } from './src/gate.mjs';

/**
 * Supply an adapter to your existing LLM/agent runtime. It must execute tools,
 * honor the structured output schema, and return the final JSON object/string.
 * Calling this function alone does not install or configure a model provider.
 */
export async function reviewCandidate(candidate, { invokeAgent, tools = [] } = {}) {
  if (typeof invokeAgent !== 'function') {
    throw new TypeError('Provide invokeAgent from your project agent runtime.');
  }

  // The checker rejects non-JSON values; this hash covers the complete input.
  const inputSha256 = fingerprintInput(candidate);
  const snapshot = JSON.parse(JSON.stringify(candidate));
  const paths = [
    'youtube-script-creative-review-agent.md',
    'references/rubric.md',
    'references/research-protocol.md',
    'schemas/review.schema.json',
  ];
  const [definition, rubric, research, schemaText] = await Promise.all(
    paths.map((path) => readFile(new URL(path, import.meta.url), 'utf8')),
  );

  const raw = await invokeAgent({
    name: 'youtube-script-creative-reviewer',
    instructions: [definition, rubric, research].join('\n\n'),
    input: {
      host_context: {
        input_sha256: inputSha256,
        now: new Date().toISOString(),
        instruction: 'Review the candidate without changing it. Return only the review JSON. Missing research means BLOCKED.',
      },
      candidate: snapshot,
    },
    tools,
    outputSchema: JSON.parse(schemaText),
  });

  let report;
  try {
    report = typeof raw === 'string' ? JSON.parse(raw) : raw;
  } catch {
    throw new Error('Reviewer did not return valid JSON. Stop the handoff and repair the review output.');
  }

  // Validate against the current object as well, detecting caller edits made
  // during the asynchronous review. A later edit still requires another check.
  return { report, validation: validateReview(candidate, report) };
}
