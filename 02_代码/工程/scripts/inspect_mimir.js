const fs = require('fs');
const path = 'C:\\Users\\lidong\\AppData\\Roaming\\DeepSeek Harness Desktop\\harness-home\\storages\\research_wiki.json';
const data = JSON.parse(fs.readFileSync(path, 'utf8'));

const projectId = '92ef8db3-9dbc-44f7-b900-5b9b888df563';
const myStages = Object.values(data.tables.research_stages || {})
  .filter(s => s.projectId === projectId)
  .sort((a, b) => a.order - b.order);

console.log(`Project ${projectId} stages (${myStages.length}):`);
for (const s of myStages) {
  console.log(`\nStage ${s.order}: ${s.templateKey} (${s.id})`);
  console.log(`  executionStatus: ${s.executionStatus}, reviewDecision: ${s.reviewDecision}`);
  console.log(`  criteria (${s.acceptanceCriteria.length}):`);
  for (const c of s.acceptanceCriteria) {
    console.log(`    - [${c.status}] ${c.id}`);
  }
}
