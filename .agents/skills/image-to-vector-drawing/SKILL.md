---
name: image-to-vector-drawing
description: Convert images, screenshots, sketches, logos, icons, diagrams, charts, paper figures, or drawing requests into clean editable SVG/vector artwork. Use when the user asks in English or Chinese to draw, redraw, vectorize, trace, convert to SVG, make a vector image, make an editable scientific illustration, 绘图, 画图, 重绘, 转矢量图, 矢量化, 转 SVG, 做 SVG, or convert a provided image into vector form.
---

# Image To Vector Drawing

## Core Rule

Prefer editable SVG as the primary output. Preserve the user's intent and visual structure over pixel-perfect bitmap copying. For complex photos, explain that the result will be a vector-style redrawing, not lossless photo vectorization.

## Workflow

1. Inspect the source.
   - If an image file is provided, view it first when possible.
   - Identify whether it is a logo/icon, line art, diagram, chart, UI screenshot, scientific figure, or photo.
   - Ask for one concise clarification only when the target style, labels, or fidelity requirements are ambiguous enough to change the SVG substantially.

2. Choose the method.
   - For icons, logos, simple illustrations, flowcharts, paper diagrams, and screenshots: hand-build semantic SVG with shapes, paths, text, gradients only when useful, and stable `viewBox`.
   - For charts or plots: reconstruct axes, labels, legends, markers, and lines as SVG objects. Do not embed the original bitmap unless the user explicitly wants a traced reference layer.
   - For complex raster art or photos: create simplified vector-style artwork with grouped regions and readable shapes.
   - For scientific figures: prioritize clean alignment, editable text, consistent stroke widths, and publication-ready layout.

3. Produce files.
   - Save the main SVG in the workspace with a clear name such as `vectorized.svg`, `<source-stem>.svg`, or `<topic>.svg`.
   - If useful, also render a PNG preview next to it.
   - Keep text as `<text>` elements when editability matters; convert text to paths only if the user requests strict appearance preservation.

4. Validate before finishing.
   - Run `scripts/validate_svg.py <svg-path>` from this skill.
   - If rendering support is available, use the generated PNG preview or another visual check.
   - Open/view the preview when possible for non-trivial drawings and iterate until text does not overlap and the composition is coherent.

## SVG Quality Guidelines

- Include `xmlns`, `viewBox`, explicit width/height or an intentional responsive setup.
- Use grouped elements with meaningful IDs for editable regions.
- Use consistent stroke widths and line caps/joins.
- Avoid embedding base64 raster images unless the user asks for a hybrid SVG.
- Avoid tiny unreadable text; simplify labels when needed and mention if labels were inferred.
- Match the input proportions unless the user asks for a different aspect ratio.
- Keep the SVG self-contained unless external fonts/assets are explicitly acceptable.

## Using AutoFigure-Edit

If the user wants to convert a scientific/paper method illustration or an existing first-stage academic figure into editable SVG, consider the local project at `E:\绘图\AutoFigure-Edit-main\AutoFigure-Edit-main` if it exists.

Use AutoFigure-Edit when the user specifically wants the model pipeline, SAM segmentation, or paper-figure reconstruction. For ordinary icons, diagrams, logos, and straightforward screenshots, hand-authored SVG is usually faster and more controllable.

## Script

Use `scripts/validate_svg.py` to check syntax, dimensions, and optional PNG rendering:

```bash
python scripts/validate_svg.py path/to/file.svg --png path/to/preview.png
```
