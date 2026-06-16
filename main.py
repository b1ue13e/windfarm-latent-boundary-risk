from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from windfarm_moe.boundary_slice import run_boundary_slice_audit
from windfarm_moe.config import DataConfig, EvalConfig, ModelConfig, TrainConfig
from windfarm_moe.decision import run_reserve_decision, run_reserve_decision_guard
from windfarm_moe.evidence_export import export_strict_wtb_evidence
from windfarm_moe.boundary_negative_controls import run_boundary_negative_controls
from windfarm_moe.external_wind import (
    ExternalWindConfig,
    fetch_external_wind_sources,
    inspect_external_wind_sources,
    preprocess_external_wind,
    run_external_wind_guard,
    run_external_wind_source_guard,
    write_external_wind_protocol,
)
from windfarm_moe.final_evidence import build_final_evidence_manifest, export_final_tables
from windfarm_moe.future_holdout import (
    run_future_holdout_evidence_guard,
    run_future_holdout_guard,
    write_future_holdout_protocol,
)
from windfarm_moe.mechanism_behavior import run_mechanism_behavior_pack
from windfarm_moe.reproducibility import run_reproducibility_manifest
from windfarm_moe.reproduction_package import write_reproduction_package
from windfarm_moe.routing_placebo import run_routing_placebo_audit
from windfarm_moe.science_readiness import run_science_readiness_dashboard
from windfarm_moe.spatial_holdout import (
    build_spatial_holdout_cache,
    run_spatial_holdout_evidence_guard,
    run_spatial_holdout_guard,
    write_spatial_holdout_protocol,
)
from windfarm_moe.strict_anchor import patch_strict_anchor_mask
from windfarm_moe.strict_baseline import run_strict_baseline_guard, write_strict_baseline_protocol
from windfarm_moe.threshold_controls import (
    run_threshold_controls_evidence_guard,
    run_threshold_controls_guard,
    run_threshold_controls_semantic_guard,
)
from windfarm_moe.time_forward import run_time_forward_audit


def ensure_cache_ready(*args, **kwargs):
    from windfarm_moe.data import ensure_cache_ready as _ensure_cache_ready

    return _ensure_cache_ready(*args, **kwargs)


def load_cache_bundle(*args, **kwargs):
    from windfarm_moe.data import load_cache_bundle as _load_cache_bundle

    return _load_cache_bundle(*args, **kwargs)


def preprocess_dataset(*args, **kwargs):
    from windfarm_moe.preprocess import preprocess_dataset as _preprocess_dataset

    return _preprocess_dataset(*args, **kwargs)


def analyze_gates(*args, **kwargs):
    from windfarm_moe.analysis import analyze_gates as _analyze_gates

    return _analyze_gates(*args, **kwargs)


def train_model(*args, **kwargs):
    from windfarm_moe.train import train_model as _train_model

    return _train_model(*args, **kwargs)


def paper_default_loss_weights(*args, **kwargs):
    from windfarm_moe.paper import paper_default_loss_weights as _paper_default_loss_weights

    return _paper_default_loss_weights(*args, **kwargs)


def resolve_capacity_matched_hidden_dim(*args, **kwargs):
    from windfarm_moe.paper import resolve_capacity_matched_hidden_dim as _resolve_capacity_matched_hidden_dim

    return _resolve_capacity_matched_hidden_dim(*args, **kwargs)


def collect_suite_run_dirs(*args, **kwargs):
    from windfarm_moe.paper import collect_suite_run_dirs as _collect_suite_run_dirs

    return _collect_suite_run_dirs(*args, **kwargs)


def aggregate_runs(*args, **kwargs):
    from windfarm_moe.paper import aggregate_runs as _aggregate_runs

    return _aggregate_runs(*args, **kwargs)


def export_revised_paper_assets(*args, **kwargs):
    from windfarm_moe.paper import export_revised_paper_assets as _export_revised_paper_assets

    return _export_revised_paper_assets(*args, **kwargs)


def build_unified_main_results_table(*args, **kwargs):
    from windfarm_moe.paper import build_unified_main_results_table as _build_unified_main_results_table

    return _build_unified_main_results_table(*args, **kwargs)


def run_paper_suite(*args, **kwargs):
    from windfarm_moe.paper import run_paper_suite as _run_paper_suite

    return _run_paper_suite(*args, **kwargs)


def run_paper_suite_parallel(*args, **kwargs):
    from windfarm_moe.paper import run_paper_suite_parallel as _run_paper_suite_parallel

    return _run_paper_suite_parallel(*args, **kwargs)


def build_wtb_sentinel_review(*args, **kwargs):
    from windfarm_moe.paper import build_wtb_sentinel_review as _build_wtb_sentinel_review

    return _build_wtb_sentinel_review(*args, **kwargs)


def run_mechanism_intervention_audit(*args, **kwargs):
    from windfarm_moe.mechanism_intervention import run_mechanism_intervention_audit as _run_mechanism_intervention_audit

    return _run_mechanism_intervention_audit(*args, **kwargs)


def run_reviewer_stat_pack(*args, **kwargs):
    from windfarm_moe.reviewer_stats import run_reviewer_stat_pack as _run_reviewer_stat_pack

    return _run_reviewer_stat_pack(*args, **kwargs)


def run_reviewer_stat_pack_guard(*args, **kwargs):
    from windfarm_moe.reviewer_stats import run_reviewer_stat_pack_guard as _run_reviewer_stat_pack_guard

    return _run_reviewer_stat_pack_guard(*args, **kwargs)


def run_strict_ablation_guard(*args, **kwargs):
    from windfarm_moe.strict_ablation import run_strict_ablation_guard as _run_strict_ablation_guard

    return _run_strict_ablation_guard(*args, **kwargs)


def run_strict_ablation_evidence_guard(*args, **kwargs):
    from windfarm_moe.strict_ablation import (
        run_strict_ablation_evidence_guard as _run_strict_ablation_evidence_guard,
    )

    return _run_strict_ablation_evidence_guard(*args, **kwargs)


def run_checkpoint_replay_audit(*args, **kwargs):
    from windfarm_moe.mechanism_intervention import run_checkpoint_replay_audit as _run_checkpoint_replay_audit

    return _run_checkpoint_replay_audit(*args, **kwargs)


def run_mechanism_evidence_gate(*args, **kwargs):
    from windfarm_moe.mechanism_intervention import run_mechanism_evidence_gate as _run_mechanism_evidence_gate

    return _run_mechanism_evidence_gate(*args, **kwargs)


def _add_common_data_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dataset", choices=["wtb", "era5", "external_wind"], default="wtb")
    parser.add_argument("--root-dir", type=str, default=".")
    parser.add_argument("--location-file", type=str, default="sdwpf_baidukddcup2022_turb_location.CSV")
    parser.add_argument("--dynamic-file", type=str, default="wtbdata_245days.csv")
    parser.add_argument("--cache-root", type=str, default="artifacts/cache")
    parser.add_argument("--max-days", type=int, default=None)
    parser.add_argument("--train-days", type=int, default=180)
    parser.add_argument("--val-days", type=int, default=30)
    parser.add_argument("--test-days", type=int, default=35)
    parser.add_argument("--holdout-days", type=int, default=0)
    parser.add_argument("--hist-len", type=int, default=36)
    parser.add_argument("--pred-len", type=int, default=24)
    parser.add_argument("--era5-zip-pattern", type=str, default="era5*.zip")
    parser.add_argument("--era5-patch-size", type=int, default=16)
    parser.add_argument("--era5-max-archives", type=int, default=None)
    parser.add_argument("--era5-helper-python", type=str, default=None)
    parser.add_argument("--era5-candidate-k", type=int, default=8)
    parser.add_argument("--farm", type=str, default="kelmarsh")
    parser.add_argument("--external-target-farm", type=str, default="")
    parser.add_argument("--external-split", choices=["chronological", "leave-one-farm-out"], default="chronological")
    parser.add_argument("--external-source-dir", type=str, default="")
    parser.add_argument("--external-rated-wind", type=float, default=10.5)
    parser.add_argument("--external-pitch-threshold", type=float, default=2.0)
    parser.add_argument("--external-cut-in-wind", type=float, default=3.0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dual-dataset regime-aware physics-aligned MoE forecasting")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preprocess_parser = subparsers.add_parser("preprocess", help="Build synchronized cache from raw files")
    _add_common_data_args(preprocess_parser)

    external_preprocess_parser = subparsers.add_parser(
        "external-wind-preprocess",
        help="Build an external Kelmarsh/Penmanshiel wind-farm cache",
    )
    _add_common_data_args(external_preprocess_parser)

    external_fetch_parser = subparsers.add_parser(
        "external-wind-fetch",
        help="Write/download the Kelmarsh/Penmanshiel Zenodo source-file manifest",
    )
    _add_common_data_args(external_fetch_parser)
    external_fetch_parser.add_argument("--output-dir", type=str, required=True)
    external_fetch_parser.add_argument("--farms", type=str, default="kelmarsh,penmanshiel")
    external_fetch_parser.add_argument("--years", type=str, default="")
    external_fetch_parser.add_argument("--no-static", action="store_true")
    external_fetch_parser.add_argument("--no-scada", action="store_true")
    external_fetch_parser.add_argument("--include-mapping", action="store_true")
    external_fetch_parser.add_argument("--file-pattern", type=str, default="")
    external_fetch_parser.add_argument("--download", action="store_true")
    external_fetch_parser.add_argument("--overwrite", action="store_true")

    external_inspect_parser = subparsers.add_parser(
        "external-wind-inspect",
        help="Inspect local external SCADA CSV/ZIP headers without preprocessing",
    )
    _add_common_data_args(external_inspect_parser)
    external_inspect_parser.add_argument("--output-dir", type=str, required=True)
    external_inspect_parser.add_argument("--farms", type=str, default="kelmarsh,penmanshiel")
    external_inspect_parser.add_argument("--max-members-per-zip", type=int, default=3)
    external_inspect_parser.add_argument("--sample-rows", type=int, default=3)

    external_protocol_parser = subparsers.add_parser(
        "external-wind-protocol",
        help="Write Kelmarsh/Penmanshiel external validation commands without executing training",
    )
    _add_common_data_args(external_protocol_parser)
    external_protocol_parser.add_argument("--output-dir", type=str, required=True)
    external_protocol_parser.add_argument("--seeds", type=str, default="201,202,203,204,205")
    external_protocol_parser.add_argument("--farms", type=str, default="kelmarsh,penmanshiel")
    external_protocol_parser.add_argument("--suite-dir", type=str, default="artifacts/external_wind_runs")

    external_guard_parser = subparsers.add_parser(
        "external-wind-guard",
        help="Verify external wind caches and completed cross-farm evidence before mechanism portability claims",
    )
    _add_common_data_args(external_guard_parser)
    external_guard_parser.add_argument("--output-dir", type=str, required=True)
    external_guard_parser.add_argument("--cache-dirs", type=str, default="")
    external_guard_parser.add_argument("--suite-dir", type=str, default="artifacts/external_wind_runs")
    external_guard_parser.add_argument("--seeds", type=str, default="201,202,203,204,205")
    external_guard_parser.add_argument(
        "--required-models",
        type=str,
        default="Graph WaveNet,PatchTST,Physics-Aligned MoE,MoE + L_bal + L_align + L_force",
    )
    external_guard_parser.add_argument("--min-nmi", type=float, default=0.50)
    external_guard_parser.add_argument("--min-ari", type=float, default=0.30)

    external_source_guard_parser = subparsers.add_parser(
        "external-wind-source-guard",
        help="Verify that the full Kelmarsh/Penmanshiel source manifest is locally downloaded and checksum-validated",
    )
    _add_common_data_args(external_source_guard_parser)
    external_source_guard_parser.add_argument("--output-dir", type=str, required=True)
    external_source_guard_parser.add_argument(
        "--manifest-path",
        type=str,
        default="artifacts/external_wind_full_manifest/external_wind_source_manifest.csv",
    )
    external_source_guard_parser.add_argument("--farms", type=str, default="kelmarsh,penmanshiel")
    external_source_guard_parser.add_argument("--min-files", type=int, default=31)
    external_source_guard_parser.add_argument("--min-total-bytes", type=int, default=10_000_000_000)

    train_parser = subparsers.add_parser("train", help="Train dense baseline or regime-aware MoE")
    _add_common_data_args(train_parser)
    train_parser.add_argument(
        "--mode",
        choices=[
            "baseline_dense",
            "baseline_stgcn",
            "baseline_graph_wavenet",
            "baseline_patchtst",
            "baseline_gat_gru",
            "baseline_graph_transformer",
            "baseline_tcn",
            "moe_no_phys",
            "moe_phys_full",
            "moe_unconstrained",
            "moe_balance_only",
            "moe_align_only",
            "moe_balance_align",
            "moe_full_no_aux",
            "moe_full_no_smooth",
            "moe_context_align",
            "moe_anchor_only",
        ],
        default="moe_phys_full",
    )
    train_parser.add_argument("--epochs", type=int, default=20)
    train_parser.add_argument("--batch-size", type=int, default=16)
    train_parser.add_argument("--lr", type=float, default=2e-3)
    train_parser.add_argument("--weight-decay", type=float, default=1e-4)
    train_parser.add_argument("--hidden-dim", type=int, default=64)
    train_parser.add_argument("--num-experts", type=int, default=None)
    train_parser.add_argument("--dropout", type=float, default=0.1)
    train_parser.add_argument("--tau", type=float, default=0.7)
    train_parser.add_argument("--patience", type=int, default=5)
    train_parser.add_argument("--align-weight", type=float, default=None)
    train_parser.add_argument("--aux-weight", type=float, default=None)
    train_parser.add_argument("--smooth-weight", type=float, default=None)
    train_parser.add_argument("--balance-weight", type=float, default=None)
    train_parser.add_argument("--physics-force-weight", type=float, default=None)
    train_parser.add_argument("--balance-top-k", type=int, default=1)
    train_parser.add_argument("--limit-train-batches", type=int, default=None)
    train_parser.add_argument("--limit-val-batches", type=int, default=None)
    train_parser.add_argument("--skip-visuals", action="store_true")
    train_parser.add_argument("--run-name", type=str, default=None)
    train_parser.add_argument("--capacity-match-dense", action="store_true")
    train_parser.add_argument("--label", type=str, default="")

    analyze_parser = subparsers.add_parser("analyze-gates", help="Generate paper figures from saved gate outputs")
    _add_common_data_args(analyze_parser)
    analyze_parser.add_argument("--run-dir", type=str, required=True)
    analyze_parser.add_argument("--split", choices=["val", "test"], default="test")
    analyze_parser.add_argument("--baseline-run-dir", type=str, default=None)
    analyze_parser.add_argument("--turbid", type=int, default=1)
    analyze_parser.add_argument("--output-dir", type=str, default=None)

    paper_export_parser = subparsers.add_parser("paper-export", help="Aggregate paper tables and copy figures")
    _add_common_data_args(paper_export_parser)
    paper_export_parser.add_argument("--output-dir", type=str, required=True)
    paper_export_parser.add_argument("--run-spec", action="append", default=[])
    paper_export_parser.add_argument("--wtb-run-spec", action="append", default=[])
    paper_export_parser.add_argument("--era5-run-spec", action="append", default=[])
    paper_export_parser.add_argument("--wtb-moe-run", type=str, default=None)
    paper_export_parser.add_argument("--wtb-dense-run", type=str, default=None)
    paper_export_parser.add_argument("--wtb-naive-run", type=str, default=None)
    paper_export_parser.add_argument("--era5-moe-run", type=str, default=None)
    paper_export_parser.add_argument("--era5-dense-run", type=str, default=None)
    paper_export_parser.add_argument("--wtb-suite-dir", action="append", default=[])
    paper_export_parser.add_argument("--era5-suite-dir", action="append", default=[])

    paper_batch_parser = subparsers.add_parser("paper-batch", help="Run the predefined paper experiment suite")
    _add_common_data_args(paper_batch_parser)
    paper_batch_parser.add_argument("--output-dir", type=str, required=True)
    paper_batch_parser.add_argument("--epochs", type=int, default=20)
    paper_batch_parser.add_argument("--batch-size", type=int, default=16)
    paper_batch_parser.add_argument("--hidden-dim", type=int, default=64)
    paper_batch_parser.add_argument("--num-experts", type=int, default=None)
    paper_batch_parser.add_argument("--dropout", type=float, default=0.1)
    paper_batch_parser.add_argument("--tau", type=float, default=0.7)
    paper_batch_parser.add_argument("--patience", type=int, default=5)
    paper_batch_parser.add_argument("--seeds", type=str, default="42,43,44")
    paper_batch_parser.add_argument("--strong-baseline-seeds", type=str, default=None)
    paper_batch_parser.add_argument("--ablation-seeds", type=str, default=None)
    paper_batch_parser.add_argument("--sensitivity-seeds", type=str, default=None)
    paper_batch_parser.add_argument("--groups", type=str, default="main")
    paper_batch_parser.add_argument("--variant-keys", type=str, default=None)
    paper_batch_parser.add_argument("--parallel", action="store_true")
    paper_batch_parser.add_argument("--max-parallel", type=int, default=None)
    paper_batch_parser.add_argument("--device-ids", type=str, default=None)
    paper_batch_parser.add_argument("--shard-id", type=int, default=0)
    paper_batch_parser.add_argument("--num-shards", type=int, default=1)
    paper_batch_parser.add_argument("--no-resume", action="store_true")
    paper_batch_parser.add_argument("--skip-visuals", action="store_true")

    sentinel_parser = subparsers.add_parser("wtb-sentinel-check", help="Compare WTB sentinel reruns against a reference suite")
    _add_common_data_args(sentinel_parser)
    sentinel_parser.add_argument("--reference-suite-dir", type=str, required=True)
    sentinel_parser.add_argument("--sentinel-suite-dir", type=str, required=True)
    sentinel_parser.add_argument("--output-path", type=str, required=True)
    sentinel_parser.add_argument("--variant-key", type=str, default="bal_align_force")
    sentinel_parser.add_argument("--overall-tolerance", type=float, default=0.03)
    sentinel_parser.add_argument("--switch-tolerance", type=float, default=0.03)
    sentinel_parser.add_argument("--nmi-drop-tolerance", type=float, default=0.05)

    reserve_parser = subparsers.add_parser("reserve-decision", help="Evaluate WTB reserve-decision value from saved runs")
    _add_common_data_args(reserve_parser)
    reserve_parser.add_argument("--output-dir", type=str, required=True)
    reserve_parser.add_argument(
        "--run-table",
        type=str,
        default="artifacts/paper_assets/tables/wtb_test_aggregated_runs.csv",
    )
    reserve_parser.add_argument("--cache-dir", type=str, default=None)
    reserve_parser.add_argument("--cost-ratios", type=str, default="2,5,10,20,50")
    reserve_parser.add_argument("--main-ratio", type=float, default=10.0)
    reserve_parser.add_argument("--quantiles", type=str, default="0.50,0.60,0.70,0.80,0.85,0.90,0.95,0.975,0.99")
    reserve_parser.add_argument("--bootstrap-samples", type=int, default=1000)
    reserve_parser.add_argument("--seed", type=int, default=42)
    reserve_parser.add_argument("--skip-plots", action="store_true")

    reserve_guard_parser = subparsers.add_parser(
        "reserve-decision-guard",
        help="Verify reserve-decision artifacts before citing operational decision evidence",
    )
    _add_common_data_args(reserve_guard_parser)
    reserve_guard_parser.add_argument("--decision-dir", type=str, default="artifacts/decision_reserve_wtb_noplots")
    reserve_guard_parser.add_argument("--output-dir", type=str, required=True)
    reserve_guard_parser.add_argument(
        "--required-models",
        type=str,
        default="Graph WaveNet,PatchTST,Physics-Aligned MoE,Boundary-forced router",
    )
    reserve_guard_parser.add_argument("--required-seeds", type=str, default="201,202,203,204,205")
    reserve_guard_parser.add_argument("--min-bootstrap-rows", type=int, default=9)
    reserve_guard_parser.add_argument("--min-seed-day-pairs", type=int, default=5)

    placebo_parser = subparsers.add_parser(
        "routing-placebo",
        help="Audit gate-regime alignment against temporal, spatial, and permutation placebo labels",
    )
    _add_common_data_args(placebo_parser)
    placebo_parser.add_argument("--output-dir", type=str, required=True)
    placebo_parser.add_argument(
        "--run-table",
        type=str,
        default="artifacts/paper_assets/tables/wtb_test_aggregated_runs.csv",
    )
    placebo_parser.add_argument("--split", choices=["val", "test", "holdout"], default="test")
    placebo_parser.add_argument(
        "--models",
        type=str,
        default="Unconstrained MoE,Physics-Aligned MoE,MoE + L_bal + L_align + L_force,Boundary-forced router",
    )
    placebo_parser.add_argument("--temporal-shifts", type=str, default="18,144")
    placebo_parser.add_argument("--bootstrap-samples", type=int, default=1000)
    placebo_parser.add_argument("--seed", type=int, default=42)

    time_forward_parser = subparsers.add_parser(
        "time-forward-audit",
        help="Slice saved split predictions into contiguous anchor-time blocks and audit late-test stability",
    )
    _add_common_data_args(time_forward_parser)
    time_forward_parser.add_argument("--output-dir", type=str, required=True)
    time_forward_parser.add_argument(
        "--run-table",
        type=str,
        default="artifacts/paper_assets/tables/wtb_test_aggregated_runs.csv",
    )
    time_forward_parser.add_argument("--split", choices=["val", "test", "holdout"], default="test")
    time_forward_parser.add_argument(
        "--models",
        type=str,
        default="Unconstrained MoE,Physics-Aligned MoE,MoE + L_bal + L_align + L_force,Boundary-forced router",
    )
    time_forward_parser.add_argument("--num-blocks", type=int, default=4)
    time_forward_parser.add_argument("--steps-per-hour", type=int, default=6)
    time_forward_parser.add_argument("--bootstrap-samples", type=int, default=1000)
    time_forward_parser.add_argument("--seed", type=int, default=42)

    boundary_parser = subparsers.add_parser(
        "boundary-slice-audit",
        help="Audit saved WTB predictions in the MPPT-to-pitch rated-wind boundary band",
    )
    _add_common_data_args(boundary_parser)
    boundary_parser.add_argument("--output-dir", type=str, required=True)
    boundary_parser.add_argument(
        "--run-table",
        type=str,
        default="artifacts/paper_assets/tables/wtb_test_aggregated_runs.csv",
    )
    boundary_parser.add_argument("--cache-dir", type=str, default="artifacts/cache/wtb_245d")
    boundary_parser.add_argument("--split", choices=["val", "test", "holdout"], default="test")
    boundary_parser.add_argument(
        "--models",
        type=str,
        default="MoE + L_bal + L_align + L_force,Boundary-forced router",
    )
    boundary_parser.add_argument("--rated-wind", type=float, default=10.5)
    boundary_parser.add_argument("--pitch-threshold", type=float, default=2.0)
    boundary_parser.add_argument("--boundary-band", type=float, default=1.0)
    boundary_parser.add_argument("--core-margin", type=float, default=1.0)
    boundary_parser.add_argument("--bootstrap-samples", type=int, default=1000)
    boundary_parser.add_argument("--seed", type=int, default=42)

    boundary_negative_parser = subparsers.add_parser(
        "boundary-negative-controls",
        help="Run wrong/fake boundary negative controls that relabel the shared boundary support",
    )
    _add_common_data_args(boundary_negative_parser)
    boundary_negative_parser.add_argument("--output-dir", type=str, required=True)
    boundary_negative_parser.add_argument(
        "--run-table",
        type=str,
        default="artifacts/paper_assets/tables/wtb_test_aggregated_runs.csv",
    )
    boundary_negative_parser.add_argument("--cache-dir", type=str, default="artifacts/cache_strictmask/wtb_245d")
    boundary_negative_parser.add_argument("--split", choices=["val", "test", "holdout"], default="test")
    boundary_negative_parser.add_argument(
        "--models",
        type=str,
        default="MoE + L_bal + L_align + L_force,Boundary-forced router",
    )
    boundary_negative_parser.add_argument(
        "--controls",
        type=str,
        default="wrong_rated_low,wrong_rated_high,wrong_pitch_low,wrong_pitch_high,random_boundary,time_shift_boundary",
    )
    boundary_negative_parser.add_argument("--rated-wind", type=float, default=10.5)
    boundary_negative_parser.add_argument("--pitch-threshold", type=float, default=2.0)
    boundary_negative_parser.add_argument("--max-control-nmi", type=float, default=0.75)
    boundary_negative_parser.add_argument("--max-control-ari", type=float, default=0.75)
    boundary_negative_parser.add_argument("--min-shared-label-change", type=float, default=0.05)
    boundary_negative_parser.add_argument("--min-positive-intervention-drop", type=float, default=0.25)
    boundary_negative_parser.add_argument("--max-control-intervention-drop", type=float, default=0.20)
    boundary_negative_parser.add_argument("--time-shift-steps", type=int, default=144)
    boundary_negative_parser.add_argument("--seed", type=int, default=42)

    evidence_parser = subparsers.add_parser(
        "strict-evidence-export",
        help="Export strict-mask WTB evidence source tables, LaTeX snippets, and SHA256 manifest",
    )
    _add_common_data_args(evidence_parser)
    evidence_parser.add_argument("--output-dir", type=str, required=True)
    evidence_parser.add_argument("--strict-suite-dir", type=str, default="artifacts/strictmask_validation_wtb_full")
    evidence_parser.add_argument("--mechanism-dir", type=str, default="artifacts/mechanism_gate_wtb_strictmask_full")
    evidence_parser.add_argument("--placebo-dir", type=str, default="artifacts/routing_placebo_wtb_strictmask_full")
    evidence_parser.add_argument("--time-forward-dir", type=str, default="artifacts/time_forward_wtb_strictmask_full")
    evidence_parser.add_argument("--boundary-slice-dir", type=str, default="artifacts/boundary_slice_wtb_strictmask_full")
    evidence_parser.add_argument("--model", type=str, default="MoE + L_bal + L_align + L_force")

    final_manifest_parser = subparsers.add_parser(
        "final-evidence-manifest",
        help="Build the single reviewer-facing evidence manifest and claim gate",
    )
    _add_common_data_args(final_manifest_parser)
    final_manifest_parser.add_argument("--output-dir", type=str, required=True)
    final_manifest_parser.add_argument("--run-table", type=str, required=True)
    final_manifest_parser.add_argument("--cache-dir", type=str, required=True)
    final_manifest_parser.add_argument("--source-artifacts", type=str, default="")
    final_manifest_parser.add_argument("--table-outputs", type=str, default="")
    final_manifest_parser.add_argument("--figure-outputs", type=str, default="")
    final_manifest_parser.add_argument("--guard-paths", type=str, default="")
    final_manifest_parser.add_argument("--external-guard", type=str, default="")
    final_manifest_parser.add_argument("--external-source-guard", type=str, default="")
    final_manifest_parser.add_argument("--split-id", type=str, default="strict-cache")
    final_manifest_parser.add_argument("--seeds", type=str, default="201,202,203,204,205")
    final_manifest_parser.add_argument("--models", type=str, default="")
    final_manifest_parser.add_argument(
        "--license-note",
        type=str,
        default="WTB/ERA5 licenses plus external wind CC-BY-4.0 where used.",
    )
    final_manifest_parser.add_argument("--min-seeds", type=int, default=5)
    final_manifest_parser.add_argument("--disallow-within-wtb-only", action="store_true")

    final_table_parser = subparsers.add_parser(
        "final-table-export",
        help="Copy final manifest-approved tables and source data into one export directory",
    )
    _add_common_data_args(final_table_parser)
    final_table_parser.add_argument("--manifest-path", type=str, required=True)
    final_table_parser.add_argument("--output-dir", type=str, required=True)
    final_table_parser.add_argument("--allow-blocked", action="store_true")

    reviewer_parser = subparsers.add_parser(
        "reviewer-stat-pack",
        help="Export per-example prediction rows, paired tests, efficiency table, and high-error gate-correct cases",
    )
    _add_common_data_args(reviewer_parser)
    reviewer_parser.add_argument("--output-dir", type=str, required=True)
    reviewer_parser.add_argument("--run-table", type=str, default="")
    reviewer_parser.add_argument("--suite-dir", action="append", default=[])
    reviewer_parser.add_argument("--cache-dir", type=str, default="")
    reviewer_parser.add_argument("--split", choices=["val", "test", "holdout"], default="test")
    reviewer_parser.add_argument("--models", type=str, default="")
    reviewer_parser.add_argument("--reference-model", type=str, default="MoE + L_bal + L_align + L_force")
    reviewer_parser.add_argument("--baseline-models", type=str, default="")
    reviewer_parser.add_argument("--steps-per-hour", type=int, default=6)
    reviewer_parser.add_argument("--bootstrap-samples", type=int, default=1000)
    reviewer_parser.add_argument("--permutation-samples", type=int, default=1000)
    reviewer_parser.add_argument("--max-per-example-rows", type=int, default=0)
    reviewer_parser.add_argument("--max-paired-examples", type=int, default=100000)
    reviewer_parser.add_argument("--top-k-failures", type=int, default=12)
    reviewer_parser.add_argument("--rated-wind", type=float, default=10.5)
    reviewer_parser.add_argument("--boundary-band", type=float, default=1.0)
    reviewer_parser.add_argument("--seed", type=int, default=42)

    reviewer_guard_parser = subparsers.add_parser(
        "reviewer-stat-pack-guard",
        help="Verify reviewer statistics pack files before citing per-example, paired-test, efficiency, and failure-case evidence",
    )
    _add_common_data_args(reviewer_guard_parser)
    reviewer_guard_parser.add_argument(
        "--pack-dir",
        type=str,
        default="artifacts/reviewer_stat_pack_wtb_strictmask_available_20260611",
    )
    reviewer_guard_parser.add_argument("--output-dir", type=str, required=True)
    reviewer_guard_parser.add_argument("--min-runs", type=int, default=20)
    reviewer_guard_parser.add_argument("--min-paired-rows", type=int, default=1)
    reviewer_guard_parser.add_argument("--min-per-example-runs", type=int, default=1)
    reviewer_guard_parser.add_argument("--min-failure-cases", type=int, default=1)
    reviewer_guard_parser.add_argument("--min-boundary-failure-cases", type=int, default=1)
    reviewer_guard_parser.add_argument("--required-models", type=str, default="")
    reviewer_guard_parser.add_argument("--required-seeds", type=str, default="")

    behavior_parser = subparsers.add_parser(
        "mechanism-behavior-pack",
        help="Export behavior-change evidence: expert curves, lead/lag, boundary errors, residuals, and failure cases",
    )
    _add_common_data_args(behavior_parser)
    behavior_parser.add_argument("--output-dir", type=str, required=True)
    behavior_parser.add_argument(
        "--run-table",
        type=str,
        default="artifacts/paper_assets/tables/wtb_test_aggregated_runs.csv",
    )
    behavior_parser.add_argument("--split", choices=["val", "test", "holdout"], default="test")
    behavior_parser.add_argument(
        "--models",
        type=str,
        default="MoE + L_bal + L_align + L_force,Boundary-forced router",
    )
    behavior_parser.add_argument("--rated-wind", type=float, default=10.5)
    behavior_parser.add_argument("--boundary-band", type=float, default=1.0)
    behavior_parser.add_argument("--top-k-failures", type=int, default=20)

    repro_parser = subparsers.add_parser(
        "reproducibility-manifest",
        help="Create a reviewer-facing reproducibility and compliance file manifest",
    )
    _add_common_data_args(repro_parser)
    repro_parser.add_argument("--output-dir", type=str, required=True)
    repro_parser.add_argument("--hash-max-mb", type=float, default=25.0)

    reproduction_package_parser = subparsers.add_parser(
        "reproduction-package",
        help="Write one-command reproduction entry points for guards, active queues, and submission artifacts",
    )
    _add_common_data_args(reproduction_package_parser)
    reproduction_package_parser.add_argument("--output-dir", type=str, required=True)

    future_parser = subparsers.add_parser(
        "future-holdout-protocol",
        help="Write a pre-specified WTB future-period holdout protocol without executing training",
    )
    _add_common_data_args(future_parser)
    future_parser.add_argument("--output-dir", type=str, required=True)
    future_parser.add_argument("--seeds", type=str, default="301,302,303,304,305")

    guard_parser = subparsers.add_parser(
        "future-holdout-guard",
        help="Validate raw files, protocol split, and cache split before future-holdout execution",
    )
    _add_common_data_args(guard_parser)
    guard_parser.add_argument("--protocol-dir", type=str, required=True)
    guard_parser.add_argument("--output-dir", type=str, required=True)

    future_evidence_guard_parser = subparsers.add_parser(
        "future-holdout-evidence-guard",
        help="Verify completed future-holdout runs and downstream audits before citing holdout evidence",
    )
    _add_common_data_args(future_evidence_guard_parser)
    future_evidence_guard_parser.add_argument("--protocol-dir", type=str, required=True)
    future_evidence_guard_parser.add_argument("--output-dir", type=str, required=True)
    future_evidence_guard_parser.add_argument("--suite-dir", type=str, default="artifacts/future_holdout_wtb_strictmask_runs")
    future_evidence_guard_parser.add_argument("--cache-dir", type=str, default="artifacts/cache_strictmask_future/wtb_245d")
    future_evidence_guard_parser.add_argument(
        "--mechanism-dir",
        type=str,
        default="",
    )
    future_evidence_guard_parser.add_argument(
        "--placebo-dir",
        type=str,
        default="",
    )
    future_evidence_guard_parser.add_argument(
        "--boundary-slice-dir",
        type=str,
        default="",
    )
    future_evidence_guard_parser.add_argument(
        "--reviewer-pack-dir",
        type=str,
        default="",
    )
    future_evidence_guard_parser.add_argument("--seeds", type=str, default="")
    future_evidence_guard_parser.add_argument("--variant-key", type=str, default="bal_align_force")
    future_evidence_guard_parser.add_argument("--model-mode", type=str, default="moe_full_no_aux")
    future_evidence_guard_parser.add_argument("--experiment-group", type=str, default="ablation")
    future_evidence_guard_parser.add_argument("--split", choices=["val", "test", "holdout"], default="holdout")
    future_evidence_guard_parser.add_argument("--allow-missing-gate-alignment", action="store_true")

    strict_baseline_parser = subparsers.add_parser(
        "strict-baseline-protocol",
        help="Write a fair strict-cache WTB strong-baseline rerun protocol without executing training",
    )
    _add_common_data_args(strict_baseline_parser)
    strict_baseline_parser.add_argument("--output-dir", type=str, required=True)
    strict_baseline_parser.add_argument("--suite-dir", type=str, default="artifacts/strictmask_baseline_rerun_wtb_full")
    strict_baseline_parser.add_argument(
        "--variant-keys",
        type=str,
        default="graph_wavenet,graph_transformer,gat_gru,patchtst",
    )
    strict_baseline_parser.add_argument("--seeds", type=str, default="201,202,203,204,205")
    strict_baseline_parser.add_argument("--epochs", type=int, default=20)
    strict_baseline_parser.add_argument("--batch-size", type=int, default=16)
    strict_baseline_parser.add_argument("--hidden-dim", type=int, default=64)

    strict_baseline_guard_parser = subparsers.add_parser(
        "strict-baseline-guard",
        help="Validate strict cache and completion status before using WTB strong-baseline reruns",
    )
    _add_common_data_args(strict_baseline_guard_parser)
    strict_baseline_guard_parser.add_argument("--protocol-dir", type=str, required=True)
    strict_baseline_guard_parser.add_argument("--output-dir", type=str, required=True)
    strict_baseline_guard_parser.add_argument("--suite-dir", type=str, default="artifacts/strictmask_baseline_rerun_wtb_full")
    strict_baseline_guard_parser.add_argument("--variant-keys", type=str, default=None)
    strict_baseline_guard_parser.add_argument("--seeds", type=str, default=None)

    strict_ablation_guard_parser = subparsers.add_parser(
        "strict-ablation-guard",
        help="Verify strict-cache WTB ablation rerun completeness and routing-control coverage",
    )
    _add_common_data_args(strict_ablation_guard_parser)
    strict_ablation_guard_parser.add_argument("--output-dir", type=str, required=True)
    strict_ablation_guard_parser.add_argument("--suite-dir", type=str, default="artifacts/strictmask_ablation_rerun_wtb_full")
    strict_ablation_guard_parser.add_argument(
        "--variant-keys",
        type=str,
        default="dense,unconstrained,bal,align,bal_align,bal_align_force,bal_align_force_smooth,context_align_force,anchor_only,full",
    )
    strict_ablation_guard_parser.add_argument("--seeds", type=str, default="201,202,203,204,205")

    strict_ablation_evidence_guard_parser = subparsers.add_parser(
        "strict-ablation-evidence-guard",
        help="Verify strict-cache ablation runs and routing-control mechanism gate before citing ablation evidence",
    )
    _add_common_data_args(strict_ablation_evidence_guard_parser)
    strict_ablation_evidence_guard_parser.add_argument("--output-dir", type=str, required=True)
    strict_ablation_evidence_guard_parser.add_argument(
        "--suite-dir",
        type=str,
        default="artifacts/strictmask_ablation_rerun_wtb_full",
    )
    strict_ablation_evidence_guard_parser.add_argument(
        "--routing-gate-dir",
        type=str,
        default="artifacts/strictmask_ablation_routing_controls_gate",
    )
    strict_ablation_evidence_guard_parser.add_argument(
        "--variant-keys",
        type=str,
        default="dense,unconstrained,bal,align,bal_align,bal_align_force,bal_align_force_smooth,context_align_force,anchor_only,full",
    )
    strict_ablation_evidence_guard_parser.add_argument("--seeds", type=str, default="201,202,203,204,205")
    strict_ablation_evidence_guard_parser.add_argument(
        "--gate-variant-keys",
        type=str,
        default="bal_align_force,context_align_force,anchor_only",
    )

    threshold_controls_guard_parser = subparsers.add_parser(
        "threshold-controls-guard",
        help="Verify strict-cache WTB wrong-threshold sensitivity controls before using them as mechanism evidence",
    )
    _add_common_data_args(threshold_controls_guard_parser)
    threshold_controls_guard_parser.add_argument("--output-dir", type=str, required=True)
    threshold_controls_guard_parser.add_argument("--suite-dir", type=str, default="artifacts/strictmask_threshold_controls_wtb")
    threshold_controls_guard_parser.add_argument(
        "--variant-keys",
        type=str,
        default="sens_rated_7p0,sens_rated_13p0,sens_pitch_0p5,sens_pitch_20p0",
    )
    threshold_controls_guard_parser.add_argument("--seeds", type=str, default="201,202,203,204,205")

    threshold_controls_evidence_guard_parser = subparsers.add_parser(
        "threshold-controls-evidence-guard",
        help="Verify strict-cache wrong-threshold runs and reviewer-stat evidence before citing threshold controls",
    )
    _add_common_data_args(threshold_controls_evidence_guard_parser)
    threshold_controls_evidence_guard_parser.add_argument("--output-dir", type=str, required=True)
    threshold_controls_evidence_guard_parser.add_argument("--suite-dir", type=str, default="artifacts/strictmask_threshold_controls_wtb")
    threshold_controls_evidence_guard_parser.add_argument(
        "--reviewer-pack-dir",
        type=str,
        default="artifacts/strictmask_threshold_controls_reviewer_stats",
    )
    threshold_controls_evidence_guard_parser.add_argument(
        "--semantic-guard-dir",
        type=str,
        default="artifacts/strict_threshold_controls_semantic_guard_wtb_strictmask",
    )
    threshold_controls_evidence_guard_parser.add_argument(
        "--boundary-negative-guard-dir",
        type=str,
        default="artifacts/boundary_negative_controls_wtb",
    )
    threshold_controls_evidence_guard_parser.add_argument(
        "--variant-keys",
        type=str,
        default="sens_rated_7p0,sens_rated_13p0,sens_pitch_0p5,sens_pitch_20p0",
    )
    threshold_controls_evidence_guard_parser.add_argument("--seeds", type=str, default="201,202,203,204,205")

    threshold_controls_semantic_guard_parser = subparsers.add_parser(
        "threshold-controls-semantic-guard",
        help="Verify wrong-threshold checkpoints do not reproduce canonical routing semantics or intervention effects",
    )
    _add_common_data_args(threshold_controls_semantic_guard_parser)
    threshold_controls_semantic_guard_parser.add_argument("--output-dir", type=str, required=True)
    threshold_controls_semantic_guard_parser.add_argument(
        "--mechanism-dir",
        type=str,
        default="artifacts/strictmask_threshold_controls_mechanism",
    )
    threshold_controls_semantic_guard_parser.add_argument(
        "--positive-mechanism-dir",
        type=str,
        default="artifacts/mechanism_gate_wtb_strictmask_full/mechanism_intervention",
    )
    threshold_controls_semantic_guard_parser.add_argument(
        "--variant-keys",
        type=str,
        default="sens_rated_7p0,sens_rated_13p0,sens_pitch_0p5,sens_pitch_20p0",
    )
    threshold_controls_semantic_guard_parser.add_argument("--seeds", type=str, default="201,202,203,204,205")
    threshold_controls_semantic_guard_parser.add_argument("--max-wrong-actual-nmi", type=float, default=0.75)
    threshold_controls_semantic_guard_parser.add_argument("--max-wrong-boundary-drop-nmi", type=float, default=0.60)
    threshold_controls_semantic_guard_parser.add_argument("--min-positive-actual-nmi", type=float, default=0.75)
    threshold_controls_semantic_guard_parser.add_argument("--min-positive-boundary-drop-nmi", type=float, default=0.40)
    threshold_controls_semantic_guard_parser.add_argument("--min-nmi-gap-from-positive", type=float, default=0.10)
    threshold_controls_semantic_guard_parser.add_argument("--min-boundary-drop-gap-from-positive", type=float, default=0.10)

    spatial_protocol_parser = subparsers.add_parser(
        "spatial-holdout-protocol",
        help="Write a WTB spatial turbine-group holdout protocol derived from a strict cache",
    )
    _add_common_data_args(spatial_protocol_parser)
    spatial_protocol_parser.add_argument("--output-dir", type=str, required=True)
    spatial_protocol_parser.add_argument("--source-cache-dir", type=str, default="artifacts/cache_strictmask/wtb_245d")
    spatial_protocol_parser.add_argument("--output-cache-root", type=str, default="artifacts/cache_strictmask_spatial_east")
    spatial_protocol_parser.add_argument("--suite-dir", type=str, default="artifacts/spatial_holdout_wtb_east_runs")
    spatial_protocol_parser.add_argument("--strategy", type=str, default="east")
    spatial_protocol_parser.add_argument("--fraction", type=float, default=0.2)
    spatial_protocol_parser.add_argument("--seeds", type=str, default="401,402,403,404,405")

    spatial_cache_parser = subparsers.add_parser(
        "spatial-holdout-cache",
        help="Build a derived WTB strict cache for spatial turbine-group holdout",
    )
    _add_common_data_args(spatial_cache_parser)
    spatial_cache_parser.add_argument("--source-cache-dir", type=str, default="artifacts/cache_strictmask/wtb_245d")
    spatial_cache_parser.add_argument("--output-cache-root", type=str, default="artifacts/cache_strictmask_spatial_east")
    spatial_cache_parser.add_argument("--strategy", type=str, default="east")
    spatial_cache_parser.add_argument("--fraction", type=float, default=0.2)

    spatial_guard_parser = subparsers.add_parser(
        "spatial-holdout-guard",
        help="Verify strict-anchor and turbine-group masking before spatial holdout training/evidence",
    )
    _add_common_data_args(spatial_guard_parser)
    spatial_guard_parser.add_argument("--protocol-dir", type=str, required=True)
    spatial_guard_parser.add_argument("--output-dir", type=str, required=True)
    spatial_guard_parser.add_argument("--source-cache-dir", type=str, default="artifacts/cache_strictmask/wtb_245d")
    spatial_guard_parser.add_argument("--output-cache-root", type=str, default="artifacts/cache_strictmask_spatial_east")
    spatial_guard_parser.add_argument("--suite-dir", type=str, default="artifacts/spatial_holdout_wtb_east_runs")
    spatial_guard_parser.add_argument("--strategy", type=str, default="east")
    spatial_guard_parser.add_argument("--fraction", type=float, default=0.2)
    spatial_guard_parser.add_argument("--seeds", type=str, default="401,402,403,404,405")
    spatial_guard_parser.add_argument("--variant-keys", type=str, default="bal_align_force,context_align_force,anchor_only")

    spatial_evidence_guard_parser = subparsers.add_parser(
        "spatial-holdout-evidence-guard",
        help="Verify completed spatial turbine-group holdout runs and downstream audits before citing held-out-turbine evidence",
    )
    _add_common_data_args(spatial_evidence_guard_parser)
    spatial_evidence_guard_parser.add_argument("--protocol-dir", type=str, required=True)
    spatial_evidence_guard_parser.add_argument("--output-dir", type=str, required=True)
    spatial_evidence_guard_parser.add_argument("--suite-dir", type=str, default="artifacts/spatial_holdout_wtb_east_runs")
    spatial_evidence_guard_parser.add_argument("--cache-dir", type=str, default="artifacts/cache_strictmask_spatial_east/wtb_245d")
    spatial_evidence_guard_parser.add_argument(
        "--mechanism-dir",
        type=str,
        default="",
    )
    spatial_evidence_guard_parser.add_argument(
        "--reviewer-pack-dir",
        type=str,
        default="",
    )
    spatial_evidence_guard_parser.add_argument("--seeds", type=str, default="401,402,403,404,405")
    spatial_evidence_guard_parser.add_argument(
        "--variant-keys",
        type=str,
        default="bal_align_force,context_align_force,anchor_only",
    )

    readiness_parser = subparsers.add_parser(
        "science-readiness-dashboard",
        help="Summarize Science-style experiment readiness across strict baselines, holdouts, reviewer stats, and ablations",
    )
    _add_common_data_args(readiness_parser)
    readiness_parser.add_argument("--output-dir", type=str, required=True)
    readiness_parser.add_argument("--strict-baseline-guard", type=str, default="")
    readiness_parser.add_argument("--future-holdout-guard", type=str, default="")
    readiness_parser.add_argument("--future-holdout-evidence-guard", type=str, default="")
    readiness_parser.add_argument("--spatial-holdout-guard", type=str, default="")
    readiness_parser.add_argument("--spatial-holdout-evidence-guard", type=str, default="")
    readiness_parser.add_argument("--strict-ablation-guard", type=str, default="")
    readiness_parser.add_argument("--strict-ablation-evidence-guard", type=str, default="")
    readiness_parser.add_argument("--threshold-controls-guard", type=str, default="")
    readiness_parser.add_argument("--threshold-controls-evidence-guard", type=str, default="")
    readiness_parser.add_argument("--reviewer-pack-guard", type=str, default="")
    readiness_parser.add_argument("--reproducibility-manifest", type=str, default="")
    readiness_parser.add_argument("--reviewer-pack-config", type=str, default="")
    readiness_parser.add_argument("--external-wind-guard", type=str, default="")
    readiness_parser.add_argument("--external-wind-source-guard", type=str, default="")
    readiness_parser.add_argument("--final-evidence-manifest", type=str, default="")
    readiness_parser.add_argument("--audit-doc", type=str, default="")
    readiness_parser.add_argument("--manuscript-doc", type=str, default="")
    readiness_parser.add_argument("--ablation-suite-dir", type=str, default="")

    strict_anchor_parser = subparsers.add_parser(
        "strict-anchor-mask-cache",
        help="Patch a WTB cache so regime-valid masks require observed anchor Wspd and Pab_mean",
    )
    _add_common_data_args(strict_anchor_parser)
    strict_anchor_parser.add_argument("--cache-dir", type=str, required=True)
    strict_anchor_parser.add_argument("--output-dir", type=str, default="")

    intervention_parser = subparsers.add_parser(
        "mechanism-intervention",
        help="Replay trained WTB MoE checkpoints after targeted physical-variable interventions",
    )
    _add_common_data_args(intervention_parser)
    intervention_parser.add_argument("--output-dir", type=str, required=True)
    intervention_parser.add_argument(
        "--run-table",
        type=str,
        default="artifacts/routing_placebo_wtb_clean/curated_wtb_gate_runs.csv",
    )
    intervention_parser.add_argument("--cache-dir", type=str, default="artifacts/cache/wtb_245d")
    intervention_parser.add_argument("--split", choices=["val", "test", "holdout"], default="test")
    intervention_parser.add_argument(
        "--models",
        type=str,
        default="Physics-Aligned MoE,MoE + L_bal + L_align + L_force",
    )
    intervention_parser.add_argument(
        "--interventions",
        type=str,
        default="actual,anchor_boundary_zero,anchor_boundary_wrong_threshold_shift,anchor_random_physics,anchor_wspd_only,anchor_pab_only,anchor_boundary_node_shuffle,anchor_boundary_global_shuffle,anchor_wake_zero,anchor_all_zero,history_boundary_zero,history_boundary_missing,history_nonboundary_zero",
    )
    intervention_parser.add_argument("--batch-size", type=int, default=128)
    intervention_parser.add_argument("--bootstrap-samples", type=int, default=1000)
    intervention_parser.add_argument("--seed", type=int, default=42)
    intervention_parser.add_argument("--device", type=str, default="auto")

    replay_parser = subparsers.add_parser(
        "checkpoint-replay",
        help="Replay best_model.pt checkpoints and compare them with saved split metrics",
    )
    _add_common_data_args(replay_parser)
    replay_parser.add_argument("--output-dir", type=str, required=True)
    replay_parser.add_argument(
        "--run-table",
        type=str,
        default="artifacts/routing_placebo_wtb_clean/curated_wtb_gate_runs.csv",
    )
    replay_parser.add_argument("--cache-dir", type=str, default="artifacts/cache/wtb_245d")
    replay_parser.add_argument("--split", choices=["val", "test", "holdout"], default="test")
    replay_parser.add_argument("--models", type=str, default="")
    replay_parser.add_argument("--batch-size", type=int, default=512)
    replay_parser.add_argument("--device", type=str, default="auto")

    mechanism_gate_parser = subparsers.add_parser(
        "mechanism-gate",
        help="Build a corrected-run table, enforce checkpoint replay, and optionally run mechanism interventions",
    )
    _add_common_data_args(mechanism_gate_parser)
    mechanism_gate_parser.add_argument("--suite-dir", type=str, required=True)
    mechanism_gate_parser.add_argument("--output-dir", type=str, required=True)
    mechanism_gate_parser.add_argument("--cache-dir", type=str, default="artifacts/cache/wtb_245d")
    mechanism_gate_parser.add_argument("--split", choices=["val", "test", "holdout"], default="test")
    mechanism_gate_parser.add_argument("--models", type=str, default="MoE + L_bal + L_align + L_force")
    mechanism_gate_parser.add_argument("--variant-keys", type=str, default="bal_align_force")
    mechanism_gate_parser.add_argument("--experiment-groups", type=str, default="ablation")
    mechanism_gate_parser.add_argument(
        "--interventions",
        type=str,
        default="actual,anchor_boundary_zero,anchor_boundary_wrong_threshold_shift,anchor_random_physics,anchor_wspd_only,anchor_pab_only,anchor_boundary_node_shuffle,anchor_boundary_global_shuffle,anchor_wake_zero,anchor_all_zero",
    )
    mechanism_gate_parser.add_argument("--batch-size", type=int, default=512)
    mechanism_gate_parser.add_argument("--bootstrap-samples", type=int, default=1000)
    mechanism_gate_parser.add_argument("--seed", type=int, default=42)
    mechanism_gate_parser.add_argument("--device", type=str, default="auto")
    mechanism_gate_parser.add_argument("--skip-intervention", action="store_true")
    return parser


def _make_data_config(args: argparse.Namespace) -> DataConfig:
    return DataConfig(
        dataset=args.dataset,
        root_dir=Path(args.root_dir),
        location_file=args.location_file,
        dynamic_file=args.dynamic_file,
        cache_root=args.cache_root,
        max_days=args.max_days,
        train_days=args.train_days,
        val_days=args.val_days,
        test_days=args.test_days,
        holdout_days=args.holdout_days,
        hist_len=args.hist_len,
        pred_len=args.pred_len,
        era5_zip_pattern=args.era5_zip_pattern,
        era5_patch_size=args.era5_patch_size,
        era5_max_archives=args.era5_max_archives,
        era5_helper_python=args.era5_helper_python,
        era5_candidate_k=args.era5_candidate_k,
        external_farm=args.farm,
        external_target_farm=args.external_target_farm,
        external_split=args.external_split,
        external_source_dir=args.external_source_dir,
        external_rated_wind=args.external_rated_wind,
        external_pitch_threshold=args.external_pitch_threshold,
        external_cut_in_wind=args.external_cut_in_wind,
    )


def _default_num_experts(dataset: str) -> int:
    return 4 if dataset in {"wtb", "external_wind"} else 3


def _parse_run_spec(raw_specs: list[str]) -> list[tuple[str, Path]]:
    parsed = []
    for raw in raw_specs:
        if "::" not in raw:
            raise ValueError(f"run-spec must use LABEL::PATH format, got: {raw}")
        label, path_str = raw.split("::", 1)
        parsed.append((label, Path(path_str)))
    return parsed


def _default_loss_weights(dataset: str) -> dict[str, float]:
    return paper_default_loss_weights(dataset)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    data_config = _make_data_config(args)

    if args.command == "preprocess":
        cache_dir = preprocess_dataset(data_config)
        print(f"Cache ready at: {cache_dir}")
        return

    if args.command == "external-wind-preprocess":
        cache_dir = preprocess_external_wind(ExternalWindConfig.from_data_config(data_config))
        print(f"External wind cache ready at: {cache_dir}")
        return

    if args.command == "external-wind-fetch":
        output_dir = fetch_external_wind_sources(
            output_dir=Path(args.output_dir),
            source_dir=Path(args.external_source_dir) if args.external_source_dir else Path("data/external_wind"),
            farms=args.farms,
            years=args.years,
            include_static=not args.no_static,
            include_scada=not args.no_scada,
            include_mapping=args.include_mapping,
            file_pattern=args.file_pattern,
            download=args.download,
            overwrite=args.overwrite,
        )
        print(f"External wind source manifest saved to: {output_dir}")
        return

    if args.command == "external-wind-inspect":
        output_dir = inspect_external_wind_sources(
            source_dir=Path(args.external_source_dir) if args.external_source_dir else Path("data/external_wind"),
            output_dir=Path(args.output_dir),
            farms=args.farms,
            max_members_per_zip=args.max_members_per_zip,
            sample_rows=args.sample_rows,
        )
        print(f"External wind SCADA inspection saved to: {output_dir}")
        return

    if args.command == "external-wind-protocol":
        output_dir = write_external_wind_protocol(
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            source_dir=Path(args.external_source_dir) if args.external_source_dir else Path("data/external_wind"),
            cache_root=Path(args.cache_root),
            seeds=args.seeds,
            farms=args.farms,
            suite_dir=Path(args.suite_dir),
        )
        print(f"External wind protocol saved to: {output_dir}")
        return

    if args.command == "external-wind-guard":
        output_dir = run_external_wind_guard(
            output_dir=Path(args.output_dir),
            cache_dirs=args.cache_dirs,
            suite_dir=Path(args.suite_dir),
            seeds=args.seeds,
            required_models=args.required_models,
            min_nmi=args.min_nmi,
            min_ari=args.min_ari,
        )
        print(f"External wind guard saved to: {output_dir}")
        return

    if args.command == "external-wind-source-guard":
        output_dir = run_external_wind_source_guard(
            output_dir=Path(args.output_dir),
            manifest_path=Path(args.manifest_path),
            farms=args.farms,
            min_files=args.min_files,
            min_total_bytes=args.min_total_bytes,
        )
        print(f"External wind source guard saved to: {output_dir}")
        return

    if args.command == "train":
        cache_dir = ensure_cache_ready(data_config)
        bundle = load_cache_bundle(cache_dir)
        model_config = ModelConfig(
            hidden_dim=args.hidden_dim,
            num_experts=args.num_experts or _default_num_experts(args.dataset),
            dropout=args.dropout,
            tau=args.tau,
        )
        if args.capacity_match_dense and args.mode == "baseline_dense":
            matched_hidden = resolve_capacity_matched_hidden_dim(
                bundle=bundle,
                mode=args.mode,
                hidden_dim=model_config.hidden_dim,
                num_experts=model_config.num_experts,
                tau=model_config.tau,
                dropout=model_config.dropout,
            )
            model_config.hidden_dim = matched_hidden
        train_config = TrainConfig(
            mode=args.mode,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.lr,
            weight_decay=args.weight_decay,
            patience=args.patience,
            align_weight=args.align_weight if args.align_weight is not None else _default_loss_weights(args.dataset)["align"],
            aux_weight=args.aux_weight if args.aux_weight is not None else _default_loss_weights(args.dataset)["aux"],
            smooth_weight=args.smooth_weight if args.smooth_weight is not None else _default_loss_weights(args.dataset)["smooth"],
            balance_weight=(
                args.balance_weight if args.balance_weight is not None else _default_loss_weights(args.dataset)["balance"]
            ),
            physics_force_weight=(
                args.physics_force_weight
                if args.physics_force_weight is not None
                else _default_loss_weights(args.dataset)["physics_force"]
            ),
            balance_top_k=args.balance_top_k,
            label=args.label,
            limit_train_batches=args.limit_train_batches,
            limit_val_batches=args.limit_val_batches,
        )
        eval_config = EvalConfig(
            skip_visuals=args.skip_visuals,
            save_predictions=True,
            switch_window=3 * int(bundle.metadata.get("steps_per_hour", 6)),
        )
        run_name = args.run_name or f"{args.dataset}_{args.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_dir = Path(data_config.root_dir) / "artifacts" / "runs" / run_name
        result = train_model(bundle, output_dir, model_config, train_config, eval_config)
        if args.dataset == "external_wind":
            result.update(
                {
                    "dataset": "external_wind",
                    "farm": data_config.external_farm,
                    "target_farm": data_config.external_target_farm,
                    "external_split": data_config.external_split,
                    "source_url": bundle.metadata.get("source_url", ""),
                    "target_source_url": bundle.metadata.get("target_source_url", ""),
                    "license": bundle.metadata.get("license", ""),
                }
            )
            from windfarm_moe.utils import save_json

            save_json(output_dir / "training_summary.json", result)
        print(
            f"Training finished. Best epoch: {result['best_epoch']}, "
            f"best val RMSE: {result['best_val_rmse']:.4f}"
        )
        return

    if args.command == "analyze-gates":
        cache_dir = ensure_cache_ready(data_config)
        bundle = load_cache_bundle(cache_dir)
        output_dir = analyze_gates(
            bundle=bundle,
            run_dir=Path(args.run_dir),
            dataset=args.dataset,
            split=args.split,
            baseline_run_dir=Path(args.baseline_run_dir) if args.baseline_run_dir else None,
            turbid=args.turbid if args.dataset == "wtb" else None,
            output_dir=Path(args.output_dir) if args.output_dir else None,
        )
        print(f"Analysis artifacts saved to: {output_dir}")
        return

    if args.command == "paper-export":
        output_dir = Path(args.output_dir)
        table_dir = output_dir / "tables"
        wtb_specs = _parse_run_spec(args.wtb_run_spec)
        era5_specs = _parse_run_spec(args.era5_run_spec)
        if args.run_spec:
            parsed = _parse_run_spec(args.run_spec)
            if args.dataset == "wtb":
                wtb_specs.extend(parsed)
            else:
                era5_specs.extend(parsed)
        for suite_dir in args.wtb_suite_dir:
            wtb_specs.extend(collect_suite_run_dirs(Path(suite_dir), "wtb"))
        for suite_dir in args.era5_suite_dir:
            era5_specs.extend(collect_suite_run_dirs(Path(suite_dir), "era5"))
        if args.wtb_dense_run:
            wtb_specs.append(("Capacity-Matched Dense Diffusion-GRU", Path(args.wtb_dense_run)))
        if args.wtb_naive_run:
            wtb_specs.append(("Unconstrained MoE", Path(args.wtb_naive_run)))
        if args.wtb_moe_run:
            wtb_specs.append(("Physics-Aligned MoE", Path(args.wtb_moe_run)))
        if args.era5_dense_run:
            era5_specs.append(("Capacity-Matched Dense Diffusion-GRU", Path(args.era5_dense_run)))
        if args.era5_moe_run:
            era5_specs.append(("Physics-Aligned MoE", Path(args.era5_moe_run)))

        needs_wtb = bool(wtb_specs)
        needs_era5 = bool(era5_specs)
        wtb_bundle = None
        era5_bundle = None
        if needs_wtb:
            wtb_data_config = DataConfig(
                dataset="wtb",
                root_dir=Path(args.root_dir),
                location_file=args.location_file,
                dynamic_file=args.dynamic_file,
                cache_root=args.cache_root,
                max_days=args.max_days,
                train_days=args.train_days,
                val_days=args.val_days,
                test_days=args.test_days,
                holdout_days=args.holdout_days,
                hist_len=args.hist_len,
                pred_len=args.pred_len,
            )
            wtb_bundle = load_cache_bundle(ensure_cache_ready(wtb_data_config))
        if needs_era5:
            era5_data_config = DataConfig(
                dataset="era5",
                root_dir=Path(args.root_dir),
                hist_len=args.hist_len,
                pred_len=args.pred_len,
                era5_zip_pattern=args.era5_zip_pattern,
                era5_patch_size=args.era5_patch_size,
                era5_max_archives=args.era5_max_archives,
                era5_helper_python=args.era5_helper_python,
                era5_candidate_k=args.era5_candidate_k,
            )
            era5_bundle = load_cache_bundle(ensure_cache_ready(era5_data_config))

        wtb_df = aggregate_runs("wtb", wtb_specs, table_dir) if wtb_specs else pd.DataFrame()
        era5_df = aggregate_runs("era5", era5_specs, table_dir) if era5_specs else pd.DataFrame()
        wtb_sensitivity_df = (
            wtb_df[wtb_df["experiment_group"] == "sensitivity"].copy()
            if (not wtb_df.empty and "experiment_group" in wtb_df.columns)
            else pd.DataFrame()
        )
        if wtb_bundle is not None and era5_bundle is not None and not wtb_df.empty and not era5_df.empty:
            export_revised_paper_assets(
                wtb_bundle=wtb_bundle,
                era5_bundle=era5_bundle,
                wtb_df=wtb_df,
                era5_df=era5_df,
                output_dir=output_dir,
                hidden_dim=64,
                wtb_num_experts=_default_num_experts("wtb"),
                era5_num_experts=_default_num_experts("era5"),
                tau=0.7,
                dropout=0.1,
                wtb_sensitivity_df=wtb_sensitivity_df,
            )
            build_unified_main_results_table(
                table_dir / "wtb_test_aggregated_runs.csv",
                table_dir / "era5_test_aggregated_runs.csv",
                table_dir / "table_main_results.csv",
            )
        print(f"Paper artifacts saved to: {output_dir}")
        return

    if args.command == "paper-batch":
        if args.dataset == "external_wind" and args.seeds == "42,43,44":
            raise ValueError(
                "paper-batch --dataset external_wind requires explicit --seeds 201,202,203,204,205 for the fixed external protocol."
            )
        if args.dataset == "external_wind" and not args.external_source_dir and not data_config.cache_dir().exists():
            raise ValueError(
                "paper-batch --dataset external_wind requires --external-source-dir unless the external cache already exists."
            )
        cache_dir = ensure_cache_ready(data_config)
        bundle = load_cache_bundle(cache_dir)
        model_config = ModelConfig(
            hidden_dim=args.hidden_dim,
            num_experts=args.num_experts or _default_num_experts(args.dataset),
            dropout=args.dropout,
            tau=args.tau,
            primary_num_classes=bundle.metadata["primary_num_classes"],
            gate_physics_dim=int(bundle.physics.shape[-1]),
        )
        train_config = TrainConfig(
            mode="moe_phys_full",
            epochs=args.epochs,
            batch_size=args.batch_size,
            patience=args.patience,
            align_weight=_default_loss_weights(args.dataset)["align"],
            aux_weight=_default_loss_weights(args.dataset)["aux"],
            smooth_weight=_default_loss_weights(args.dataset)["smooth"],
            balance_weight=_default_loss_weights(args.dataset)["balance"],
            physics_force_weight=_default_loss_weights(args.dataset)["physics_force"],
        )
        eval_config = EvalConfig(
            skip_visuals=args.skip_visuals,
            save_predictions=True,
            switch_window=3 * int(bundle.metadata.get("steps_per_hour", 6)),
        )
        seeds = [int(token.strip()) for token in args.seeds.split(",") if token.strip()]
        strong_baseline_seeds = (
            [int(token.strip()) for token in args.strong_baseline_seeds.split(",") if token.strip()]
            if args.strong_baseline_seeds
            else seeds
        )
        ablation_seeds = (
            [int(token.strip()) for token in args.ablation_seeds.split(",") if token.strip()]
            if args.ablation_seeds
            else seeds
        )
        sensitivity_seeds = (
            [int(token.strip()) for token in args.sensitivity_seeds.split(",") if token.strip()]
            if args.sensitivity_seeds
            else ablation_seeds
        )
        groups = [token.strip() for token in args.groups.split(",") if token.strip()]
        variant_keys = (
            [token.strip() for token in args.variant_keys.split(",") if token.strip()]
            if args.variant_keys
            else None
        )
        if args.parallel:
            device_ids = (
                [int(token.strip()) for token in args.device_ids.split(",") if token.strip()]
                if args.device_ids
                else None
            )
            run_paper_suite_parallel(
                cache_dir=cache_dir,
                output_root=Path(args.output_dir),
                dataset=args.dataset,
                seeds=seeds,
                base_model_config=model_config,
                base_train_config=train_config,
                eval_config=eval_config,
                groups=groups,
                strong_baseline_seeds=strong_baseline_seeds,
                ablation_seeds=ablation_seeds,
                sensitivity_seeds=sensitivity_seeds,
                variant_keys=variant_keys,
                device_ids=device_ids,
                max_parallel=args.max_parallel,
                resume=not args.no_resume,
                shard_id=args.shard_id,
                num_shards=args.num_shards,
            )
        else:
            run_paper_suite(
                bundle=bundle,
                output_root=Path(args.output_dir),
                dataset=args.dataset,
                seeds=seeds,
                base_model_config=model_config,
                base_train_config=train_config,
                eval_config=eval_config,
                groups=groups,
                strong_baseline_seeds=strong_baseline_seeds,
                ablation_seeds=ablation_seeds,
                sensitivity_seeds=sensitivity_seeds,
                variant_keys=variant_keys,
            )
        print(f"Paper batch finished in: {args.output_dir}")
        return

    if args.command == "wtb-sentinel-check":
        review_path = build_wtb_sentinel_review(
            reference_suite_dir=Path(args.reference_suite_dir),
            sentinel_suite_dir=Path(args.sentinel_suite_dir),
            output_path=Path(args.output_path),
            variant_key=args.variant_key,
            overall_tolerance=args.overall_tolerance,
            switch_tolerance=args.switch_tolerance,
            nmi_drop_tolerance=args.nmi_drop_tolerance,
        )
        print(f"WTB sentinel review saved to: {review_path}")
        return

    if args.command == "reserve-decision":
        if args.dataset != "wtb":
            raise ValueError("reserve-decision currently supports only --dataset wtb")
        cache_dir = Path(args.cache_dir) if args.cache_dir else ensure_cache_ready(data_config)
        output_dir = run_reserve_decision(
            run_table=Path(args.run_table),
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            cache_dir=cache_dir,
            cost_ratios=[float(token.strip()) for token in args.cost_ratios.split(",") if token.strip()],
            main_ratio=args.main_ratio,
            quantiles=[float(token.strip()) for token in args.quantiles.split(",") if token.strip()],
            bootstrap_samples=args.bootstrap_samples,
            seed=args.seed,
            make_plots=not args.skip_plots,
        )
        print(f"Reserve-decision artifacts saved to: {output_dir}")
        return

    if args.command == "reserve-decision-guard":
        if args.dataset != "wtb":
            raise ValueError("reserve-decision-guard currently supports only --dataset wtb")
        output_dir = run_reserve_decision_guard(
            decision_dir=Path(args.decision_dir),
            output_dir=Path(args.output_dir),
            required_models=args.required_models,
            required_seeds=args.required_seeds,
            min_bootstrap_rows=args.min_bootstrap_rows,
            min_seed_day_pairs=args.min_seed_day_pairs,
        )
        print(f"Reserve-decision guard saved to: {output_dir}")
        return

    if args.command == "routing-placebo":
        shifts = [int(token.strip()) for token in args.temporal_shifts.split(",") if token.strip()]
        output_dir = run_routing_placebo_audit(
            run_table=Path(args.run_table),
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            split=args.split,
            models=args.models,
            temporal_shifts=shifts,
            seed=args.seed,
            bootstrap_samples=args.bootstrap_samples,
        )
        print(f"Routing placebo audit saved to: {output_dir}")
        return

    if args.command == "time-forward-audit":
        output_dir = run_time_forward_audit(
            run_table=Path(args.run_table),
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            split=args.split,
            models=args.models,
            num_blocks=args.num_blocks,
            steps_per_hour=args.steps_per_hour,
            bootstrap_samples=args.bootstrap_samples,
            seed=args.seed,
        )
        print(f"Time-forward audit saved to: {output_dir}")
        return

    if args.command == "boundary-slice-audit":
        output_dir = run_boundary_slice_audit(
            run_table=Path(args.run_table),
            cache_dir=Path(args.cache_dir),
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            split=args.split,
            models=args.models,
            rated_wind=args.rated_wind,
            pitch_threshold=args.pitch_threshold,
            boundary_band=args.boundary_band,
            core_margin=args.core_margin,
            bootstrap_samples=args.bootstrap_samples,
            seed=args.seed,
        )
        print(f"Boundary-slice audit saved to: {output_dir}")
        return

    if args.command == "boundary-negative-controls":
        output_dir = run_boundary_negative_controls(
            run_table=Path(args.run_table),
            cache_dir=Path(args.cache_dir),
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            split=args.split,
            models=args.models,
            controls=args.controls,
            rated_wind=args.rated_wind,
            pitch_threshold=args.pitch_threshold,
            max_control_nmi=args.max_control_nmi,
            max_control_ari=args.max_control_ari,
            min_shared_label_change=args.min_shared_label_change,
            min_positive_intervention_drop=args.min_positive_intervention_drop,
            max_control_intervention_drop=args.max_control_intervention_drop,
            time_shift_steps=args.time_shift_steps,
            seed=args.seed,
        )
        print(f"Boundary negative controls saved to: {output_dir}")
        return

    if args.command == "strict-evidence-export":
        output_dir = export_strict_wtb_evidence(
            output_dir=Path(args.output_dir),
            strict_suite_dir=Path(args.strict_suite_dir),
            mechanism_dir=Path(args.mechanism_dir),
            placebo_dir=Path(args.placebo_dir),
            time_forward_dir=Path(args.time_forward_dir),
            boundary_slice_dir=Path(args.boundary_slice_dir),
            model=args.model,
        )
        print(f"Strict WTB evidence source package saved to: {output_dir}")
        return

    if args.command == "final-evidence-manifest":
        output_dir = build_final_evidence_manifest(
            output_dir=Path(args.output_dir),
            run_table=Path(args.run_table),
            cache_dir=Path(args.cache_dir),
            source_artifacts=args.source_artifacts,
            table_outputs=args.table_outputs,
            figure_outputs=args.figure_outputs,
            guard_paths=args.guard_paths,
            external_guard=Path(args.external_guard) if args.external_guard else None,
            external_source_guard=Path(args.external_source_guard) if args.external_source_guard else None,
            dataset=args.dataset,
            farm=args.farm if args.dataset == "external_wind" else "",
            split_id=args.split_id,
            seeds=args.seeds,
            models=args.models,
            license_note=args.license_note,
            min_seeds=args.min_seeds,
            allow_within_wtb_only=not args.disallow_within_wtb_only,
        )
        print(f"Final evidence manifest saved to: {output_dir}")
        return

    if args.command == "final-table-export":
        output_dir = export_final_tables(
            manifest_path=Path(args.manifest_path),
            output_dir=Path(args.output_dir),
            fail_on_blocked=not args.allow_blocked,
        )
        print(f"Final table export saved to: {output_dir}")
        return

    if args.command == "reviewer-stat-pack":
        output_dir = run_reviewer_stat_pack(
            dataset=args.dataset,
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            run_table=Path(args.run_table) if args.run_table else None,
            suite_dirs=[Path(path) for path in args.suite_dir],
            cache_dir=Path(args.cache_dir) if args.cache_dir else None,
            split=args.split,
            models=args.models,
            reference_model=args.reference_model,
            baseline_models=args.baseline_models,
            steps_per_hour=args.steps_per_hour,
            bootstrap_samples=args.bootstrap_samples,
            permutation_samples=args.permutation_samples,
            max_per_example_rows=args.max_per_example_rows,
            max_paired_examples=args.max_paired_examples,
            top_k_failures=args.top_k_failures,
            rated_wind=args.rated_wind,
            boundary_band=args.boundary_band,
            seed=args.seed,
        )
        print(f"Reviewer statistics pack saved to: {output_dir}")
        return

    if args.command == "reviewer-stat-pack-guard":
        output_dir = run_reviewer_stat_pack_guard(
            pack_dir=Path(args.pack_dir),
            output_dir=Path(args.output_dir),
            min_runs=args.min_runs,
            min_paired_rows=args.min_paired_rows,
            min_per_example_runs=args.min_per_example_runs,
            min_failure_cases=args.min_failure_cases,
            min_boundary_failure_cases=args.min_boundary_failure_cases,
            required_models=args.required_models,
            required_seeds=args.required_seeds,
        )
        print(f"Reviewer statistics pack guard saved to: {output_dir}")
        return

    if args.command == "mechanism-behavior-pack":
        output_dir = run_mechanism_behavior_pack(
            run_table=Path(args.run_table),
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            split=args.split,
            models=args.models,
            rated_wind=args.rated_wind,
            boundary_band=args.boundary_band,
            top_k_failures=args.top_k_failures,
        )
        print(f"Mechanism behavior pack saved to: {output_dir}")
        return

    if args.command == "reproducibility-manifest":
        output_dir = run_reproducibility_manifest(
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            hash_max_mb=args.hash_max_mb,
        )
        print(f"Reproducibility manifest saved to: {output_dir}")
        return

    if args.command == "reproduction-package":
        output_dir = write_reproduction_package(output_dir=Path(args.output_dir))
        print(f"Reproduction package saved to: {output_dir}")
        return

    if args.command == "future-holdout-protocol":
        seeds = [int(token.strip()) for token in args.seeds.split(",") if token.strip()]
        output_dir = write_future_holdout_protocol(
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            cache_root=args.cache_root,
            train_days=args.train_days,
            val_days=args.val_days,
            test_days=args.test_days,
            holdout_days=args.holdout_days,
            hist_len=args.hist_len,
            pred_len=args.pred_len,
            seeds=seeds,
        )
        print(f"Future holdout protocol saved to: {output_dir}")
        return

    if args.command == "future-holdout-guard":
        output_dir = run_future_holdout_guard(
            protocol_dir=Path(args.protocol_dir),
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            cache_root=args.cache_root,
            train_days=args.train_days,
            val_days=args.val_days,
            test_days=args.test_days,
            holdout_days=args.holdout_days,
            hist_len=args.hist_len,
            pred_len=args.pred_len,
            location_file=args.location_file,
            dynamic_file=args.dynamic_file,
        )
        print(f"Future holdout guard saved to: {output_dir}")
        return

    if args.command == "future-holdout-evidence-guard":
        output_dir = run_future_holdout_evidence_guard(
            protocol_dir=Path(args.protocol_dir),
            output_dir=Path(args.output_dir),
            suite_dir=Path(args.suite_dir),
            cache_dir=Path(args.cache_dir),
            mechanism_dir=Path(args.mechanism_dir) if args.mechanism_dir else None,
            placebo_dir=Path(args.placebo_dir) if args.placebo_dir else None,
            boundary_slice_dir=Path(args.boundary_slice_dir) if args.boundary_slice_dir else None,
            reviewer_pack_dir=Path(args.reviewer_pack_dir) if args.reviewer_pack_dir else None,
            seeds=args.seeds or None,
            variant_key=args.variant_key,
            model_mode=args.model_mode,
            experiment_group=args.experiment_group,
            split=args.split,
            require_gate_alignment=not args.allow_missing_gate_alignment,
        )
        print(f"Future holdout evidence guard saved to: {output_dir}")
        return

    if args.command == "strict-baseline-protocol":
        output_dir = write_strict_baseline_protocol(
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            cache_root=args.cache_root,
            suite_dir=Path(args.suite_dir),
            train_days=args.train_days,
            val_days=args.val_days,
            test_days=args.test_days,
            hist_len=args.hist_len,
            pred_len=args.pred_len,
            variant_keys=args.variant_keys,
            seeds=args.seeds,
            epochs=args.epochs,
            batch_size=args.batch_size,
            hidden_dim=args.hidden_dim,
        )
        print(f"Strict baseline protocol saved to: {output_dir}")
        return

    if args.command == "strict-baseline-guard":
        output_dir = run_strict_baseline_guard(
            protocol_dir=Path(args.protocol_dir),
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            cache_root=args.cache_root,
            suite_dir=Path(args.suite_dir),
            train_days=args.train_days,
            val_days=args.val_days,
            test_days=args.test_days,
            hist_len=args.hist_len,
            pred_len=args.pred_len,
            variant_keys=args.variant_keys,
            seeds=args.seeds,
        )
        print(f"Strict baseline guard saved to: {output_dir}")
        return

    if args.command == "strict-ablation-guard":
        output_dir = run_strict_ablation_guard(
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            cache_root=args.cache_root,
            suite_dir=Path(args.suite_dir),
            train_days=args.train_days,
            val_days=args.val_days,
            test_days=args.test_days,
            hist_len=args.hist_len,
            pred_len=args.pred_len,
            variant_keys=args.variant_keys,
            seeds=args.seeds,
        )
        print(f"Strict ablation guard saved to: {output_dir}")
        return

    if args.command == "strict-ablation-evidence-guard":
        output_dir = run_strict_ablation_evidence_guard(
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            cache_root=args.cache_root,
            suite_dir=Path(args.suite_dir),
            routing_gate_dir=Path(args.routing_gate_dir),
            train_days=args.train_days,
            val_days=args.val_days,
            test_days=args.test_days,
            hist_len=args.hist_len,
            pred_len=args.pred_len,
            variant_keys=args.variant_keys,
            seeds=args.seeds,
            gate_variant_keys=args.gate_variant_keys,
        )
        print(f"Strict ablation evidence guard saved to: {output_dir}")
        return

    if args.command == "threshold-controls-guard":
        output_dir = run_threshold_controls_guard(
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            cache_root=args.cache_root,
            suite_dir=Path(args.suite_dir),
            train_days=args.train_days,
            val_days=args.val_days,
            test_days=args.test_days,
            hist_len=args.hist_len,
            pred_len=args.pred_len,
            variant_keys=args.variant_keys,
            seeds=args.seeds,
        )
        print(f"Threshold controls guard saved to: {output_dir}")
        return

    if args.command == "threshold-controls-evidence-guard":
        output_dir = run_threshold_controls_evidence_guard(
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            cache_root=args.cache_root,
            suite_dir=Path(args.suite_dir),
            reviewer_pack_dir=Path(args.reviewer_pack_dir),
            semantic_guard_dir=Path(args.semantic_guard_dir),
            boundary_negative_guard_dir=Path(args.boundary_negative_guard_dir),
            train_days=args.train_days,
            val_days=args.val_days,
            test_days=args.test_days,
            hist_len=args.hist_len,
            pred_len=args.pred_len,
            variant_keys=args.variant_keys,
            seeds=args.seeds,
        )
        print(f"Threshold controls evidence guard saved to: {output_dir}")
        return

    if args.command == "threshold-controls-semantic-guard":
        output_dir = run_threshold_controls_semantic_guard(
            output_dir=Path(args.output_dir),
            mechanism_dir=Path(args.mechanism_dir),
            positive_mechanism_dir=Path(args.positive_mechanism_dir),
            variant_keys=args.variant_keys,
            seeds=args.seeds,
            max_wrong_actual_nmi=args.max_wrong_actual_nmi,
            max_wrong_boundary_drop_nmi=args.max_wrong_boundary_drop_nmi,
            min_positive_actual_nmi=args.min_positive_actual_nmi,
            min_positive_boundary_drop_nmi=args.min_positive_boundary_drop_nmi,
            min_nmi_gap_from_positive=args.min_nmi_gap_from_positive,
            min_boundary_drop_gap_from_positive=args.min_boundary_drop_gap_from_positive,
        )
        print(f"Threshold controls semantic guard saved to: {output_dir}")
        return

    if args.command == "spatial-holdout-protocol":
        output_dir = write_spatial_holdout_protocol(
            output_dir=Path(args.output_dir),
            source_cache_dir=Path(args.source_cache_dir),
            output_cache_root=args.output_cache_root,
            suite_dir=Path(args.suite_dir),
            strategy=args.strategy,
            fraction=args.fraction,
            seeds=args.seeds,
        )
        print(f"Spatial holdout protocol saved to: {output_dir}")
        return

    if args.command == "spatial-holdout-cache":
        output_cache_dir = Path(args.root_dir) / args.output_cache_root / "wtb_245d"
        output_dir = build_spatial_holdout_cache(
            source_cache_dir=Path(args.source_cache_dir),
            output_cache_dir=output_cache_dir,
            strategy=args.strategy,
            fraction=args.fraction,
        )
        print(f"Spatial holdout cache saved to: {output_dir}")
        return

    if args.command == "spatial-holdout-guard":
        output_dir = run_spatial_holdout_guard(
            protocol_dir=Path(args.protocol_dir),
            output_dir=Path(args.output_dir),
            source_cache_dir=Path(args.source_cache_dir),
            output_cache_root=args.output_cache_root,
            suite_dir=Path(args.suite_dir),
            strategy=args.strategy,
            fraction=args.fraction,
            seeds=args.seeds,
            variant_keys=args.variant_keys,
        )
        print(f"Spatial holdout guard saved to: {output_dir}")
        return

    if args.command == "spatial-holdout-evidence-guard":
        output_dir = run_spatial_holdout_evidence_guard(
            protocol_dir=Path(args.protocol_dir),
            output_dir=Path(args.output_dir),
            suite_dir=Path(args.suite_dir),
            cache_dir=Path(args.cache_dir),
            mechanism_dir=Path(args.mechanism_dir) if args.mechanism_dir else None,
            reviewer_pack_dir=Path(args.reviewer_pack_dir) if args.reviewer_pack_dir else None,
            seeds=args.seeds,
            variant_keys=args.variant_keys,
        )
        print(f"Spatial holdout evidence guard saved to: {output_dir}")
        return

    if args.command == "science-readiness-dashboard":
        output_dir = run_science_readiness_dashboard(
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            strict_baseline_guard=Path(args.strict_baseline_guard) if args.strict_baseline_guard else None,
            future_holdout_guard=Path(args.future_holdout_guard) if args.future_holdout_guard else None,
            future_holdout_evidence_guard=Path(args.future_holdout_evidence_guard)
            if args.future_holdout_evidence_guard
            else None,
            spatial_holdout_guard=Path(args.spatial_holdout_guard) if args.spatial_holdout_guard else None,
            spatial_holdout_evidence_guard=Path(args.spatial_holdout_evidence_guard)
            if args.spatial_holdout_evidence_guard
            else None,
            strict_ablation_guard=Path(args.strict_ablation_guard) if args.strict_ablation_guard else None,
            strict_ablation_evidence_guard=Path(args.strict_ablation_evidence_guard)
            if args.strict_ablation_evidence_guard
            else None,
            threshold_controls_guard=Path(args.threshold_controls_guard) if args.threshold_controls_guard else None,
            threshold_controls_evidence_guard=Path(args.threshold_controls_evidence_guard)
            if args.threshold_controls_evidence_guard
            else None,
            reviewer_pack_guard=Path(args.reviewer_pack_guard) if args.reviewer_pack_guard else None,
            reproducibility_manifest=Path(args.reproducibility_manifest) if args.reproducibility_manifest else None,
            reviewer_pack_config=Path(args.reviewer_pack_config) if args.reviewer_pack_config else None,
            external_wind_guard=Path(args.external_wind_guard) if args.external_wind_guard else None,
            external_wind_source_guard=Path(args.external_wind_source_guard) if args.external_wind_source_guard else None,
            final_evidence_manifest=Path(args.final_evidence_manifest) if args.final_evidence_manifest else None,
            audit_doc=Path(args.audit_doc) if args.audit_doc else None,
            manuscript_doc=Path(args.manuscript_doc) if args.manuscript_doc else None,
            ablation_suite_dir=Path(args.ablation_suite_dir) if args.ablation_suite_dir else None,
        )
        print(f"Science readiness dashboard saved to: {output_dir}")
        return

    if args.command == "strict-anchor-mask-cache":
        output_dir = patch_strict_anchor_mask(
            cache_dir=Path(args.cache_dir),
            output_dir=Path(args.output_dir) if args.output_dir else None,
        )
        print(f"Strict-anchor mask patch saved to: {output_dir}")
        return

    if args.command == "mechanism-intervention":
        output_dir = run_mechanism_intervention_audit(
            run_table=Path(args.run_table),
            cache_dir=Path(args.cache_dir),
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            split=args.split,
            models=args.models,
            interventions=args.interventions,
            batch_size=args.batch_size,
            seed=args.seed,
            bootstrap_samples=args.bootstrap_samples,
            device=args.device,
        )
        print(f"Mechanism intervention audit saved to: {output_dir}")
        return

    if args.command == "checkpoint-replay":
        output_dir = run_checkpoint_replay_audit(
            run_table=Path(args.run_table),
            cache_dir=Path(args.cache_dir),
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            split=args.split,
            models=args.models,
            batch_size=args.batch_size,
            device=args.device,
        )
        print(f"Checkpoint replay audit saved to: {output_dir}")
        return

    if args.command == "mechanism-gate":
        output_dir = run_mechanism_evidence_gate(
            suite_dir=Path(args.suite_dir),
            cache_dir=Path(args.cache_dir),
            output_dir=Path(args.output_dir),
            root_dir=Path(args.root_dir),
            dataset=args.dataset,
            split=args.split,
            models=args.models,
            variant_keys=args.variant_keys,
            experiment_groups=args.experiment_groups,
            interventions=args.interventions,
            batch_size=args.batch_size,
            bootstrap_samples=args.bootstrap_samples,
            seed=args.seed,
            device=args.device,
            run_intervention_on_pass=not args.skip_intervention,
        )
        print(f"Mechanism evidence gate saved to: {output_dir}")
        return

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
