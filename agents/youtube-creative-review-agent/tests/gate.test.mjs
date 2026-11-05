/**
 * Synthetic metadata fixtures only. These do not represent researched stories,
 * real YouTube observations, editorial approval, or predicted performance.
 * Fictional YouTube IDs exist only in in-memory tests and temporary CLI inputs.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {fingerprintInput,validateReview,assertCreativeApproved,WEIGHTS,GATES} from '../src/gate.mjs';

const ROOT = fileURLToPath(new URL('../',import.meta.url));
const CLI = join(ROOT,'src/gate.mjs');
const NOW = new Date('2026-11-06T08:00:00Z');
const DAY = 86400000;
const template = JSON.parse(readFileSync(join(ROOT,'examples/input.template.json'),'utf8'));
const iso = value => new Date(value).toISOString();
const total = review => Math.round(Object.entries(WEIGHTS).reduce((sum,[key,weight]) => sum + review.scores[key].score / 5 * weight,0) * 10) / 10;
function fixture(now = NOW) {
  const input = structuredClone(template);
  input.is_example = false;
  input.episode_id = 'synthetic-metadata-test-only';
  input.research_brief = {mode:'recent_trend',audience_fit:'Synthetic test of the declared channel audience.',query_seeds:['Synthetic query, never executed']};
  const lines = [
    'This is a synthetic story used only to exercise a metadata guard, with no claim about a real event.',
    'Its invented sequence describes a lamp revealing an object, a map showing a route, and a final explanation that answers the opening question.',
    'The example cannot establish factual truth, audience demand, legal rights, genuine research, or future views. Its artificial sources and observations exist only inside automated tests so that missing evidence, stale approvals, changed inputs, and invalid decisions can be detected reliably before integration into another project.'
  ];
  input.script = {text:lines.join(' '),claim_links:[{text:lines[0],source_ids:['source-a','source-b']}]};
  input.creative = {
    title:'Synthetic test only',description:'A mechanics-only test, never a publishable episode.',
    opening_frame:'A test lamp points toward a test object.',payoff:'The synthetic narrative has a complete final explanation.',
    storyboard:lines.map((line,i) => ({id:'scene-'+i,start_seconds:[0,14,28][i],end_seconds:[14,28,43][i],visual:'Synthetic fixture scene',action:'Reveal a different relevant test element',narration:line})),
    style_notes:'Original fixture geometry; not media production.',sound_plan:'Synthetic plan for intelligible narration.',caption_plan:'Readable synchronized captions are planned.'
  };
  input.sources = ['a','b'].map(letter => ({
    id:'source-'+letter,url:'https://example.'+(letter === 'a' ? 'com' : 'org')+'/fictional-source',
    accessed_at:iso(+now-3600000),origin_key:'fictional-origin-'+letter,read_confirmed:true,
    evidence_note:'Synthetic declared evidence; no page was read and no factual approval is represented.'
  }));
  const ids = Array.from({length:6},(_,i) => 'TEST'+String(i+1).padStart(7,'0'));
  const report = {
    schema_version:'1.0',episode_id:input.episode_id,input_sha256:fingerprintInput(input),
    reviewed_at:iso(now),reviewer:'Automated synthetic-fixture test',decision:'APPROVE',
    summary:'Metadata fixture only; not a genuine researched creative approval.',
    research:{
      mode:'recent_trend',completed:true,
      queries:[{query:'Synthetic unexecuted query',searched_at:iso(now),notes:'Test metadata only.'}],
      comparables:ids.map((id,i) => ({
        id,url:'https://www.youtube.com/shorts/'+id,channel_id:'fixture-channel-'+Math.floor(i/2),
        title:'Synthetic video '+i,published_at:iso(+now-[10,20,40,50,60,80][i]*DAY),
        observed_at:iso(now),duration_seconds:43,public_views:(i+1)*1000,language:'en',format_match:true,
        selection:i < 2 ? 'recent_ordinary' : 'breakout_candidate',inspection:'metadata',
        evidence_url:'https://www.youtube.com/shorts/'+id,relevance:'Synthetic audience match.',
        limits:'No actual observation, video inspection or retention data; fixture only.'
      })),
      findings:['Synthetic demand evidence only.'],counterevidence:['Ordinary fixture counts are below the highest fixture count.'],
      limitations:['No real YouTube data was collected.'],evidence_confidence:'medium'
    },
    scores:Object.fromEntries(Object.keys(WEIGHTS).map(key => [key,{score:5,rationale:'Synthetic rubric evidence for guard testing only.',evidence_refs:['input:script','comparable:'+ids[0]]}])),
    total_score:100,
    gates:Object.fromEntries(GATES.map(key => [key,{status:'pass',rationale:'Synthetic declared gate result.',evidence_refs:['source:source-a','input:creative']}])),
    timing:{word_count:input.script.text.split(/\s+/u).length,estimated_min_seconds:40,estimated_max_seconds:43,method:'Synthetic total-screen-time estimate including speech, pauses and final hold; not a measured voice track.',measured_audio_seconds:null},
    issues:[],revision_brief:{required_changes:[],alternative_hooks:[],script_patch:null,visual_changes:[]},
    performance_outlook:{potential:'strong',success_probability:null,qualified_view_forecast:null,reason:'Synthetic qualitative field, not a real outlook.',assumptions:['All observations are intentionally artificial test fixtures.']},
    media_authorized:false,publication_authorized:false
  };
  return {input,report};
}
function denied(input, report, pattern, now = NOW) {
  const result = validateReview(input,report,{now});
  assert.equal(result.creative_approved,false);
  assert.equal(result.media_authorized,false);
  assert.equal(result.publication_authorized,false);
  if (pattern) assert.match(result.errors.join(' '),pattern);
  return result;
}

test('complete synthetic metadata passes only the creative handoff',() => {
  const {input,report} = fixture();
  const result = assertCreativeApproved(input,report,{now:NOW});
  assert.equal(result.valid,true); assert.equal(result.creative_approved,true);
  assert.equal(result.recomputed_score,100); assert.equal(result.eligible_comparable_count,6);
  assert.equal(result.media_authorized,false); assert.equal(result.publication_authorized,false);
});
test('canonical hash is key-order independent, content-sensitive and JSON-only',() => {
  assert.equal(fingerprintInput({b:2,a:{y:1,x:0}}),fingerprintInput({a:{x:0,y:1},b:2}));
  assert.notEqual(fingerprintInput({a:['x','y']}),fingerprintInput({a:['y','x']}));
  assert.notEqual(fingerprintInput({script:'A B'}),fingerprintInput({script:'A  B'}));
  for (const item of [undefined,NaN,Infinity,{x:undefined},{x:BigInt(1)},new Date()]) assert.throws(() => fingerprintInput(item));
  const circular = {}; circular.self = circular; assert.throws(() => fingerprintInput(circular));
});
test('templates, missing reports and supplied blocked example fail closed',() => {
  const {input,report} = fixture(); input.is_example = true; report.input_sha256=fingerprintInput(input);
  denied(input,report,/Examples and templates/);
  input.is_example = false; input.is_template = true; report.input_sha256=fingerprintInput(input);
  denied(input,report,/Examples and templates/);
  assert.doesNotThrow(() => denied(input,null,/wrong JSON type/));
  const blocked = JSON.parse(readFileSync(join(ROOT,'examples/review.blocked.json'),'utf8'));
  const result=validateReview(template,blocked);
  assert.equal(result.valid,true,JSON.stringify(result.errors)); assert.equal(result.creative_approved,false);
});
test('score and required criterion floors cannot be bypassed',() => {
  let {input,report}=fixture();
  for (const key of Object.keys(WEIGHTS)) report.scores[key].score=3;
  report.total_score=total(report);
  denied(input,report,/at least 85/);
  ({input,report}=fixture()); report.scores.hook.score=3; report.total_score=total(report);
  assert.equal(report.total_score,94); denied(input,report,/hook is below/);
  ({input,report}=fixture()); report.total_score=99; denied(input,report,/recomputed weighted score/);
});
test('a high score cannot overrule major issues or failed hard gates',() => {
  let {input,report}=fixture();
  report.issues=[{severity:'major',location:'script',problem:'Synthetic unresolved problem.',fix:'Resolve the test issue.',evidence_refs:['input:script']}];
  denied(input,report,/major or blocker/);
  ({input,report}=fixture()); report.gates.complete_payoff.status='fail';
  denied(input,report,/complete_payoff must pass/);
});
test('missing, stale or mismatched research blocks approval',() => {
  let {input,report}=fixture(); report.research.comparables.pop();
  denied(input,report,/Insufficient current research/);
  ({input,report}=fixture()); report.research.comparables[0].observed_at=iso(+NOW-8*DAY);
  denied(input,report,/Insufficient current research/);
  ({input,report}=fixture()); report.research.mode='evergreen';
  denied(input,report,/mode must match/);
  ({input,report}=fixture()); report.research.comparables[0].url='https://www.youtube.com/shorts/OTHER000001';
  denied(input,report,/same YouTube video/);
});
test('evergreen evidence can qualify at180days while the90day trend mode cannot',() => {
  const {input,report}=fixture();
  input.research_brief.mode='evergreen'; report.research.mode='evergreen';
  [10,80,100,120,150,175].forEach((age,i) => { report.research.comparables[i].published_at=iso(+NOW-age*DAY); });
  report.input_sha256=fingerprintInput(input);
  assert.equal(validateReview(input,report,{now:NOW}).creative_approved,true);
  input.research_brief.mode='recent_trend'; report.research.mode='recent_trend'; report.input_sha256=fingerprintInput(input);
  denied(input,report,/Insufficient current research/);
});
test('stale extra comparables cannot be retained as approval evidence',() => {
  const {input,report}=fixture();
  const extra=structuredClone(report.research.comparables[0]);
  extra.id='TEST0000007'; extra.url='https://www.youtube.com/shorts/'+extra.id;
  extra.evidence_url=extra.url; extra.observed_at=iso(+NOW-8*DAY);
  report.research.comparables.push(extra);
  const result=denied(input,report,/older than seven days/);
  assert.equal(result.eligible_comparable_count,6);
});
test('research samples need independent channels, recent ordinary observations and comparable durations',() => {
  let {input,report}=fixture(); report.research.comparables.forEach(c => { c.channel_id='one-channel'; });
  denied(input,report,/Insufficient current research/);
  ({input,report}=fixture()); report.research.comparables.forEach(c => { c.selection='breakout_candidate'; });
  denied(input,report,/Insufficient current research/);
  ({input,report}=fixture()); report.research.comparables[0].duration_seconds=36000;
  denied(input,report,/Insufficient current research/);
});
test('changed script, storyboard, title and context invalidate the old fingerprint',() => {
  for (const mutate of [
    i => { i.script.text+=' Changed.'; },
    i => { i.creative.storyboard[0].visual='Changed visual'; },
    i => { i.creative.title='Changed title'; },
    i => { i.rights_context.intended_use='commercial_draft'; }
  ]) {
    const {input,report}=fixture(); mutate(input); denied(input,report,/Input changed/);
  }
});
test('stale approval, fabricated probability and claimed authorization fail',() => {
  let {input,report}=fixture(); denied(input,report,/older than 24 hours/,new Date(+NOW+25*3600000));
  ({input,report}=fixture()); report.performance_outlook.success_probability=0.95;
  denied(input,report,/success_probability must equal null/);
  ({input,report}=fixture()); report.media_authorized=true;
  denied(input,report,/media_authorized must equal false/);
});
test('invalid source URLs and unresolved references are clean denials, not crashes',() => {
  let {input,report}=fixture(); input.sources[0].url='not a URL'; report.input_sha256=fingerprintInput(input);
  assert.doesNotThrow(() => denied(input,report,/HTTP/));
  ({input,report}=fixture()); report.scores.hook.evidence_refs=['source:missing'];
  denied(input,report,/unresolved evidence/);
});
test('timing and storyboard must agree with the exact reviewed script',() => {
  let {input,report}=fixture(); report.timing.estimated_max_seconds=44;
  denied(input,report,/feasible timing estimate/);
  ({input,report}=fixture()); input.creative.storyboard[0].narration='Different words'; report.input_sha256=fingerprintInput(input);
  denied(input,report,/reproduce the complete script/);
  ({input,report}=fixture()); report.timing.word_count++;
  denied(input,report,/word_count must match/);
});
test('unknown outlook, incomplete revisions and malformed input never approve',() => {
  let {input,report}=fixture(); report.performance_outlook.potential='unknown';
  denied(input,report,/qualitative performance outlook/);
  ({input,report}=fixture()); report.decision='REVISE';
  denied(input,report,/explicit issue|required changes/);
  assert.doesNotThrow(() => denied({},{}));
  assert.throws(() => assertCreativeApproved({},{}));
});
test('CLI returns clear JSON and exit codes for malformed files, missing reports and fingerprints',() => {
  const directory=mkdtempSync(join(tmpdir(),'creative-review-test-'));
  try {
    const inputPath=join(directory,'input.json'),reviewPath=join(directory,'review.json');
    const {input,report}=fixture(new Date()); writeFileSync(inputPath,JSON.stringify(input)); writeFileSync(reviewPath,JSON.stringify(report));
    let result=spawnSync(process.execPath,[CLI,'fingerprint',inputPath],{encoding:'utf8'});
    assert.equal(result.status,0); assert.equal(JSON.parse(result.stdout).creative_approved,false);
    result=spawnSync(process.execPath,[CLI,'check',inputPath,reviewPath],{encoding:'utf8'});
    assert.equal(result.status,0,result.stdout); assert.equal(JSON.parse(result.stdout).creative_approved,true);
    result=spawnSync(process.execPath,[CLI,'check',inputPath],{encoding:'utf8'});
    assert.equal(result.status,1); assert.equal(JSON.parse(result.stdout).creative_approved,false);
    writeFileSync(reviewPath,'{ invalid JSON');
    result=spawnSync(process.execPath,[CLI,'check',inputPath,reviewPath],{encoding:'utf8'});
    assert.equal(result.status,1); assert.equal(JSON.parse(result.stdout).valid,false);
    result=spawnSync(process.execPath,[CLI,'check',inputPath,join(directory,'absent.json')],{encoding:'utf8'});
    assert.equal(result.status,1); assert.equal(JSON.parse(result.stdout).creative_approved,false);
  } finally { rmSync(directory,{recursive:true,force:true}); }
});
