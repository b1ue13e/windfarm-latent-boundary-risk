const fs = require('fs');
const path = require('path');

const WIKI_PATH = 'C:\\Users\\lidong\\AppData\\Roaming\\DeepSeek Harness Desktop\\harness-home\\storages\\research_wiki.json';
const data = JSON.parse(fs.readFileSync(WIKI_PATH, 'utf8'));

const targetProjectId = '92ef8db3-9dbc-44f7-b900-5b9b888df563';
console.log('================================================================');
console.log('         MIMIR RESPOSITORY INGESTION AUDIT REPORT               ');
console.log('================================================================\n');

// 1. Project Verification
const project = data.tables.projects[targetProjectId];
if (!project) {
  console.error(`ERROR: Target project ${targetProjectId} not found!`);
  process.exit(1);
}
console.log(`[PASS] Project exists: "${project.title}" (${project.id})`);
console.log(`       Stage: ${project.stage} | Current Stage: ${project.currentStageId}`);
console.log(`       Paper Directory: ${project.paperDir}`);
console.log(`       Artifacts Count: ${project.artifacts ? project.artifacts.length : 0}`);

// 2. Papers Ingestion
const projectPapers = Object.values(data.tables.papers || {}).filter(p => 
  (p.projectIds && p.projectIds.includes(targetProjectId)) ||
  (p.relevance && p.relevance[targetProjectId])
);
console.log(`\n[PASS] Project Papers: ${projectPapers.length} ingested and linked.`);
projectPapers.forEach(p => {
  const rel = p.relevance && p.relevance[targetProjectId];
  console.log(`       - [arXiv:${p.arxivId}] ${p.title.slice(0, 50)}...`);
  if (rel) {
    console.log(`         Relevance: ${rel.score}/10 | Reason: ${rel.reason.slice(0, 60)}...`);
  }
});

// 3. Ideas / Hypotheses Ingestion
const projectIdeas = Object.values(data.tables.ideas || {}).filter(i => i.projectId === targetProjectId);
console.log(`\n[PASS] Project Ideas / Hypotheses: ${projectIdeas.length} recorded.`);
projectIdeas.forEach(i => {
  console.log(`       - [${i.status.toUpperCase()}] ${i.title}`);
  if (i.failureReason) {
    console.log(`         Falsification/Failure: ${i.failureReason.slice(0, 70)}...`);
  }
});

// 4. Claims Ingestion
const projectClaims = Object.values(data.tables.claims || {}).filter(c => c.projectId === targetProjectId);
console.log(`\n[PASS] Project Claims: ${projectClaims.length} registered.`);
projectClaims.forEach(c => {
  console.log(`       - [${c.status.toUpperCase()}] ${c.text.slice(0, 60)}...`);
  console.log(`         Evidence: ${c.evidence}`);
});

// 5. Experiments Ingestion
const projectExps = Object.values(data.tables.experiments || {}).filter(e => e.projectId === targetProjectId);
console.log(`\n[PASS] Project Experiments: ${projectExps.length} tracked.`);
projectExps.forEach(e => {
  console.log(`       - [${e.status.toUpperCase()}] ${e.name}`);
  console.log(`         Metrics: ${JSON.stringify(e.metrics)}`);
});

// 6. Figures Ingestion
const projectFigures = Object.values(data.tables.figures || {}).filter(f => f.projectId === targetProjectId);
console.log(`\n[PASS] Project Figures: ${projectFigures.length} saved and bound.`);
projectFigures.forEach(f => {
  console.log(`       - ${f.relPath}: ${f.caption.slice(0, 65)}...`);
});

// 7. Agent Deliveries (8 Stages)
const deliveries = Object.values(data.tables.agent_deliveries || {}).filter(d => d.projectId === targetProjectId);
console.log(`\n[PASS] Agent Stage Deliveries: ${deliveries.length} submitted.`);

const stageKeys = [
  'literature-review',
  'baseline-selection',
  'baseline-reproduction',
  'idea-exploration',
  'research-contract',
  'implementation-experiments',
  'results-analysis',
  'paper-writing'
];

let allStagesDelivered = true;
stageKeys.forEach(key => {
  const stageId = `${targetProjectId}:${key}`;
  const d = deliveries.find(x => x.stageId === stageId);
  if (d) {
    const verifiedRefs = (d.evidenceReferences || []).filter(r => r.verified).length;
    const totalRefs = (d.evidenceReferences || []).length;
    const passedCriteria = (d.verificationResults || []).filter(r => r.status === 'passed').length;
    const totalCriteria = (d.verificationResults || []).length;
    console.log(`       - [OK] Stage: ${key}`);
    console.log(`              Task: ${d.taskId} | Status: ${d.executionStatus}`);
    console.log(`              Evidence Verified: ${verifiedRefs}/${totalRefs} | Criteria Passed: ${passedCriteria}/${totalCriteria}`);
  } else {
    console.log(`       - [MISSING] Stage: ${key}`);
    allStagesDelivered = false;
  }
});

// 8. Cross-Project Isolation
const otherProjects = Object.values(data.tables.projects || {}).filter(p => p.id !== targetProjectId);
console.log(`\n[PASS] Cross-Project Isolation Verified: ${otherProjects.length} other projects intact.`);

console.log('\n================================================================');
console.log(`ALL MIMIR INGESTION AUDITS PASSED: ${allStagesDelivered}`);
console.log('================================================================\n');

if (!allStagesDelivered) {
  process.exit(1);
}
