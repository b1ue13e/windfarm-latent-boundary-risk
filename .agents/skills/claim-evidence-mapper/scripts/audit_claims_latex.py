#!/usr/bin/env python3
"""
audit_claims_latex.py - Top-Tier Conference LaTeX Claim & Evidence Auditor
Usage:
    python audit_claims_latex.py /path/to/main.tex [--strict]
"""

import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

OVERCLAIM_KEYWORDS = [
    r"\bdrastic(?:ally)?\b",
    r"\bsuperior\s+performance\b",
    r"\bcompletely\s+solve[ds]?\b",
    r"\bunprecedented\b",
    r"\bgroudbreaking\b",
    r"\bflawless\b",
    r"\bperfect(?:ly)?\b",
]

QUANTITATIVE_PATTERN = re.compile(r"(\b\d+(?:\.\d+)?%\b|\b\d+\.\d+\s*\\pm\s*\d+\.\d+\b|\b\d+(?:\.\d+)?\s*(?:times|folds?|$\times$)\b)")
REF_PATTERN = re.compile(r"\\(?:ref|eqref|cite)\{[^\}]+\}")

def remove_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        clean_line = re.sub(r"(?<!\\)%.*$", "", line)
        lines.append(clean_line)
    return "\n".join(lines)

def analyze_tex(file_path: Path, strict: bool = False) -> Dict:
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
    clean_text = remove_comments(raw_text)

    paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]

    issues = {
        "overclaims": [],
        "floating_metrics": [],
        "macro_variables": [],
        "stats": {
            "total_paragraphs": len(paragraphs),
            "floating_count": 0,
            "overclaim_count": 0
        }
    }

    for p_idx, para in enumerate(paragraphs, 1):
        for kw in OVERCLAIM_KEYWORDS:
            match = re.search(kw, para, re.IGNORECASE)
            if match:
                issues["overclaims"].append({
                    "paragraph_idx": p_idx,
                    "keyword": match.group(0),
                    "snippet": para[:140] + ("..." if len(para) > 140 else "")
                })
                issues["stats"]["overclaim_count"] += 1

        quant_matches = QUANTITATIVE_PATTERN.findall(para)
        refs = REF_PATTERN.findall(para)
        if quant_matches and not refs:
            issues["floating_metrics"].append({
                "paragraph_idx": p_idx,
                "metrics": quant_matches,
                "snippet": para[:140] + ("..." if len(para) > 140 else "")
            })
            issues["stats"]["floating_count"] += 1

    macro_matches = re.findall(r"\\newcommand\{\\([A-Za-z]+Metric[A-Za-z]*)\}\{([^\}]+)\}", raw_text)
    issues["macro_variables"] = macro_matches

    return issues

def print_report(issues: Dict, file_path: Path):
    print("=" * 70)
    print(f"[TopConf Claim-Evidence Audit Report]: {file_path.name}")
    print("=" * 70)

    if issues["macro_variables"]:
        print(f"\n[+] Synchronized Metric Macros ({len(issues['macro_variables'])} found):")
        for name, val in issues["macro_variables"]:
            print(f"    \\{name} -> '{val}'")
    else:
        print("\n[-] Notice: No Central Metric Macros found (e.g. \\newcommand{\\OurLeadTime}{...}).")
        print("    Recommendation: Use topconf_preamble.tex to synchronize key numbers.")

    print(f"\n[!] Overclaiming & Hype Check ({issues['stats']['overclaim_count']} flags):")
    if not issues["overclaims"]:
        print("    PASS: Clean, rigorous academic tone.")
    else:
        for item in issues["overclaims"]:
            print(f"    FLAG [Para {item['paragraph_idx']}] Keyword '{item['keyword']}':")
            print(f"         \"{item['snippet']}\"")

    print(f"\n[!] Floating Quantitative Numbers Check ({issues['stats']['floating_count']} flags):")
    if not issues["floating_metrics"]:
        print("    PASS: All metrics tied to Tables, Figures, or Citations.")
    else:
        for item in issues["floating_metrics"]:
            print(f"    FLAG [Para {item['paragraph_idx']}] Numbers {item['metrics']} without \\ref:")
            print(f"         \"{item['snippet']}\"")

    print("\n" + "=" * 70)
    total_alerts = issues["stats"]["overclaim_count"] + issues["stats"]["floating_count"]
    if total_alerts == 0:
        print("RESULT: PASSED (Zero Critical Claim Flaws)")
    else:
        print(f"RESULT: {total_alerts} Warning(s) Detected - Review before submission.")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description="Audit LaTeX files for claims and evidence grounding.")
    parser.add_argument("tex_file", type=Path, help="Path to LaTeX source file (.tex)")
    parser.add_argument("--strict", action="store_true", help="Exit with non-zero code on any warning")
    args = parser.parse_args()

    issues = analyze_tex(args.tex_file, args.strict)
    print_report(issues, args.tex_file)

    if args.strict and (issues["stats"]["overclaim_count"] + issues["stats"]["floating_count"] > 0):
        sys.exit(1)

if __name__ == "__main__":
    main()
