from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from main import build_parser
from windfarm_moe.evidence_export import export_strict_wtb_evidence
from windfarm_moe.utils import load_json, save_json


class EvidenceExportTests(unittest.TestCase):
    def test_parser_accepts_strict_evidence_export(self) -> None:
        args = build_parser().parse_args(["strict-evidence-export", "--output-dir", "out"])

        self.assertEqual(args.command, "strict-evidence-export")
        self.assertEqual(args.dataset, "wtb")
        self.assertEqual(args.strict_suite_dir, "artifacts/strictmask_validation_wtb_full")

    def test_export_strict_wtb_evidence_writes_source_tables_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            suite = root / "suite"
            run = suite / "wtb_bal_align_force_seed201"
            metrics_dir = run / "test_metrics"
            metrics_dir.mkdir(parents=True)
            save_json(
                metrics_dir / "metrics.json",
                {
                    "overall": {"mae": 1.0, "rmse": 2.0},
                    "switch_window": {"mae": 1.5, "rmse": 2.5},
                    "by_regime": {"pitch_control": {"mae": 3.0, "rmse": 4.0}},
                    "gate_alignment": {
                        "nmi": 0.8,
                        "ari": 0.9,
                        "expert_usage_entropy": 0.2,
                        "expert_usage_variance": 0.1,
                    },
                },
            )
            save_json(run / "training_summary.json", {"best_epoch": 3, "best_val_rmse": 1.7})
            save_json(suite / "suite_summary.json", {"rows": []})

            mechanism = root / "mechanism"
            (mechanism / "mechanism_intervention").mkdir(parents=True)
            (mechanism / "checkpoint_replay").mkdir(parents=True)
            pd.DataFrame(
                [
                    {
                        "dataset": "wtb",
                        "model": "M",
                        "intervention": "anchor_boundary_zero",
                        "delta_overall_rmse_mean": 1.0,
                        "delta_overall_rmse_ci_low": 0.5,
                        "delta_overall_rmse_ci_high": 1.5,
                        "delta_switch_rmse_mean": 1.2,
                        "delta_switch_rmse_ci_low": 0.6,
                        "delta_switch_rmse_ci_high": 1.8,
                        "drop_nmi_mean": 0.4,
                        "drop_nmi_ci_low": 0.3,
                        "drop_nmi_ci_high": 0.5,
                        "drop_ari_mean": 0.6,
                        "drop_ari_ci_low": 0.4,
                        "drop_ari_ci_high": 0.7,
                    }
                ]
            ).to_csv(mechanism / "mechanism_intervention" / "mechanism_intervention_effects.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "seed": 201,
                        "run_dir": "run_seed201",
                        "intervention": "actual",
                        "overall_rmse": 2.0,
                        "switch_rmse": 2.5,
                        "nmi": 0.8,
                        "ari": 0.9,
                    },
                    {
                        "seed": 201,
                        "run_dir": "run_seed201",
                        "intervention": "anchor_boundary_zero",
                        "overall_rmse": 3.0,
                        "switch_rmse": 3.7,
                        "nmi": 0.4,
                        "ari": 0.3,
                    },
                ]
            ).to_csv(mechanism / "mechanism_intervention" / "mechanism_intervention_raw.csv", index=False)
            pd.DataFrame([{"replay_status": "matches_reference", "n_runs": 1}]).to_csv(
                mechanism / "checkpoint_replay" / "checkpoint_replay_summary.csv", index=False
            )

            placebo = root / "placebo"
            placebo.mkdir()
            pd.DataFrame(
                [
                    {
                        "control_condition": "global_shuffle",
                        "delta_nmi_mean": 0.8,
                        "delta_nmi_ci_low": 0.7,
                        "delta_nmi_ci_high": 0.9,
                        "delta_ari_mean": 0.9,
                        "delta_ari_ci_low": 0.8,
                        "delta_ari_ci_high": 1.0,
                    }
                ]
            ).to_csv(placebo / "routing_placebo_effects.csv", index=False)
            pd.DataFrame([{"condition": "actual", "nmi_mean": 0.8, "ari_mean": 0.9}]).to_csv(
                placebo / "routing_placebo_summary.csv", index=False
            )
            pd.DataFrame(
                [
                    {
                        "seed": 201,
                        "run_dir": "run_seed201",
                        "condition": "actual",
                        "nmi": 0.8,
                        "ari": 0.9,
                    },
                    {
                        "seed": 201,
                        "run_dir": "run_seed201",
                        "condition": "global_shuffle",
                        "nmi": 0.1,
                        "ari": 0.0,
                    },
                ]
            ).to_csv(placebo / "routing_placebo_raw.csv", index=False)

            time_forward = root / "time_forward"
            time_forward.mkdir()
            pd.DataFrame(
                [
                    {
                        "block_id": 1,
                        "block_label": "early",
                        "anchor_start_min": 10,
                        "anchor_end_max": 20,
                        "overall_rmse_mean": 2.0,
                        "overall_rmse_std": 0.0,
                        "switch_rmse_mean": 2.5,
                        "switch_rmse_std": 0.0,
                        "nmi_mean": 0.8,
                        "nmi_std": 0.0,
                        "ari_mean": 0.9,
                        "ari_std": 0.0,
                    }
                ]
            ).to_csv(time_forward / "time_forward_summary.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "delta_overall_rmse_mean": 5.0,
                        "delta_switch_rmse_mean": 6.0,
                        "delta_nmi_mean": 0.1,
                    }
                ]
            ).to_csv(time_forward / "time_forward_effects.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "model": "M",
                        "block_id": 1,
                        "block_label": "early",
                        "overall_rmse": 2.0,
                        "switch_rmse": 2.5,
                        "pitch_control_rmse": 3.0,
                        "nmi": 0.8,
                        "ari": 0.9,
                        "wspd_mean": 8.0,
                        "pab_mean": 1.0,
                        "target_power_mean": 10.0,
                        "abs_ramp_mean": 1.0,
                        "mask_valid_rate": 1.0,
                        "regime_valid_rate": 1.0,
                        "boundary_share": 0.1,
                        "idle_share": 0.1,
                        "mppt_share": 0.7,
                        "pitch_control_share": 0.2,
                        "transition_share": 0.0,
                    }
                ]
            ).to_csv(time_forward / "time_forward_shift_diagnostics.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "model": "M",
                        "delta_overall_rmse_mean": 5.0,
                        "delta_overall_rmse_ci_low": 4.0,
                        "delta_overall_rmse_ci_high": 6.0,
                        "delta_abs_ramp_mean_mean": 2.0,
                        "delta_abs_ramp_mean_ci_low": 1.0,
                        "delta_abs_ramp_mean_ci_high": 3.0,
                        "delta_nmi_mean": 0.1,
                        "delta_nmi_ci_low": 0.0,
                        "delta_nmi_ci_high": 0.2,
                        "wspd_mean_ks": 0.5,
                        "regime_share_total_variation": 0.2,
                        "regime_share_jensen_shannon": 0.03,
                    }
                ]
            ).to_csv(time_forward / "time_forward_shift_effects.csv", index=False)

            boundary = root / "boundary"
            boundary.mkdir()
            pd.DataFrame(
                [
                    {
                        "slice": "boundary_band",
                        "rmse_mean": 3.0,
                        "rmse_std": 0.1,
                        "nmi_mean": 0.7,
                        "ari_mean": 0.8,
                        "n_anchor_cells_mean": 12,
                    },
                    {
                        "slice": "nonboundary_valid",
                        "rmse_mean": 2.0,
                        "rmse_std": 0.1,
                        "nmi_mean": 0.6,
                        "ari_mean": 0.7,
                        "n_anchor_cells_mean": 20,
                    },
                ]
            ).to_csv(boundary / "boundary_slice_summary.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "comparison": "boundary_band_minus_nonboundary_valid",
                        "comparator_slice": "nonboundary_valid",
                        "delta_rmse_mean": 1.0,
                        "delta_rmse_ci_low": 0.5,
                        "delta_rmse_ci_high": 1.5,
                        "delta_mae_mean": 0.8,
                        "delta_mae_ci_low": 0.4,
                        "delta_mae_ci_high": 1.2,
                    }
                ]
            ).to_csv(boundary / "boundary_slice_effects.csv", index=False)

            output_dir = export_strict_wtb_evidence(
                output_dir=root / "evidence",
                strict_suite_dir=suite,
                mechanism_dir=mechanism,
                placebo_dir=placebo,
                time_forward_dir=time_forward,
                boundary_slice_dir=boundary,
                model="M",
            )

            seed_metrics = pd.read_csv(output_dir / "tables" / "strict_wtb_seed_metrics.csv")
            manifest = load_json(output_dir / "strict_wtb_evidence_manifest.json")

            self.assertEqual(float(seed_metrics.iloc[0]["overall_rmse"]), 2.0)
            self.assertTrue((output_dir / "generated" / "table_strict_wtb_seed_metrics.tex").exists())
            self.assertTrue((output_dir / "generated" / "table_strict_wtb_boundary_slice.tex").exists())
            self.assertTrue((output_dir / "generated" / "table_strict_wtb_late_shift_diagnostics.tex").exists())
            self.assertTrue((output_dir / "generated" / "table_strict_wtb_mechanism_per_seed.tex").exists())
            self.assertTrue((output_dir / "generated" / "table_strict_wtb_placebo_per_seed.tex").exists())
            self.assertTrue((output_dir / "README.md").exists())
            self.assertIn("boundary_slice_summary_csv", manifest["outputs"])
            self.assertIn("mechanism_raw_csv", manifest["outputs"])
            self.assertIn("placebo_raw_csv", manifest["outputs"])
            self.assertIn("time_forward_shift_effects_csv", manifest["outputs"])
            self.assertIn("mechanism_per_seed_tex", manifest["outputs"])
            self.assertIn("late_shift_diagnostics_tex", manifest["outputs"])
            self.assertIn("placebo_per_seed_tex", manifest["outputs"])
            self.assertIn("seed_metrics_csv", manifest["outputs"])
            self.assertEqual(manifest["summary"]["replay_status"], "matches_reference")
            self.assertEqual(manifest["summary"]["boundary_band_rmse_mean"], 3.0)


if __name__ == "__main__":
    unittest.main()
