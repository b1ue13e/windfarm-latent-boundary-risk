#!/usr/bin/env python
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


SVG_NS = "http://www.w3.org/2000/svg"


def _numeric(value: str | None) -> float | None:
    if not value:
        return None
    match = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)", value)
    return float(match.group(1)) if match else None


def _svg_size(root: ET.Element) -> tuple[float | None, float | None, str | None]:
    width = _numeric(root.get("width"))
    height = _numeric(root.get("height"))
    view_box = root.get("viewBox")
    if (width is None or height is None) and view_box:
        parts = view_box.replace(",", " ").split()
        if len(parts) == 4:
            try:
                width = width if width is not None else float(parts[2])
                height = height if height is not None else float(parts[3])
            except ValueError:
                pass
    return width, height, view_box


def validate(svg_path: Path, png_path: Path | None = None) -> int:
    if not svg_path.is_file():
        print(f"ERROR: file not found: {svg_path}", file=sys.stderr)
        return 2

    try:
        tree = ET.parse(svg_path)
    except ET.ParseError as exc:
        print(f"ERROR: invalid XML/SVG: {exc}", file=sys.stderr)
        return 1

    root = tree.getroot()
    if root.tag not in {"svg", f"{{{SVG_NS}}}svg"}:
        print(f"ERROR: root element is not svg: {root.tag}", file=sys.stderr)
        return 1

    width, height, view_box = _svg_size(root)
    warnings: list[str] = []
    if width is None or height is None:
        warnings.append("missing usable width/height and viewBox dimensions")
    if not root.get("xmlns") and not root.tag.startswith("{"):
        warnings.append("missing xmlns attribute")
    if view_box is None:
        warnings.append("missing viewBox")

    print(f"OK: valid SVG: {svg_path}")
    if width is not None and height is not None:
        print(f"size: {width:g} x {height:g}")
    if view_box:
        print(f"viewBox: {view_box}")
    for warning in warnings:
        print(f"WARNING: {warning}")

    if png_path:
        try:
            import cairosvg
        except Exception as exc:
            print(f"WARNING: cannot render PNG because cairosvg is unavailable: {exc}")
        else:
            png_path.parent.mkdir(parents=True, exist_ok=True)
            cairosvg.svg2png(url=str(svg_path), write_to=str(png_path))
            print(f"rendered: {png_path}")

    return 0 if not warnings else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an SVG and optionally render a PNG preview.")
    parser.add_argument("svg", type=Path)
    parser.add_argument("--png", type=Path, default=None)
    args = parser.parse_args()
    return validate(args.svg, args.png)


if __name__ == "__main__":
    raise SystemExit(main())
