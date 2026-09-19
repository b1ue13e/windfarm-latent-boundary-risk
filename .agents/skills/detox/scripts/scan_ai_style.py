#!/usr/bin/env python3
"""Scan academic prose for common AI-style and research-sense warning signs.

The scanner is non-destructive. It reports suspicious patterns but does not
decide whether a manuscript is AI-written.
"""

from __future__ import annotations

import argparse
import re
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path


ALLOWED_SUFFIXES = {".txt", ".md", ".tex"}


@dataclass(frozen=True)
class PatternGroup:
    key: str
    label: str
    pattern: re.Pattern[str]
    advice: str


PATTERNS = [
    PatternGroup(
        "hedging",
        "Hedging overload",
        re.compile(
            r"可能|或许|也许|一定程度上|某种程度上|似乎|看似|往往|通常而言|大体上|"
            r"\b(?:may|might|perhaps|possibly|seems?|appears?|arguably|potentially|"
            r"to some extent|in some sense|in certain respects|tends? to)\b",
            re.IGNORECASE,
        ),
        "Remove hedges that are not needed for the evidence scope.",
    ),
    PatternGroup(
        "defensive_transition",
        "Defensive transition cliches",
        re.compile(
            r"值得注意的是|需要指出的是|不可否认的是|必须强调的是|毋庸置疑|显而易见|"
            r"\b(?:it is worth noting|it should be noted|it must be emphasized|"
            r"it is important to emphasize|undeniably|needless to say)\b",
            re.IGNORECASE,
        ),
        "Delete padding transitions or replace them with a real logical turn.",
    ),
    PatternGroup(
        "not_a_but_b",
        "Not A but B template",
        re.compile(
            r"(?:并非|并不是|不是|不只是|不仅是).{0,40}(?:而是|更是|而在于|不如说)|"
            r"\bnot\s+(?:merely|simply|only)?\s*.{0,80}?\b(?:but|instead|rather)\b",
            re.IGNORECASE,
        ),
        "State B directly unless A is a real competing claim.",
    ),
    PatternGroup(
        "mechanical_transition",
        "Mechanical ordering/report tone",
        re.compile(
            r"首先|其次|再次|最后|综上所述|基于此|有鉴于此|从宏观层面|从微观层面|"
            r"从理论层面|从实践层面|"
            r"\b(?:firstly|secondly|thirdly|finally|in conclusion|to sum up|"
            r"from a theoretical perspective|from a practical perspective)\b",
            re.IGNORECASE,
        ),
        "Use ordering only when it reflects the argument's real sequence.",
    ),
    PatternGroup(
        "empty_contribution",
        "Empty contribution/significance claim",
        re.compile(
            r"丰富了.{0,20}研究|提供了.{0,20}(?:参考|借鉴|思路)|具有重要的理论意义和实践价值|"
            r"推动.{0,20}纵深发展|拓展了.{0,20}视角|"
            r"\b(?:provides? new insights?|offers? a reference|has theoretical and practical implications|"
            r"contributes to the literature|enriches the literature)\b",
            re.IGNORECASE,
        ),
        "Replace generic significance with the exact claim, audience, and boundary.",
    ),
    PatternGroup(
        "causal_verb",
        "Causal-language watch",
        re.compile(
            r"促进|导致|影响|推动|决定|造成|引发|提升|抑制|驱动|"
            r"\b(?:causes?|leads? to|drives?|promotes?|determines?|increases?|reduces?|"
            r"improves?|affects?|impacts?)\b",
            re.IGNORECASE,
        ),
        "Check whether the research design licenses causal wording.",
    ),
    PatternGroup(
        "pseudo_problem",
        "Pseudo problem/question marker",
        re.compile(
            r"本文试图回答|如何进行|何以可能|在数字化时代|"
            r"\b(?:this paper attempts to answer|how can .* transform|in the digital era)\b",
            re.IGNORECASE,
        ),
        "Turn broad topics into concrete puzzles, contradictions, or anomalies.",
    ),
]


def configure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def decode_bytes(data: bytes) -> str:
    encodings = ("utf-8-sig", "utf-8", "gb18030", "big5", "utf-16", "utf-16-le", "utf-16-be", "latin-1")
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def read_text(path: Path) -> str:
    return decode_bytes(path.read_bytes())


def clean_for_scan(text: str, suffix: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if suffix == ".tex":
        text = re.sub(r"(?<!\\)%.*", "", text)
        text = re.sub(r"\\(?:cite|ref|label|emph|textbf|section|subsection)\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", text)
    return text


def split_paragraphs(text: str) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if len(paragraphs) <= 1:
        paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
    return paragraphs


def visible_length(paragraph: str) -> int:
    compact = re.sub(r"\s+", "", paragraph)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", compact)
    if len(cjk_chars) >= max(5, len(compact) // 5):
        return len(compact)
    return len(re.findall(r"[A-Za-z0-9_'-]+", paragraph))


def excerpt(text: str, start: int, end: int, width: int = 54) -> str:
    prefix_start = max(0, start - width // 2)
    suffix_end = min(len(text), end + width // 2)
    snippet = text[prefix_start:suffix_end].replace("\n", " ")
    snippet = re.sub(r"\s+", " ", snippet).strip()
    if prefix_start > 0:
        snippet = "..." + snippet
    if suffix_end < len(text):
        snippet += "..."
    return snippet


def find_matches(text: str) -> dict[str, list[re.Match[str]]]:
    return {group.key: list(group.pattern.finditer(text)) for group in PATTERNS}


def paragraph_rhythm(paragraphs: list[str]) -> tuple[list[int], str]:
    lengths = [visible_length(p) for p in paragraphs if visible_length(p) > 0]
    if len(lengths) < 4:
        return lengths, "Not enough paragraphs to assess homogeneity."

    mean = statistics.mean(lengths)
    stdev = statistics.pstdev(lengths)
    cv = stdev / mean if mean else 0.0
    if cv < 0.18:
        verdict = f"Warning: paragraph lengths are highly homogeneous, CV={cv:.2f}."
    elif cv < 0.28:
        verdict = f"Mild warning: paragraph rhythm is somewhat even, CV={cv:.2f}."
    else:
        verdict = f"OK: paragraph rhythm has visible variation, CV={cv:.2f}."
    return lengths, verdict


def numbered_list_count(text: str) -> int:
    markers = re.findall(
        r"(?m)^\s*(?:\d+[\.\)]|[一二三四五六七八九十]+[、.]|"
        r"(?:First|Second|Third|Fourth|Finally)\b)",
        text,
        flags=re.IGNORECASE,
    )
    dimension_phrases = re.findall(
        r"(?:三个|四个|五个).{0,8}(?:维度|层面|方面)|"
        r"\b(?:three|four|five)\s+(?:dimensions|aspects|levels)\b",
        text,
        flags=re.IGNORECASE,
    )
    return len(markers) + len(dimension_phrases)


def build_report(name: str, text: str, suffix: str) -> str:
    clean_text = clean_for_scan(text, suffix)
    paragraphs = split_paragraphs(clean_text)
    matches = find_matches(clean_text)
    lengths, rhythm_verdict = paragraph_rhythm(paragraphs)
    list_count = numbered_list_count(clean_text)

    lines = [
        "== Paper AI Detox Scan ==",
        f"Input: {name}",
        f"Characters: {len(clean_text)}",
        f"Paragraphs: {len(paragraphs)}",
        "",
        "Risk counts:",
    ]

    for group in PATTERNS:
        lines.append(f"- {group.label}: {len(matches[group.key])}")
    lines.append(f"- Numbered/list structure markers: {list_count}")

    lines.extend(["", "Paragraph rhythm:"])
    if lengths:
        lines.append(
            f"- Mean length: {statistics.mean(lengths):.1f}; "
            f"min/max: {min(lengths)}/{max(lengths)}"
        )
    lines.append(f"- {rhythm_verdict}")

    lines.extend(["", "Flagged excerpts:"])
    shown = 0
    for group in PATTERNS:
        for match in matches[group.key][:3]:
            lines.append(f"- [{group.label}] {excerpt(clean_text, match.start(), match.end())}")
            shown += 1
            if shown >= 12:
                break
        if shown >= 12:
            break
    if shown == 0:
        lines.append("- No high-signal pattern excerpts found.")

    lines.extend(["", "Suggested revision targets:"])
    for group in PATTERNS:
        if matches[group.key]:
            lines.append(f"- {group.advice}")
    if list_count >= 3:
        lines.append("- Check whether the numbered structure creates real logic or only format.")
    if lengths and len(lengths) >= 4 and statistics.pstdev(lengths) / statistics.mean(lengths) < 0.28:
        lines.append("- Vary paragraph length: use short paragraphs for claims and longer ones for evidence.")
    if not any(matches.values()) and list_count == 0:
        lines.append("- Scanner found few surface patterns; inspect research design and citation integrity manually.")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Non-destructively scan .txt, .md, or .tex academic prose for AI-style warning signs."
    )
    parser.add_argument("inputs", nargs="+", help="Files to scan, or '-' for standard input.")
    return parser.parse_args()


def main() -> int:
    configure_stdout()
    args = parse_args()
    reports: list[str] = []

    for raw_input in args.inputs:
        if raw_input == "-":
            text = decode_bytes(sys.stdin.buffer.read())
            reports.append(build_report("stdin", text, ".txt"))
            continue

        path = Path(raw_input)
        if not path.exists():
            print(f"[ERROR] File not found: {path}", file=sys.stderr)
            return 2
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            allowed = ", ".join(sorted(ALLOWED_SUFFIXES))
            print(f"[ERROR] Unsupported extension for {path}. Allowed: {allowed}", file=sys.stderr)
            return 2
        reports.append(build_report(str(path), read_text(path), path.suffix.lower()))

    print("\n\n".join(reports))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
