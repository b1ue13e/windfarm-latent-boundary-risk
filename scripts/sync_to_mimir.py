#!/usr/bin/env python3
"""同步 research-manifest.json 到 Mimir wiki"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

# 读取本地清单
manifest_path = Path(r"E:\论文3\research-manifest.json")
with open(manifest_path, encoding="utf-8") as f:
    manifest = json.load(f)

# 读取 Mimir wiki
wiki_path = Path(r"C:\Users\lidong\AppData\Roaming\DeepSeek Harness Desktop\harness-home\storages\research_wiki.json")
with open(wiki_path, encoding="utf-8") as f:
    wiki = json.load(f)

# 生成项目 ID
project_id = str(uuid.uuid4())
now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

# 构建项目记录
project = {
    "id": project_id,
    "title": manifest["project"]["title"],
    "stage": "experiments",
    "researchQuestion": manifest["question"]["text"],
    "workflowTemplateId": "default-research-v1",
    "currentStageId": f"{project_id}:experiments",
    "researchOutcome": "not_assessed",
    "paperDir": "manuscript",
    "artifacts": [],
    "reviewRounds": 0,
    "updatedAt": now,
}

# 插入项目
wiki["tables"]["projects"][project_id] = project

# 同步 ideas（假设）
for hyp in manifest.get("hypotheses", []):
    idea_id = str(uuid.uuid4())
    idea = {
        "id": idea_id,
        "title": f"假设 {hyp['id']}",
        "hypothesis": hyp["text"],
        "status": "adopted" if hyp["status"] == "testing" else "proposed",
        "projectId": project_id,
        "createdAt": now,
    }
    wiki["tables"]["ideas"][idea_id] = idea

# 同步 experiments
for exp in manifest.get("experiments", []):
    exp_id = str(uuid.uuid4())
    experiment = {
        "id": exp_id,
        "name": exp["title"],
        "projectId": project_id,
        "status": exp["status"],
        "logPath": f"experiments/{exp['id']}/log.md",
        "metrics": {},
        "createdAt": now,
        "updatedAt": exp.get("updatedAt", now),
    }
    wiki["tables"]["experiments"][exp_id] = experiment

# 写回 Mimir wiki
with open(wiki_path, "w", encoding="utf-8") as f:
    json.dump(wiki, f, ensure_ascii=False, indent=2)

print(f"OK: Synced to Mimir")
print(f"  Project ID: {project_id}")
print(f"  Title: {project['title']}")
print(f"  Stage: {project['stage']}")
print(f"  Hypotheses: {len(manifest.get('hypotheses', []))}")
print(f"  Experiments: {len(manifest.get('experiments', []))}")
