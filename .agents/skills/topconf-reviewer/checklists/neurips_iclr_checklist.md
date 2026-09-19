# NeurIPS & ICLR Official Paper Checklist Guidelines

When reviewing papers against the official conference standards, verify each of the following 10 core dimensions:

## 1. Claims and Hypotheses
- **Checklist Item**: Do the main claims match the experimental results without overclaiming?
- **Red Flags**: Claiming "universal applicability" when tested only on synthetic toy graphs; claiming "SOTA" without showing variance or on limited datasets.

## 2. Limitations and Failure Modes
- **Checklist Item**: Does the paper dedicate a clear section to explicit limitations, assumptions, and failure modes?
- **Red Flags**: No limitation section; burying limitations in obscure paragraphs; failing to identify when the method breaks down.

## 3. Theoretical Assumptions and Proofs
- **Checklist Item**: Are all assumptions clearly stated, numbered, and discussed? Are full proofs included in the appendix?
- **Red Flags**: Hidden assumptions (e.g. graph connectedness, bounded spectrum); hand-waving steps in proofs.

## 4. Experimental Rigor and Baselines
- **Checklist Item**: Are standard, recognized benchmarks used? Are baselines up to date (current year - 1)?
- **Red Flags**: Omitting top-performing baselines; evaluating on non-standard subsets.

## 5. Statistical Significance and Error Bars
- **Checklist Item**: Are results reported with mean and standard deviation over at least 5 distinct random seeds?
- **Red Flags**: Single-run numbers; missing error bars in tables and line plots; claiming superiority on overlapping confidence intervals without t-test.

## 6. Hyperparameter Tuning Fairness
- **Checklist Item**: Did baselines receive equal hyperparameter tuning effort/budget?
- **Red Flags**: Proposed method heavily tuned with grid search, while baselines use default out-of-the-box parameters.

## 7. Compute Resources and Footprint
- **Checklist Item**: Does the paper disclose GPU hardware, total compute hours, and inference latency/memory complexity?
- **Red Flags**: No mention of training hardware or runtime complexity.

## 8. Reproducibility and Code Availability
- **Checklist Item**: Is anonymized code/data provided in supplementary material or URL? Are full environment specifications included?
- **Red Flags**: "Code will be released upon acceptance" with no implementation details.

## 9. Negative Societal Impacts & Ethics
- **Checklist Item**: Did the authors discuss potential dual-use, privacy, or safety risks if applicable?

## 10. Figures and Readability
- **Checklist Item**: Are figures colorblind-friendly, vector format (PDF/SVG), high resolution, with readable font sizes comparable to caption text?
