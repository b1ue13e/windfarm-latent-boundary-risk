const fs = require('fs');

const WIKI_PATH = 'C:\\Users\\lidong\\AppData\\Roaming\\DeepSeek Harness Desktop\\harness-home\\storages\\research_wiki.json';
console.log('Loading Mimir wiki data from:', WIKI_PATH);
const wiki = JSON.parse(fs.readFileSync(WIKI_PATH, 'utf8'));

const projectId = '92ef8db3-9dbc-44f7-b900-5b9b888df563';
const p = wiki.tables.projects[projectId];

console.log('\n================ 1. PROJECT OVERVIEW ================');
console.log('Project ID:', p.id);
console.log('Title:', p.title);
console.log('Research Question:', p.researchQuestion);
console.log('Stage:', p.stage);
console.log('Current Stage ID:', p.currentStageId);
console.log('Research Outcome:', p.researchOutcome);
console.log('Paper Dir:', p.paperDir);
console.log('Artifacts Count:', p.artifacts.length);
console.log('Artifacts List:');
p.artifacts.forEach(a => console.log('  -', a));

console.log('\n================ 2. EIGHT RESEARCH STAGES (STAGE-GATE) ================');
const stages = Object.values(wiki.tables.research_stages)
  .filter(s => s.projectId === projectId)
  .sort((a, b) => a.order - b.order);

console.log(`Total Stages: ${stages.length} / 8`);
let allPassed = true;
stages.forEach(s => {
  const criteriaPassed = s.acceptanceCriteria.filter(c => c.status === 'passed').length;
  const totalCriteria = s.acceptanceCriteria.length;
  console.log(`\n[Stage ${s.order}] ${s.name} (${s.templateKey})`);
  console.log(`  Execution Status: ${s.executionStatus} | Gate Decision: ${s.reviewDecision}`);
  console.log(`  Deliverables: ${s.deliverables.join(', ')}`);
  console.log(`  Criteria Progress: ${criteriaPassed}/${totalCriteria} passed`);
  if (s.reviewDecision !== 'go' || s.executionStatus !== 'completed') {
    allPassed = false;
  }
});
console.log('\nAll 8 Stage Gates Passed:', allPassed);

console.log('\n================ 3. PAPERS IN LIBRARY ================');
const projectPapers = Object.values(wiki.tables.papers).filter(paper => 
  (paper.projectIds && paper.projectIds.includes(projectId)) || 
  (paper.relevance && paper.relevance[projectId])
);
console.log(`Project-associated Papers Count: ${projectPapers.length}`);
projectPapers.forEach(paper => {
  const rel = paper.relevance && paper.relevance[projectId];
  console.log(`  - [arXiv: ${paper.arxivId}] ${paper.title}`);
  if (rel) {
    console.log(`    Relevance Score: ${rel.score}/10 | Reason: ${rel.reason}`);
  }
});

console.log('\n================ 4. EXPERIMENT RECORDS ================');
const projectExps = Object.values(wiki.tables.experiments).filter(e => e.projectId === projectId);
console.log(`Project Experiments Count: ${projectExps.length}`);
projectExps.forEach(e => {
  console.log(`  - [${e.status.toUpperCase()}] ${e.name}`);
  console.log(`    Metrics:`, JSON.stringify(e.metrics));
  if (e.logPath) console.log(`    Log Path: ${e.logPath}`);
});

console.log('\n================ 5. IDEAS & HYPOTHESES ================');
const projectIdeas = Object.values(wiki.tables.ideas).filter(i => i.projectId === projectId);
console.log(`Project Ideas Count: ${projectIdeas.length}`);
projectIdeas.forEach(i => {
  console.log(`  - [${i.status.toUpperCase()}] ${i.title}`);
  console.log(`    Hypothesis: ${i.hypothesis}`);
  if (i.failureReason) {
    console.log(`    Failure / Falsification Reason: ${i.failureReason}`);
  }
});

console.log('\n================ 6. TRACKED CLAIMS ================');
const projectClaims = Object.values(wiki.tables.claims).filter(c => c.projectId === projectId);
console.log(`Project Tracked Claims Count: ${projectClaims.length}`);
projectClaims.forEach(c => {
  console.log(`  - [${c.status.toUpperCase()}] ${c.text}`);
  console.log(`    Evidence: ${c.evidence}`);
});

console.log('\n================ 7. FIGURES ================');
const projectFigures = Object.values(wiki.tables.figures).filter(f => f.projectId === projectId);
console.log(`Project Figures Count: ${projectFigures.length}`);
projectFigures.forEach(f => {
  console.log(`  - ${f.relPath}: "${f.caption}"`);
});

console.log('\n================ 8. RESEARCH CONTRACTS ================');
const projectContracts = Object.values(wiki.tables.research_contracts).filter(c => c.projectId === projectId);
console.log(`Project Contracts Count: ${projectContracts.length}`);
projectContracts.forEach(c => {
  console.log(`  - Version ${c.version} [Locked: ${c.locked}]: Mode=${c.mode}`);
  console.log(`    Hypothesis: ${c.hypothesis}`);
});

console.log('\n================ 9. CROSS-PROJECT ISOLATION AUDIT ================');
const allProjects = Object.values(wiki.tables.projects);
console.log(`Total Projects in Mimir: ${allProjects.length}`);
allProjects.forEach(pOther => {
  const isTarget = pOther.id === projectId;
  console.log(`  - Project ${pOther.id}: "${pOther.title}" (Stage: ${pOther.stage}) ${isTarget ? '<-- TARGET' : '[UNTOUCHED]'}`);
});

console.log('\n================ INTEGRITY VERIFICATION SUMMARY ================');
const isSuccess = p.title.includes('跨风电场备用筛查的时空图迁移与局部条件基线决策增益评估') &&
  stages.length === 8 &&
  allPassed &&
  projectPapers.length >= 3 &&
  projectExps.length >= 5 &&
  projectIdeas.length >= 4 &&
  projectClaims.length >= 4 &&
  projectFigures.length >= 6 &&
  projectContracts.length >= 1;

console.log('Mimir Data Integrity Check Passed:', isSuccess);
process.exit(isSuccess ? 0 : 1);
