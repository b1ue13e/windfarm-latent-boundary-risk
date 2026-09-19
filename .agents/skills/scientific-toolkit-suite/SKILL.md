---
name: scientific-toolkit-suite
description: Consolidated scientific tools, libraries, APIs, data analysis, machine learning, statistics, visualization, biomedical, chemistry, genomics, astronomy, physics, quantum, engineering, document, spreadsheet, PDF, and integration skill suite. Use when a request names a scientific Python/R/library/tool/API/file format or asks for domain-specific analysis outside the core academic manuscript workflow.
---

# Scientific Toolkit Suite

This is the main entry point for the many specialized scientific-agent skills. It keeps the active skill list compact while preserving the original detailed instructions in the archive.

## Source Index

Archived source map:

`C:\Users\lidong\.codex\skills\scientific-toolkit-suite\references\source-map.md`

Open the source map, choose the one most specific skill for the concrete library/domain/file type, then read that archived `SKILL.md`. Avoid loading multiple source skills unless the task truly crosses domains.

## Routing

- Biomedical, genomics, single-cell, protein, molecule, chemistry, clinical, drug-discovery tasks:
  use the matching source skill such as `scanpy`, `scvi-tools`, `anndata`, `biopython`, `rdkit`, `datamol`, `deepchem`, `esm`, `depmap`, `clinical-reports`, or related domain skill.

- Data science, statistics, machine learning, time series, explainability, visualization:
  use the matching source skill such as `scikit-learn`, `statsmodels`, `statistical-analysis`, `aeon`, `timesfm-forecasting`, `shap`, `matplotlib`, `seaborn`, `plotly`, `dask`, `vaex`, or `scientific-visualization`.

- Physics, astronomy, quantum, materials, symbolic math, engineering simulation:
  use the matching source skill such as `astropy`, `qiskit`, `cirq`, `qutip`, `pennylane`, `sympy`, `pymatgen`, `fluidsim`, or related tool.

- Documents, PDFs, spreadsheets, slides, markdown/mermaid, image/infographic generation, database/API integrations:
  use the matching source skill such as `pdf`, `docx`, `xlsx`, `pptx`, `markdown-mermaid-writing`, `database-lookup`, `markitdown`, or an integration-specific skill.

## Operating Rules

- Pick the narrowest matching source skill first.
- Prefer the codebase's existing libraries and local scripts before adding new dependencies.
- For medical, legal, financial, or current factual content, verify current authoritative sources before giving high-stakes guidance.
- Keep specialized library instructions out of the answer unless the user asks for explanation; use them to act correctly.
