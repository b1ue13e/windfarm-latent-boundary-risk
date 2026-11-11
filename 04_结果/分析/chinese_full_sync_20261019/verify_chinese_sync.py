"""Check translation coverage, immutable evidence and scientific boundaries."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import re
from pathlib import Path

from sync_chinese import ROOT, OUT, TOKEN, translated_float, translated_prose
from translations import MATH_TEXT, SOURCE_SHA256, TRANSLATIONS


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(text: str) -> str:
    for english, chinese in MATH_TEXT.items():
        text = text.replace(chinese, english)
    return text


def main() -> None:
    english = (ROOT / "paper_tste_ieee.md").read_text(encoding="utf-8")
    assert sha(ROOT / "paper_tste_ieee.md") == SOURCE_SHA256
    body = english[english.index(r"\begin{abstract}") :]
    chinese = (ROOT / "paper_tste_chinese.md").read_text(encoding="utf-8")
    counts = Counter()
    for index, original in enumerate(re.split(r"\n[ \t]*\n", body)):
        original = original.strip()
        if not original:
            continue
        translated, _ = (translated_prose(index, original) if index in TRANSLATIONS
                          else translated_float(index, original))
        for left, right in MATH_TEXT.items():
            translated = translated.replace(left, right)
        assert translated in chinese, (index, "Missing translated segment")
        source_tokens = Counter(TOKEN.findall(original))
        target_tokens = Counter(TOKEN.findall(canonical(translated)))
        assert source_tokens == target_tokens, (index, source_tokens - target_tokens, target_tokens - source_tokens)
        normalized = translated.replace("一级", "1级").replace("二级", "2级").replace("六步", "6步")
        numbers = lambda text: Counter(re.findall(r"\d+(?:[.,]\d+)*", text))
        assert not numbers(original) - numbers(normalized), (index, "Omitted source numeral")
        counts["segments"] += 1
    translated_body = chinese[chinese.index(r"\begin{abstract}") :]
    for command in ("label", "ref"):
        assert re.findall(r"\\"+command+r"\{[^}]+\}", body) == re.findall(r"\\"+command+r"\{[^}]+\}", translated_body)
    assert re.findall(r"\[@[^\]]+\]", body) == re.findall(r"\[@[^\]]+\]", translated_body)
    for kind in ("equation", "table", "figure"):
        counts[kind] = len(re.findall(r"\\begin\{"+kind+r"\*?\}", body))
        assert counts[kind] == len(re.findall(r"\\begin\{"+kind+r"\*?\}", translated_body))
    tabular = r"\\begin\{tabular\*?\}.*?\\end\{tabular\*?\}"
    left_tables = re.findall(tabular, body, re.S)
    right_tables = re.findall(tabular, translated_body, re.S)
    assert len(left_tables) == len(right_tables) == 4
    for left, right in zip(left_tables, right_tables):
        def data_rows(table):
            rows = []
            for line in table.splitlines():
                if re.search(r"(?<!\\)&", line) and not line.startswith(r"\multicolumn"):
                    rows.append(re.findall(r"\d+(?:[.,]\d+)*", line))
            return rows
        assert data_rows(left) == data_rows(right), "Table data-row order or values changed"
    assert re.findall(r"\\includegraphics.*?\{([^}]+)\}", body) == re.findall(r"\\includegraphics.*?\{([^}]+)\}", translated_body)
    for name in ("manuscript/paper_chinese_topjournal_final.md", "manuscript/paper_tste_chinese_topjournal.md"):
        assert (ROOT / name).read_bytes() == (ROOT / "paper_tste_chinese.md").read_bytes()
    for phrase in ("平均成本高0.5641", "联合近似区间", "主2", "420", "367", "53", "46", "26", "18",
                   "q0.95策略不在", "delay3/0.5", "不是独立重复", "E07仍未激活", "不覆盖任意季节或控制漂移"):
        assert phrase in chinese, phrase
    for phrase in ("绝对统治地位", "终极行业交付", "系统综合考核成本降低41.9", "确立如下风电备用决策的最小充分模型选用准则"):
        assert phrase not in chinese, phrase
    before = json.loads((OUT / "before.json").read_text(encoding="utf-8"))
    for name in before["protected"]:
        assert sha(ROOT / name) == before["sha256"][name], name
    result = dict(status="PASS", counts=dict(counts), english_sha256=SOURCE_SHA256,
                  chinese_sha256=sha(ROOT / "paper_tste_chinese.md"), identical_chinese_copies=3,
                  protected_files_unchanged=len(before["protected"]),
                  math_citations_labels_and_figures_preserved=True,
                  table_numeric_rows_and_order_preserved=True,
                  source_numerals_preserved=True, no_missing_source_segment=True,
                  primary_secondary_and_negative_boundaries_present=True,
                  scope="Document synchronization only; no inference or experiment rerun")
    (OUT / "translation_checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
