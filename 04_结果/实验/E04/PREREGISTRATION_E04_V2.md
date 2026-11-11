# E04-v2 Immutable Preregistration Protocol

**Status:** PRE-EXECUTION SPECIFICATION  
**Experiment:** E04-v2  
**Freeze:** `experiments/E04/PREREGISTRATION_E04_V2.json` and the preregistration-only Git commit to be recorded in the E04-v2 execution plan after commit creation.
**Execution rule:** E04-v2 may execute only against that frozen commit and the referenced input hashes. Any change requires E04-v3 with a new pre-execution commit. Any change to the frozen fields requires a new experiment version and a new preregistration commit.

## Frozen parameters

- `alpha=0.05`
- `epsilon_C=0 kWh`
- `epsilon_V=0`
- `v_max=0.10`
- Primary population: WTB Full test population
- Replication unit: 5 training seeds x 35 daily blocks, joint seed/block resampling
- Primary bootstrap: 20,000 draws, RNG seed `20261017`
- Stability diagnostic: 10,000 draws, RNG seed `20261018`
- Candidates: B, C, D, D10
- Complexity order: B < C < D < D10
- Selector: first policy satisfying cost UCB, violation-difference UCB, and absolute-violation UCB; otherwise `NO FEASIBLE POLICY`.

The selector stability frequency is diagnostic only and cannot relax primary feasibility. The action/selection population, threshold, baseline, candidate set, and uncertainty procedure are immutable after the preregistration commit.

## Provenance and receipt

`run_e04_bound.py` writes an execution plan before invoking the command. On exit code 0 and complete declared outputs, it writes an output manifest and execution receipt bound to the preregistration file SHA-256, input records, command argv, working directory, process return code, and output hashes. The selector refuses to read arrays unless the receipt, manifest, preregistration hash, and all output hashes verify.

## Historical separation

E04 v1 and its `NO FEASIBLE POLICY` result remain historical evidence with an independent review verdict of NEEDS-WORK. E04-v2 is a new immutable preregistration intended to repair temporal-precedence and output-binding blockers. It must not overwrite or retroactively certify v1.
