# TSTE Final-Read Checklist (reviewer's-eye self-check before upload)

Last updated: 2026-07-01. Use with `paper_tste_ieee.pdf` + `paper_tste_supplementary.pdf`
+ `cover_letter_tste.md` open. Each item: what a TSTE reviewer will probe / where to look /
pass criterion. Machine checks already pass (`complete_tste_number_consistency`,
`complete_ready_for_evidence_freeze`, 10pp+4pp); this list is the human read they can't do.

## 1. The headline is "recovery + accountability", never "SOTA accuracy"
- Where: abstract, Intro contributions, Results opener.
- Pass: the paper never claims to beat iTransformer/Graph WaveNet on RMSE; the 236.13 vs
  224.34 gap is stated as an explicit, priced (11.79-unit) trade-off for a complementary
  diagnostic layer. If any sentence reads as an accuracy win, fix it.

## 2. Two-benchmark claim is stated as boundary *recovery*, correctly scoped
- Where: abstract, falsification/generalization paragraph, deployment section.
- Pass: WTB NMI 0.87 + La Haute Borne NMI 0.941 are presented as the routing-recovery
  evidence; it is NOT implied that La Haute Borne also demonstrates reserve/economic value.
  Reserve + label-degradation value is explicitly WTB-only.

## 3. The circularity defense for La Haute Borne is visible and honest
- Where: Supplementary Table A9 + the main-text sentence that references it.
- Pass: the audit is shown — zero-Patv still 0.953 (not active-power feedback), Wspd+Pab
  jointly zeroed -> 0.001, randomized physics -> 0.028 (boundary anchors are load-bearing).
  Claim reads "anchor-observable positive control, not anchor-free discovery." A reviewer
  who asks "is 0.94 just the gate echoing the pitch that defines the label?" must find the
  answer here without emailing you.

## 4. Kelmarsh/Penmanshiel is presented as boundary-condition failure, not hidden
- Where: deployment-gate prose + Supplementary Table A8 (now has a positive-control "go"
  row for La Haute Borne above the no-go rows).
- Pass: the negative result is foregrounded as "where pitch observability/coverage fail,
  the mechanism does not transfer" — a two-sided, testable-condition story, not spin.

## 5. Number consistency across abstract / body / cover / supplementary
- Where: everywhere the load-bearing numbers appear.
- Pass (spot-check by eye, machine already green): 0.87, 0.941, 236.13, 224.34, 11.79,
  0.960 / 0.196 / 0.508 (six-step delay & 50% availability), 14.5% / 3.6% reserve.
  Confirm the cover letter's numbers match the abstract exactly.

## 6. Claim-boundary / limitations language is intact
- Where: Limitations section, cover-letter "Honest boundaries" list.
- Pass: method is stated as boundary-aware regularized routing that stays useful under
  label degradation — NOT anchor-free physical discovery, NOT a future-label predictor,
  NOT market/dispatch optimization, NOT authorized cross-farm reserve use.

## 7. Elsevier-template residue removed / made IEEE-appropriate
- Pass: the main manuscript now uses the short heading "AI Use Statement" with no Elsevier-specific
  boilerplate. Confirm no "Highlights", "Nomenclature (Elsevier-style)", CRediT, or "graphical
  abstract" leaked into the IEEE PDF.
- Pass: affiliations, corresponding author, and email are checked in the submission script metadata.

## 8. Cross-references, figures, tables, citations all resolve
- Where: full PDF skim.
- Pass: no "??" or "[?]"; every Fig./Table/Supplementary ref points to the right object;
  figure captions match the two-benchmark framing (no stale single-dataset captions);
  references render in IEEE style with no undefined/orphan citations. (Build log: 0 undefined.)

## 9. Code & data availability + reproducibility statement is accurate
- Where: main "Code and data availability", cover-letter "Reproducibility".
- Pass: lists KDD Cup 2022 + ENGIE La Haute Borne + Kelmarsh/Penmanshiel; states raw
  third-party data not redistributed; provenance names the anchor-stress cache/train/guard,
  early-warning, and La Haute Borne anchor audits. No promise you cannot keep.

## 10. Cover letter frames TSTE fit and the ask correctly
- Where: `cover_letter_tste.md`.
- Pass: leads with the sustainable-energy operating problem (degraded-label reserve
  screening), asks reviewers to assess the degraded-label + two-farm-recovery contribution,
  and the Transfer-role point states La Haute Borne recovery + Kelmarsh/Penmanshiel gating.
  Add editor-requested items (suggested reviewers, conflicts) if the portal requires them.

## 11. Page/format compliance
- Pass: main <= 10 pages (IEEE PES initial limit), IEEEtran journal class, double column,
  supplementary self-contained (4 pages). Confirm the PDF in the upload zip is the freshly
  rebuilt one (matches the two-benchmark text), not a stale copy.

---
When all boxes pass: upload `artifacts/tste_submission/<latest>/TSTE_UPLOAD_FILES.zip`.
