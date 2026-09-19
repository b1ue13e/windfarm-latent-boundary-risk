#!/usr/bin/env python3
"""Read-only structural preflight for an Obsidian course and its assignments."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


IGNORED_PARTS = {
    ".git",
    ".obsidian",
    ".recovery-hold",
    ".reasonix",
    ".tmp",
    ".pytest_cache",
    "__pycache__",
    ".归档",
    "🗄️ 归档",
}
STUDY_REQUIRED = ("type", "topic", "course", "created", "status", "stage_moc", "flow", "kind")
ASSIGNMENT_REQUIRED = (
    "type",
    "project_type",
    "course",
    "assignment_id",
    "assignment_level",
    "assignment_format",
    "stage_id",
    "requires",
    "source_type",
    "created",
    "status",
    "flow",
)
LEVEL_DIRS = {"lesson": "课后作业", "stage": "阶段作业", "capstone": "大作业"}
VALID_FORMATS = {
    "problem-set",
    "lab",
    "project",
    "exam",
    "quiz",
    "competition",
    "reproduction",
    "reading",
    "oral",
    "mistake-review",
    "log",
}
VALID_SOURCE_TYPES = {
    "official_assignment",
    "open_textbook_exercise",
    "open_source_project_task",
    "local_integration_task",
}
LEGACY_LABELS = ("李宏毅式", "李宏毅-CMU模式", "4-Tier", "Boss Baseline", "阶梯作业")
PLACEHOLDER_RE = re.compile(r"\b(?:TODO|TBD)\b|\[待创建\]|待补(?:充|全)?|待完善", re.I)
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
TABLE_ALIAS_RE = re.compile(r"\[\[[^\]\n]*(?<!\\)\|[^\]]+\]\]")
STAGE_DIR_RE = re.compile(r"^\d{2}-.+")
TOP_LEVEL_RE = re.compile(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$")


@dataclass
class Issue:
    severity: str
    code: str
    path: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只读预检 Obsidian 课程结构、字段和作业关系")
    parser.add_argument("--vault", type=Path, default=Path.cwd(), help="知识库根目录")
    parser.add_argument("--course", required=True, help="课程目录名、相对路径或绝对路径")
    parser.add_argument("--project", help="项目目录相对路径或绝对路径；默认自动查找同名目录")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--strict", action="store_true", help="存在 error 时返回非零退出码")
    parser.add_argument("--limit", type=int, default=200, help="文本模式最多显示的问题数")
    return parser.parse_args()


def walk_visible(root: Path) -> list[Path]:
    if not root.exists():
        return []
    result: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in IGNORED_PARTS and not name.startswith(".")]
        current = Path(dirpath)
        result.extend(current / name for name in filenames if name.lower().endswith(".md"))
    return result


def named_directories(root: Path, name: str) -> list[Path]:
    if not root.exists():
        return []
    result: list[Path] = []
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [item for item in dirnames if item not in IGNORED_PARTS and not item.startswith(".")]
        current = Path(dirpath)
        result.extend((current / item).resolve() for item in dirnames if item == name)
    return sorted(set(result))


def resolve_course(vault: Path, raw: str) -> Path | None:
    candidate = Path(raw)
    if candidate.is_absolute() and candidate.is_dir():
        return candidate.resolve()
    direct = vault / candidate
    if direct.is_dir():
        return direct.resolve()
    course_root = vault / "02-Knowledge" / "🧠 学习系统"
    exact = course_root / raw
    if exact.is_dir():
        return exact.resolve()
    matches = named_directories(course_root, raw)
    return matches[0] if len(matches) == 1 else None


def find_project(vault: Path, course: Path, raw: str | None) -> tuple[Path | None, list[Path]]:
    if raw:
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = vault / candidate
        return (candidate.resolve() if candidate.is_dir() else None), []
    matches = named_directories(vault / "03-Projects", course.name)
    return (matches[0] if len(matches) == 1 else None), matches


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def scalar(raw: str) -> Any:
    value = raw.strip()
    if not value:
        return ""
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.startswith("[") and value.endswith("]"):
        links = WIKILINK_RE.findall(value)
        if links:
            return [f"[[{link}]]" for link in links]
        return [item.strip().strip('"\'') for item in value[1:-1].split(",") if item.strip()]
    return value.strip('"\'')


def parse_yaml_subset(raw: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = TOP_LEVEL_RE.match(line)
        if match:
            current_key = match.group(1)
            data[current_key] = scalar(match.group(2) or "")
            continue
        if current_key and line.startswith((" ", "\t")) and line.strip().startswith("-"):
            if not isinstance(data[current_key], list):
                data[current_key] = []
            data[current_key].append(scalar(line.strip()[1:]))
    return data


def frontmatter(path: Path) -> tuple[dict[str, Any], str, str | None]:
    text = read_text(path)
    if not text.startswith("---"):
        return {}, text, "missing frontmatter"
    match = re.match(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n?", text, re.S)
    if not match:
        return {}, text, "unterminated frontmatter"
    return parse_yaml_subset(match.group(1)), text[match.end() :], None


def clean_link(raw: str) -> str:
    target = raw.replace("\\|", "|").split("|", 1)[0]
    return target.split("#", 1)[0].split("^", 1)[0].strip().lstrip("/")


def build_link_index(vault: Path) -> tuple[dict[str, list[Path]], dict[str, Path]]:
    stems: dict[str, list[Path]] = defaultdict(list)
    paths: dict[str, Path] = {}
    for path in walk_visible(vault):
        stems[path.stem.casefold()].append(path)
        relative = path.relative_to(vault).with_suffix("").as_posix().casefold()
        paths[relative] = path
    return stems, paths


def resolve_link(
    source: Path,
    raw: str,
    vault: Path,
    stems: dict[str, list[Path]],
    paths: dict[str, Path],
) -> tuple[bool, str]:
    target = clean_link(raw)
    if not target or "<%" in target or "${" in target:
        return True, "template"
    normalized = target.replace("\\", "/").removesuffix(".md")
    if normalized.casefold() in paths:
        return True, "path"
    local = (source.parent.relative_to(vault) / normalized).as_posix().casefold()
    if local in paths:
        return True, "relative"
    matches = stems.get(Path(normalized).stem.casefold(), [])
    if len(matches) == 1:
        return True, "unique-stem"
    return False, "ambiguous" if len(matches) > 1 else "missing"


def link_values(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    result: list[str] = []
    for item in values:
        if not isinstance(item, str):
            continue
        links = WIKILINK_RE.findall(item)
        result.extend(links or ([item] if item.strip() else []))
    return result


def relative(path: Path | None, vault: Path) -> str | None:
    if path is None:
        return None
    try:
        return path.relative_to(vault).as_posix()
    except ValueError:
        return str(path)


def add(issues: list[Issue], severity: str, code: str, path: Path, vault: Path, message: str) -> None:
    issues.append(Issue(severity, code, relative(path, vault) or str(path), message))


def first_heading(body: str) -> str:
    match = re.search(r"(?m)^#\s+(.+?)\s*$", body)
    return match.group(1) if match else ""


def content_size(body: str) -> int:
    without_code = re.sub(r"```.*?```", "", body, flags=re.S)
    return len(re.sub(r"\s+", "", without_code))


def check_table_links(path: Path, body: str, vault: Path, issues: list[Issue]) -> None:
    for line_number, line in enumerate(body.splitlines(), 1):
        if line.lstrip().startswith("|") and TABLE_ALIAS_RE.search(line):
            add(
                issues,
                "error",
                "TABLE_LINK_ESCAPE",
                path,
                vault,
                f"第 {line_number} 行表格 Wikilink 的别名分隔符未转义",
            )


def audit_course(
    course: Path,
    vault: Path,
    stems: dict[str, list[Path]],
    paths: dict[str, Path],
    issues: list[Issue],
) -> dict[str, int]:
    files = walk_visible(course)
    counts = {"course_markdown": len(files), "study_cards": 0, "stage_mocs": 0}
    root_files = [path for path in files if path.parent == course]
    learning_paths = [path for path in root_files if path.name.startswith("🗺️") and "学习路径" in path.stem]
    if len(learning_paths) != 1:
        add(issues, "error", "LEARNING_PATH_COUNT", course, vault, f"根目录学习路径数量为 {len(learning_paths)}，应为 1")
    for path in root_files:
        if not path.name.startswith(("🗺️", "📚", "🧭")) and path.name not in {"README.md", "AGENTS.md"}:
            add(issues, "warning", "ROOT_MARKDOWN_CANDIDATE", path, vault, "根目录 Markdown 可能是散落知识卡，需人工归类")

    stage_dirs = [path for path in course.iterdir() if path.is_dir() and STAGE_DIR_RE.match(path.name)]
    if not any(path.name == "00-前置知识" for path in stage_dirs):
        add(issues, "warning", "PREREQUISITE_DIR_MISSING", course, vault, "缺少 00-前置知识 目录")
    for stage_dir in stage_dirs:
        mocs = list(stage_dir.glob("🧭*.md"))
        counts["stage_mocs"] += len(mocs)
        if len(mocs) != 1:
            add(issues, "error", "STAGE_MOC_COUNT", stage_dir, vault, f"阶段 MOC 数量为 {len(mocs)}，应为 1")

    for path in files:
        data, body, fm_error = frontmatter(path)
        if fm_error:
            add(issues, "warning", "FRONTMATTER_PARSE", path, vault, fm_error)
        kind = str(data.get("kind", ""))
        is_study = data.get("type") == "study" and kind != "moc"
        if data.get("project_type") == "homework" or data.get("assignment_level") is not None:
            add(issues, "error", "ASSIGNMENT_IN_KNOWLEDGE", path, vault, "作业位于知识目录，形成第二作业源")
        if not is_study:
            check_table_links(path, body, vault, issues)
            continue
        counts["study_cards"] += 1
        if path.parent == course:
            add(issues, "error", "ROOT_STUDY_CARD", path, vault, "课程知识卡散落在课程根目录")
        for field in STUDY_REQUIRED:
            if data.get(field) in (None, "", []):
                add(issues, "error", "STUDY_FIELD_MISSING", path, vault, f"缺少必填字段 {field}")
        if data.get("flow") not in (None, "knowledge"):
            add(issues, "warning", "STUDY_FLOW", path, vault, f"flow={data.get('flow')!r}，课程卡应为 knowledge")
        if "downstream" in data:
            add(issues, "error", "STATIC_DOWNSTREAM", path, vault, "人工维护 downstream，形成第二事实源")
        if "upstream" in data and data.get("upstream") in (None, "", []):
            add(issues, "warning", "EMPTY_UPSTREAM", path, vault, "无直接前置时应省略 upstream")
        for field in ("stage_moc", "upstream"):
            for raw in link_values(data.get(field)):
                ok, reason = resolve_link(path, raw, vault, stems, paths)
                if not ok:
                    add(issues, "error", "UNRESOLVED_RELATION", path, vault, f"{field} 无法解析（{reason}）：{clean_link(raw)}")
        exempt = data.get("assessment_exempt") is True
        if exempt and not data.get("assessment_exempt_reason"):
            add(issues, "error", "EXEMPT_REASON_MISSING", path, vault, "豁免页缺少 assessment_exempt_reason")
        if not exempt:
            signals = ("contains(requires, this.file.link)", "检索练习", "可执行产物", "闭卷验收", "通过标准")
            if not any(signal in body for signal in signals):
                add(issues, "warning", "ASSESSMENT_SIGNAL_MISSING", path, vault, "未发现作业反查、检索练习、可执行产物或通过标准")
            if content_size(body) < 600:
                add(issues, "warning", "THIN_STUDY_CARD", path, vault, "非豁免知识卡正文过短，需人工检查内容质量")
        if PLACEHOLDER_RE.search(body):
            add(issues, "error", "PLACEHOLDER", path, vault, "包含 TODO、待创建、待补或待完善占位内容")
        if any(label in path.name or label in first_heading(body) for label in LEGACY_LABELS):
            add(issues, "error", "LEGACY_NAME", path, vault, "文件名或 H1 含历史营销式标签")
        check_table_links(path, body, vault, issues)
    return counts


def audit_project(
    project: Path | None,
    vault: Path,
    stems: dict[str, list[Path]],
    paths: dict[str, Path],
    issues: list[Issue],
) -> dict[str, int]:
    counts = {"assignment_files": 0, "lesson": 0, "stage": 0, "capstone": 0}
    if project is None:
        add(issues, "error", "PROJECT_NOT_RESOLVED", vault / "03-Projects", vault, "无法唯一定位课程项目目录")
        return counts
    if not (project / "🧭 课程作业总索引.md").exists():
        add(issues, "warning", "ASSIGNMENT_INDEX_MISSING", project, vault, "缺少 🧭 课程作业总索引.md")
    files: list[Path] = []
    for directory in LEVEL_DIRS.values():
        target = project / directory
        if not target.is_dir():
            add(issues, "warning", "ASSIGNMENT_DIR_MISSING", target, vault, f"缺少 {directory} 目录")
        files.extend(walk_visible(target))
    files = sorted(set(files))
    counts["assignment_files"] = len(files)

    for path in files:
        data, body, fm_error = frontmatter(path)
        if fm_error:
            add(issues, "error", "ASSIGNMENT_FRONTMATTER", path, vault, fm_error)
        for field in ASSIGNMENT_REQUIRED:
            if data.get(field) in (None, "", []):
                add(issues, "error", "ASSIGNMENT_FIELD_MISSING", path, vault, f"缺少必填字段 {field}")
        level = data.get("assignment_level")
        if level not in LEVEL_DIRS:
            add(issues, "error", "ASSIGNMENT_LEVEL", path, vault, f"assignment_level={level!r} 不合法")
        else:
            counts[level] += 1
            if LEVEL_DIRS[level] not in path.parts:
                add(issues, "error", "ASSIGNMENT_LOCATION", path, vault, f"{level} 作业应位于 {LEVEL_DIRS[level]}")
        if data.get("assignment_format") not in VALID_FORMATS:
            add(issues, "warning", "ASSIGNMENT_FORMAT", path, vault, f"assignment_format={data.get('assignment_format')!r} 不在推荐枚举中")
        if data.get("source_type") not in VALID_SOURCE_TYPES:
            add(issues, "error", "SOURCE_TYPE", path, vault, f"source_type={data.get('source_type')!r} 不合法")
        requires = link_values(data.get("requires"))
        if not requires:
            add(issues, "error", "REQUIRES_MISSING", path, vault, "requires 为空或不是可解析链接")
        for raw in requires:
            ok, reason = resolve_link(path, raw, vault, stems, paths)
            if not ok:
                add(issues, "error", "REQUIRES_UNRESOLVED", path, vault, f"requires 无法解析（{reason}）：{clean_link(raw)}")
        if any(label in path.name or label in first_heading(body) for label in LEGACY_LABELS):
            add(issues, "error", "LEGACY_ASSIGNMENT_NAME", path, vault, "作业文件名或 H1 含历史营销式标签")
        required_sections = {
            "学习目标": ("学习目标",),
            "任务边界": ("任务背景", "任务说明", "问题背景", "任务边界"),
            "提交产物": ("提交产物", "提交要求"),
            "验收标准": ("验收标准", "Rubric", "评分标准"),
            "引导自检": ("引导", "自检", "检查点", "调试"),
        }
        for label, variants in required_sections.items():
            if not any(variant in body for variant in variants):
                add(issues, "warning", "ASSIGNMENT_DETAIL", path, vault, f"未发现“{label}”相关章节")
        if content_size(body) < 900:
            add(issues, "warning", "THIN_ASSIGNMENT", path, vault, "作业正文过短，需人工核查详细度")
        if PLACEHOLDER_RE.search(body):
            add(issues, "error", "ASSIGNMENT_PLACEHOLDER", path, vault, "作业包含占位内容")
        check_table_links(path, body, vault, issues)
    if counts["capstone"] == 0:
        add(issues, "warning", "CAPSTONE_MISSING", project, vault, "未发现 capstone；完整课程需确认跨阶段验收")
    return counts


def main() -> int:
    args = parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    vault = args.vault.resolve()
    course = resolve_course(vault, args.course)
    if course is None:
        print(f"ERROR: 无法唯一定位课程目录：{args.course}", file=sys.stderr)
        return 2
    project, project_matches = find_project(vault, course, args.project)
    stems, paths = build_link_index(vault)
    issues: list[Issue] = []
    if len(project_matches) > 1:
        joined = ", ".join(relative(path, vault) or str(path) for path in project_matches)
        add(issues, "error", "PROJECT_AMBIGUOUS", vault / "03-Projects", vault, f"发现多个同名项目目录：{joined}")
    course_counts = audit_course(course, vault, stems, paths, issues)
    project_counts = audit_project(project, vault, stems, paths, issues) if len(project_matches) <= 1 else {
        "assignment_files": 0,
        "lesson": 0,
        "stage": 0,
        "capstone": 0,
    }
    severity_order = {"error": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda item: (severity_order[item.severity], item.path, item.code))
    summary = {
        "vault": str(vault),
        "course": relative(course, vault),
        "project": relative(project, vault),
        **course_counts,
        **project_counts,
        "errors": sum(issue.severity == "error" for issue in issues),
        "warnings": sum(issue.severity == "warning" for issue in issues),
    }
    if args.json:
        print(json.dumps({"summary": summary, "issues": [asdict(issue) for issue in issues]}, ensure_ascii=False, indent=2))
    else:
        print("COURSE PREFLIGHT")
        for key, value in summary.items():
            print(f"{key}: {value}")
        print("\nISSUES")
        for issue in issues[: args.limit]:
            print(f"[{issue.severity.upper()}] {issue.code} | {issue.path} | {issue.message}")
        if len(issues) > args.limit:
            print(f"... 另有 {len(issues) - args.limit} 项，使用 --json 或提高 --limit 查看")
        print("\n说明：本报告只做机械预检，不能替代来源核验、逐卡教学审查或 A/B/C 验收。")
    return 1 if args.strict and summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
