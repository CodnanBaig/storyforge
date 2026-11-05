#!/usr/bin/env node
/**
 * Deterministic metadata guard, not an LLM, trend predictor, fact checker or
 * YouTube/publishing approval. Full input is fingerprinted with sorted object
 * keys; arrays and string bytes keep their order/content. JSON-only values.
 * Review freshness (24h) and research freshness (7d) are project rules.
 */
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';

export const WEIGHTS = Object.freeze({
  topic_demand:15, hook:15, clarity:10, narrative:10, payoff:15,
  visual:10, originality:10, packaging:5, audio_captions:5, channel_fit:5
});
export const GATES = Object.freeze([
  'factual_support','originality','complete_payoff','timing_feasibility',
  'visual_feasibility','truthful_packaging'
]);
const CRITICAL = ['hook','payoff','visual','originality'];
const DAY = 86400000, TOLERANCE = 300000;
const INPUT_SCHEMA = JSON.parse(readFileSync(new URL('../schemas/input.schema.json', import.meta.url), 'utf8'));
const REVIEW_SCHEMA = JSON.parse(readFileSync(new URL('../schemas/review.schema.json', import.meta.url), 'utf8'));
const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const hasText = value => typeof value === 'string' && value.trim().length > 0;
const normalizedText = value => value.trim().replace(/\s+/gu, ' ');
const wordCount = value => value.trim() ? value.trim().split(/\s+/u).length : 0;

function canonical(value, active = new Set()) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (typeof value !== 'object' || active.has(value)) throw new TypeError('Input must contain only finite, acyclic JSON values.');
  if (!Array.isArray(value) && ![Object.prototype, null].includes(Object.getPrototypeOf(value))) throw new TypeError('Only plain JSON objects are supported.');
  active.add(value);
  const encoded = Array.isArray(value)
    ? '[' + Array.from(value, item => canonical(item, active)).join(',') + ']'
    : '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key], active)).join(',') + '}';
  active.delete(value);
  return encoded;
}

export function fingerprintInput(input) {
  return createHash('sha256').update(canonical(input), 'utf8').digest('hex');
}

/* Implements the structural keywords used by this package's two local schemas.
 * This is deliberately not an arbitrary JSON Schema implementation.
 */
function schemaErrors(value, schema, path, errors) {
  if (errors.length >= 100) return;
  if ('const' in schema && value !== schema.const) errors.push(path + ' must equal ' + JSON.stringify(schema.const) + '.');
  if (schema.enum && !schema.enum.includes(value)) errors.push(path + ' has an unsupported value.');
  const matches = type => ({
    null:value === null, object:isObject(value), array:Array.isArray(value),
    string:typeof value === 'string', boolean:typeof value === 'boolean',
    number:typeof value === 'number' && Number.isFinite(value),
    integer:typeof value === 'number' && Number.isInteger(value)
  })[type];
  if (schema.type && ![schema.type].flat().some(matches)) {
    errors.push(path + ' has the wrong JSON type.'); return;
  }
  if (typeof value === 'number') {
    if (schema.minimum !== undefined && value < schema.minimum) errors.push(path + ' is below its minimum.');
    if (schema.maximum !== undefined && value > schema.maximum) errors.push(path + ' exceeds its maximum.');
  }
  if (typeof value === 'string') {
    if (schema.minLength !== undefined && value.length < schema.minLength) errors.push(path + ' must not be empty.');
    if (schema.pattern && !new RegExp(schema.pattern).test(value)) errors.push(path + ' has an invalid format.');
  }
  if (Array.isArray(value)) value.forEach((item, i) => schemaErrors(item, schema.items || {}, path + '[' + i + ']', errors));
  if (isObject(value)) {
    for (const key of schema.required || []) if (!Object.hasOwn(value, key)) errors.push(path + '.' + key + ' is required.');
    for (const [key, item] of Object.entries(value)) {
      if (schema.properties?.[key]) schemaErrors(item, schema.properties[key], path + '.' + key, errors);
      else if (schema.additionalProperties === false) errors.push(path + '.' + key + ' is not an allowed field.');
    }
  }
}

function timestamp(value, allowDateOnly = false) {
  if (typeof value !== 'string') return NaN;
  const isDate = /^\d{4}-\d{2}-\d{2}$/u.test(value);
  if (!(allowDateOnly && isDate) && !/T.*(?:Z|[+-]\d{2}:\d{2})$/u.test(value)) return NaN;
  const parsed = Date.parse(value);
  if (isDate && Number.isFinite(parsed) && new Date(parsed).toISOString().slice(0,10) !== value) return NaN;
  return parsed;
}
function httpUrl(value) {
  try { const u = new URL(value); return ['https:','http:'].includes(u.protocol) && !u.username && !u.password; }
  catch { return false; }
}
function videoId(value) {
  try {
    const u = new URL(value), host = u.hostname.toLowerCase();
    if (u.protocol !== 'https:' || u.username || u.password) return null;
    if (host === 'youtu.be') return u.pathname.split('/')[1];
    if (!['youtube.com','www.youtube.com','m.youtube.com'].includes(host)) return null;
    if (u.pathname === '/watch') return u.searchParams.get('v');
    if (u.pathname.startsWith('/shorts/')) return u.pathname.split('/')[2];
    return null;
  } catch { return null; }
}
function atPath(value, path) {
  for (const key of path.split('.')) {
    if (!value || typeof value !== 'object' || !Object.hasOwn(value, key)) return undefined;
    value = value[key];
  }
  return value;
}
function baseResult(errors, decision = null, score = null, comparableCount = 0) {
  const valid = errors.length === 0;
  return {
    valid, creative_approved:valid && decision === 'APPROVE', decision,
    recomputed_score:score, eligible_comparable_count:comparableCount,
    media_authorized:false, publication_authorized:false, errors
  };
}

export function validateReview(input, review, {now = new Date()} = {}) {
  const errors = [];
  const need = (condition, message) => { if (!condition) errors.push(message); };
  let expectedHash;
  try {
    expectedHash = fingerprintInput(input);
    fingerprintInput(review);
    schemaErrors(input, INPUT_SCHEMA, 'input', errors);
    schemaErrors(review, REVIEW_SCHEMA, 'review', errors);
  } catch (error) { errors.push(error.message); }
  if (errors.length) return baseResult(errors, review?.decision || null);
  const nowMs = new Date(now).getTime(), reviewed = timestamp(review.reviewed_at);
  const approving = review.decision === 'APPROVE';
  need(Number.isFinite(nowMs), 'now must be a valid timestamp.');
  need(Number.isFinite(reviewed) && reviewed <= nowMs + TOLERANCE, 'reviewed_at must be a timezone-aware timestamp, not in the future.');
  if (approving) need(reviewed >= nowMs - DAY, 'Approval is older than 24 hours; rerun the review.');
  need(review.input_sha256 === expectedHash, 'Input changed or input_sha256 is incorrect; review this exact input again.');
  need(review.episode_id === input.episode_id, 'Review episode_id does not match the input.');
  need(hasText(review.reviewer) && hasText(review.summary), 'Reviewer and summary must be meaningful nonempty strings.');
  need(review.research.mode === input.research_brief.mode, 'Research mode must match the input; do not change it to pass.');

  const sourceIds = new Set(input.sources.map(s => s.id));
  need(sourceIds.size === input.sources.length, 'Source IDs must be unique.');
  const comparableIds = new Set(review.research.comparables.map(c => c.id));
  function referenceExists(ref) {
    const split = ref.indexOf(':'), prefix = ref.slice(0, split), id = ref.slice(split + 1);
    if (split < 1 || !id) return false;
    if (prefix === 'source') return sourceIds.has(id);
    if (prefix === 'comparable') return comparableIds.has(id);
    if (prefix === 'input') return atPath(input, id) !== undefined;
    if (prefix === 'research') return atPath(review.research, id) !== undefined;
    return false;
  }
  function checkEvidence(entry, label, required) {
    need(hasText(entry.rationale), label + ' needs a rationale.');
    if (required) need(entry.evidence_refs.length > 0, label + ' needs evidence references.');
    for (const ref of entry.evidence_refs) need(referenceExists(ref), label + ' has an unresolved evidence reference: ' + ref);
  }
  for (const key of Object.keys(WEIGHTS)) checkEvidence(review.scores[key], 'scores.' + key, review.scores[key].score !== null);
  for (const key of GATES) checkEvidence(review.gates[key], 'gates.' + key, review.gates[key].status === 'pass');
  for (const issue of review.issues) {
    need([issue.location,issue.problem,issue.fix].every(hasText), 'Each issue needs a location, problem and actionable fix.');
    for (const ref of issue.evidence_refs) need(referenceExists(ref), 'Issue has an unresolved evidence reference: ' + ref);
  }
  for (const source of input.sources) {
    need(httpUrl(source.url), 'Source ' + source.id + ' needs a public HTTP(S) evidence URL without credentials.');
    const accessed = timestamp(source.accessed_at);
    need(Number.isFinite(accessed) && accessed <= reviewed + TOLERANCE, 'Source ' + source.id + ' has an invalid/future accessed_at.');
  }

  const allScored = Object.keys(WEIGHTS).every(key => review.scores[key].score !== null);
  const score = allScored ? Math.round(Object.entries(WEIGHTS).reduce((sum,[key,weight]) => sum + review.scores[key].score / 5 * weight,0) * 10) / 10 : null;
  need(review.total_score === score, 'total_score must equal the recomputed weighted score, or null if any rating is unknown.');
  if (review.decision !== 'BLOCKED') need(allScored, 'Only BLOCKED may contain unknown scores.');
  const withinWeek = value => {
    const time = timestamp(value);
    return Number.isFinite(time) && time >= reviewed - 7 * DAY && time <= reviewed + TOLERANCE;
  };
  const maxDays = review.research.mode === 'recent_trend' ? 90 : 180;
  const recentDays = review.research.mode === 'recent_trend' ? 30 : 90;
  const qualified = new Map(), channelsByVideo = new Map();
  for (const c of review.research.comparables) {
    const published = timestamp(c.published_at, true), observed = timestamp(c.observed_at);
    need(videoId(c.url) === c.id, 'Comparable ' + c.id + ' URL must identify the same YouTube video.');
    need(httpUrl(c.evidence_url), 'Comparable ' + c.id + ' needs an accessible evidence URL without credentials.');
    need(Number.isFinite(published) && Number.isFinite(observed) && published <= observed + TOLERANCE && observed <= reviewed + TOLERANCE, 'Comparable ' + c.id + ' has inconsistent dates.');
    if (approving) need(withinWeek(c.observed_at), 'Comparable ' + c.id + ' observation is older than seven days; refresh it before approval.');
    if (channelsByVideo.has(c.id)) need(channelsByVideo.get(c.id) === c.channel_id, 'A video cannot have conflicting channel IDs.');
    channelsByVideo.set(c.id, c.channel_id);
    const eligible = withinWeek(c.observed_at) && published >= reviewed - maxDays * DAY &&
      Number.isInteger(c.public_views) && c.public_views >= 0 &&
      typeof c.duration_seconds === 'number' && c.duration_seconds >= input.constraints.duration_min_seconds * 0.5 && c.duration_seconds <= input.constraints.duration_max_seconds * 1.5 &&
      c.language.toLowerCase() === input.channel.language.toLowerCase() && c.format_match &&
      [c.title,c.channel_id,c.relevance,c.limits].every(hasText);
    if (eligible && (!qualified.has(c.id) || timestamp(qualified.get(c.id).observed_at) < observed)) qualified.set(c.id,c);
  }
  const comps = [...qualified.values()];
  const hasCoverage = comps.length >= 6 &&
    new Set(comps.map(c => c.channel_id.toLowerCase())).size >= 3 &&
    comps.filter(c => timestamp(c.published_at,true) >= reviewed - recentDays * DAY).length >= 2 &&
    comps.filter(c => c.selection === 'recent_ordinary').length >= 2;
  const queryEvidence = review.research.queries.length > 0 && review.research.queries.every(q => hasText(q.query) && hasText(q.notes) && withinWeek(q.searched_at));
  const researchReady = review.research.completed && hasCoverage && queryEvidence &&
    [review.research.findings,review.research.counterevidence,review.research.limitations].every(a => a.length > 0 && a.every(hasText)) &&
    ['medium','high'].includes(review.research.evidence_confidence);
  if (!researchReady) need(review.decision === 'BLOCKED', 'Insufficient current research requires BLOCKED: six eligible videos, three channels, two recent, two ordinary, fresh query evidence, findings, counterevidence and limitations.');
  if (review.decision !== 'BLOCKED' && score !== null) {
    if (score < 70) need(review.decision === 'REJECT', 'A completed review below 70 must REJECT.');
    if (score >= 70 && review.decision === 'REJECT') need(review.issues.some(i => i.severity === 'blocker' && i.evidence_refs.length > 0), 'REJECT at 70+ needs an evidenced fatal blocker.');
  }
  if (['REVISE','REJECT','BLOCKED'].includes(review.decision)) need(review.issues.length > 0, 'A nonapproval decision needs at least one explicit issue.');
  if (['REVISE','BLOCKED'].includes(review.decision)) need(review.revision_brief.required_changes.length > 0, 'REVISE/BLOCKED must specify required changes or evidence to obtain.');
  if (review.timing.word_count !== null) need(review.timing.word_count === wordCount(input.script.text), 'timing.word_count must match the whitespace-delimited script word count.');

  if (approving) {
    need(input.is_example === false && input.is_template !== true, 'Examples and templates cannot receive creative approval.');
    need(score !== null && score >= 85, 'APPROVE requires a weighted score of at least 85/100.');
    for (const key of Object.keys(WEIGHTS)) need(review.scores[key].score >= (CRITICAL.includes(key) ? 4 : 3), key + ' is below its approval floor.');
    for (const key of GATES) need(review.gates[key].status === 'pass', key + ' must pass.');
    need(!review.issues.some(i => ['major','blocker'].includes(i.severity)), 'APPROVE cannot contain major or blocker issues.');
    need(review.revision_brief.required_changes.length === 0 && review.revision_brief.script_patch === null, 'An approval cannot include required edits or an unreviewed replacement script.');
    need([input.script.text,input.research_brief.audience_fit,input.creative.title,input.creative.description,input.creative.opening_frame,input.creative.payoff,input.creative.style_notes,input.creative.sound_plan,input.creative.caption_plan].every(hasText), 'Approval requires a complete script, audience rationale, packaging and creative plan.');
    need(input.constraints.visual_stack.length > 0 && input.research_brief.query_seeds.length > 0, 'Visual stack and research query seeds are required.');
    const confirmed = input.sources.filter(s => s.read_confirmed && httpUrl(s.url) && hasText(s.origin_key) && hasText(s.evidence_note));
    const origins = new Set(confirmed.map(s => s.origin_key.trim().toLowerCase()));
    const urls = new Set(confirmed.map(s => { const u = new URL(s.url); return u.origin + u.pathname.replace(/\/$/u,''); }));
    need(origins.size >= 2 && urls.size >= 2, 'Approval requires two confirmed independent factual reporting origins and distinct source URLs.');
    const confirmedIds = new Set(confirmed.map(s => s.id));
    need(input.script.claim_links.length > 0, 'A factual script needs claim-to-source links.');
    for (const claim of input.script.claim_links) {
      need(hasText(claim.text) && normalizedText(input.script.text).includes(normalizedText(claim.text)), 'Each claim link must quote an actual script span.');
      need(claim.source_ids.length > 0 && claim.source_ids.every(id => confirmedIds.has(id)), 'Each claim must reference confirmed source IDs.');
    }
    const min = input.constraints.duration_min_seconds, max = input.constraints.duration_max_seconds;
    need(min > 0 && max >= min, 'Duration bounds must be positive and ordered.');
    const scenes = input.creative.storyboard;
    need(scenes.length > 0, 'Approval requires a timed storyboard.');
    need(new Set(scenes.map(s => s.id)).size === scenes.length, 'Storyboard scene IDs must be unique.');
    let end = 0;
    for (const scene of scenes) {
      need(Math.abs(scene.start_seconds - end) < 0.000001 && scene.end_seconds > scene.start_seconds, 'Storyboard scenes must be contiguous from zero with positive durations.');
      need(hasText(scene.visual) && hasText(scene.action), 'Every scene needs a visual and purposeful action.');
      end = scene.end_seconds;
    }
    need(end >= min && end <= max, 'Storyboard end must fit the configured duration range.');
    need(normalizedText(scenes.map(s => s.narration).join(' ')) === normalizedText(input.script.text), 'Storyboard narration must reproduce the complete script without extra words.');
    const t = review.timing;
    need(t.word_count !== null && t.word_count > 0 && typeof t.estimated_min_seconds === 'number' && t.estimated_min_seconds > 0 &&
      typeof t.estimated_max_seconds === 'number' && t.estimated_max_seconds >= t.estimated_min_seconds && t.estimated_max_seconds <= end && t.estimated_max_seconds <= max &&
      hasText(t.method), 'Approval requires an explained, feasible timing estimate; actual voice duration is not yet verified.');
    need(review.performance_outlook.potential !== 'unknown' && hasText(review.performance_outlook.reason) && review.performance_outlook.assumptions.length > 0 && review.performance_outlook.assumptions.every(hasText), 'Approval requires an explained, qualitative performance outlook and explicit assumptions.');
  }
  return baseResult(errors, review.decision, score, comps.length);
}

export function assertCreativeApproved(input, review, options) {
  const result = validateReview(input, review, options);
  if (!result.creative_approved) {
    const error = new Error('Creative handoff denied: ' + (result.errors.join(' ') || 'Decision is ' + result.decision + '.'));
    error.result = result; throw error;
  }
  return result;
}

function cli() {
  const [command,inputPath,reviewPath,...extra] = process.argv.slice(2);
  try {
    if (!['fingerprint','check'].includes(command) || !inputPath || extra.length || (command === 'check' && !reviewPath) || (command === 'fingerprint' && reviewPath)) throw new Error('Usage: node src/gate.mjs fingerprint input.json | check input.json review.json');
    const input = JSON.parse(readFileSync(inputPath,'utf8'));
    const result = command === 'fingerprint'
      ? {input_sha256:fingerprintInput(input),creative_approved:false,media_authorized:false,publication_authorized:false}
      : validateReview(input,JSON.parse(readFileSync(reviewPath,'utf8')));
    console.log(JSON.stringify(result,null,2));
    process.exitCode = command === 'fingerprint' || result.creative_approved ? 0 : 1;
  } catch (error) {
    console.log(JSON.stringify({valid:false,creative_approved:false,media_authorized:false,publication_authorized:false,errors:[error.message]},null,2));
    process.exitCode = 1;
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) cli();
