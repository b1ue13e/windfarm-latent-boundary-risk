# TSTE Final-Read Checklist

Last updated: 2026-07-02. Use with `paper_tste_ieee.pdf`,
`paper_tste_supplementary.pdf`, and `cover_letter_tste.md` open. Machine checks should
already pass; this list is the human reviewer-eye pass before upload.

## 1. The Headline Is Recovery + Accountability, Never SOTA Accuracy

- Where: abstract, Introduction contributions, Results opener.
- Pass: the paper never claims to beat iTransformer or Graph WaveNet on RMSE. The
  train-only class-weight rerun is the RMSE guardrail result (229.93 vs 224.34, gap
  5.59), while the 236.13 legacy checkpoint is explicitly the fully archived run used for
  downstream label-degradation and reserve audits. If any sentence treats 236.13 as the
  current accuracy target, fix it.

## 2. Cross-Site Claim Is Mechanism Replication, Not Automatic Transfer

- Where: abstract, falsification/generalization paragraph, deployment section.
- Pass: WTB train-only NMI/ARI 0.721/0.740, legacy full-audit NMI about 0.87/ARI about
  0.92, and La Haute Borne NMI/ARI 0.941/0.971 are presented as routing-recovery
  evidence. La Haute Borne must not be read as reserve/economic transfer. Reserve and
  label-degradation value remain WTB-only.

## 3. La Haute Borne Circularity Defense Is Visible

- Where: Supplementary Table A9 and the main-text sentence that references it.
- Pass: zero-Patv still gives NMI 0.953, jointly zeroing wind speed and pitch collapses
  NMI to 0.001, and randomized physics gives 0.028. The claim reads "anchor-observable
  cross-site mechanism replication, not anchor-free discovery or automatic reserve
  transfer." A reviewer asking whether 0.941 just echoes active power or pitch should find
  the answer immediately.

## 4. Kelmarsh/Penmanshiel Is A Boundary-Condition Failure

- Where: deployment-gate prose and Supplementary Table A8.
- Pass: the negative result is foregrounded as observability/routing failure: mean NMI
  0.4877 and ARI 0.5112 do not authorize gate-bin reserve use. This is a testable
  deployment condition, not hidden bad news.

## 5. Number Consistency

- Where: abstract, body, cover letter, supplementary.
- Pass: spot-check 229.93, 224.34, 5.59, 236.13, 0.721/0.740, 0.941/0.971,
  0.4877/0.5112, 0.960/0.196/0.508, 14.5%/3.6%, A10b 0.815/0.361/0.405, and A11 CI
  tokens -4.65M/-2.45M/-0.0203/-0.0072/-0.78M/-0.30M. The cover letter should match the
  abstract exactly on load-bearing numbers.

## 6. Claim Boundaries Are Intact

- Where: Limitations section and cover-letter honest boundaries.
- Pass: method is boundary-aware regularized routing, not anchor-free discovery, future
  label prediction, market dispatch optimization, reserve-policy optimality, or automatic
  cross-farm reserve transfer.

## 7. Modular Alternative Is Treated Fairly

- Where: early-warning/classifier-control paragraph and route-evolution paragraph.
- Pass: the simple issue-time anchor classifier is disclosed as stronger on clean
  standalone detection. The gate's narrower value is in-model route responsibility,
  same-run route-conditioned residual/reserve slicing, and A10b route-evolution behavior
  around transitions.

## 8. IEEE Formatting Residue Is Removed

- Pass: no Elsevier-specific "Highlights", "Nomenclature", CRediT, or graphical abstract
  text leaks into the IEEE PDF. Affiliation, corresponding author, and email are checked
  in the submission metadata.

## 9. Cross-References, Figures, Tables, Citations Resolve

- Where: full PDF skim.
- Pass: no "??" or "[?]"; every figure/table/supplementary reference points to the right
  object; captions match the cross-site mechanism-replication framing; references render
  in IEEE style with no undefined/orphan citations.

## 10. Reproducibility Statement Is Accurate

- Where: Code and data availability, cover-letter reproducibility paragraph.
- Pass: lists KDD Cup 2022, ENGIE La Haute Borne, Kelmarsh, and Penmanshiel; states raw
  third-party data are not redistributed; provenance includes anchor-stress, early-warning,
  class-weight rerun, La Haute Borne anchor audit, reserve diagnostics, and evidence-freeze
  protocols.

## 11. Cover Letter Frames The Ask Correctly

- Where: `cover_letter_tste.md`.
- Pass: leads with degraded-label wind-farm reserve screening, asks reviewers to assess
  auditable in-model routing and bounded reserve-screening consequence, and states La Haute
  Borne cross-site mechanism replication plus Kelmarsh/Penmanshiel observability/routing
  gates.

## 12. Page And Package Compliance

- Pass: main <= 10 pages, IEEEtran journal class, double column, supplementary self-contained
  and within the expected page range. Confirm the upload ZIP uses freshly rebuilt PDFs, not
  stale local copies.

When all boxes pass, upload `artifacts/tste_submission/<latest>/TSTE_UPLOAD_FILES.zip`.
