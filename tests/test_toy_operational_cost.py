from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from main import build_parser
from windfarm_moe.operational_cost import run_engineering_unit_value_translation, run_toy_operational_cost
from windfarm_moe.utils import load_json


class ToyOperationalCostTests(unittest.TestCase):
    def test_parser_accepts_command(self) -> None:
        args = build_parser().parse_args(
            [
                "toy-operational-cost",
                "--output-dir",
                "out",
                "--main-ratio",
                "20",
                "--engineering-output-dir",
                "eng",
            ]
        )

        self.assertEqual(args.command, "toy-operational-cost")
        self.assertEqual(args.main_ratio, 20.0)
        self.assertEqual(args.engineering_output_dir, "eng")

    def test_run_combines_decision_and_probabilistic_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decision = root / "decision"
            probabilistic = root / "probabilistic"
            decision.mkdir()
            probabilistic.mkdir()
            _write_decision(decision)
            _write_probabilistic(probabilistic)

            output = run_toy_operational_cost(
                decision_dir=decision,
                probabilistic_dir=probabilistic,
                output_dir=root / "toy",
                main_ratio=10.0,
            )

            summary = pd.read_csv(output / "reserve_toy_operational_cost.csv")
            config = load_json(output / "reserve_toy_operational_cost.json")

            self.assertTrue((output / "reserve_toy_operational_cost.tex").exists())
            self.assertIn("toy_total_cost", summary.columns)
            self.assertIn("Boundary-forced router/gate-bin", set(summary["policy_label"]))
            self.assertIn("Graph WaveNet/global_quantile", set(summary["policy_label"]))
            gate = summary[summary["policy_label"].eq("Boundary-forced router/gate-bin")].iloc[0]
            self.assertAlmostEqual(float(gate["toy_total_cost"]), 55.0)
            self.assertEqual(config["main_ratio"], 10.0)

    def test_engineering_translation_reports_mwh_and_eur_scenario_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decision = root / "decision"
            probabilistic = root / "probabilistic"
            toy = root / "toy"
            engineering = root / "engineering"
            decision.mkdir()
            probabilistic.mkdir()
            _write_decision(decision)
            _write_probabilistic(probabilistic)

            run_toy_operational_cost(
                decision_dir=decision,
                probabilistic_dir=probabilistic,
                output_dir=toy,
                main_ratio=10.0,
            )
            output = run_engineering_unit_value_translation(
                decision_dir=decision,
                toy_cost_dir=toy,
                output_dir=engineering,
                main_ratio=10.0,
                reserve_prices_eur_per_mwh=[100.0],
            )

            table = pd.read_csv(output / "engineering_unit_value_translation.csv")
            same_model = table[table["comparison"].eq("Boundary gate-bin vs same-router global")].iloc[0]

            self.assertTrue((output / "table_engineering_unit_value_translation.tex").exists())
            self.assertAlmostEqual(float(same_model["delta_reserve_mwh_equiv"]), -0.005)
            self.assertAlmostEqual(float(same_model["avoided_shortage_mwh_equiv"]), 0.004)
            self.assertAlmostEqual(float(same_model["delta_total_cost_mwh_equiv"]), -0.045)
            self.assertAlmostEqual(float(same_model["delta_eur_at_100_per_mwh"]), -4.5)


def _write_decision(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "subset": "boundary",
                "cost_ratio": 10.0,
                "model": "Boundary-forced router",
                "policy": "global",
                "total_cost_mean": 100.0,
                "violation_rate_mean": 0.10,
                "reserve_energy_mean": 40.0,
                "shortage_energy_mean": 6.0,
                "valid_cells_mean": 100.0,
            },
            {
                "subset": "boundary",
                "cost_ratio": 10.0,
                "model": "Boundary-forced router",
                "policy": "gate-bin",
                "total_cost_mean": 90.0,
                "violation_rate_mean": 0.08,
                "reserve_energy_mean": 35.0,
                "shortage_energy_mean": 2.0,
                "valid_cells_mean": 100.0,
            },
            {
                "subset": "boundary",
                "cost_ratio": 10.0,
                "model": "Graph WaveNet",
                "policy": "global",
                "total_cost_mean": 95.0,
                "violation_rate_mean": 0.09,
                "reserve_energy_mean": 37.0,
                "shortage_energy_mean": 3.0,
                "valid_cells_mean": 100.0,
            },
        ]
    ).to_csv(path / "reserve_decision_by_ratio.csv", index=False)


def _write_probabilistic(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "subset": "boundary",
                "cost_ratio": 10.0,
                "model": "Graph WaveNet",
                "baseline": "global_quantile",
                "n_runs": 5,
                "total_cost_mean": 80.0,
                "violation_rate_mean": 0.07,
                "reserve_energy_mean": 30.0,
                "shortage_energy_mean": 4.0,
                "valid_cells_mean": 100.0,
            }
        ]
    ).to_csv(path / "reserve_quantile_baseline.csv", index=False)
