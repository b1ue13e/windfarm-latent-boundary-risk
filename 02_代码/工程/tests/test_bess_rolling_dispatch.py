"""Unit tests for Wind-BESS Rolling Dispatch Decision Optimizer."""
import unittest
import numpy as np

from src.decision.bess_rolling_dispatch import (
    BESSConfig,
    DispatchStepResult,
    DispatchTrajectoryResult,
    WindBESSRollingOptimizer,
)


class TestBESSConfig(unittest.TestCase):
    def test_default_config_is_valid(self) -> None:
        cfg = BESSConfig()
        self.assertEqual(cfg.capacity_mwh, 20.0)
        self.assertEqual(cfg.power_rating_mw, 5.0)
        self.assertAlmostEqual(cfg.dt_hours, 1.0 / 6.0)

    def test_invalid_capacity_raises(self) -> None:
        with self.assertRaises(ValueError):
            BESSConfig(capacity_mwh=-5.0)
        with self.assertRaises(ValueError):
            BESSConfig(capacity_mwh=0.0)

    def test_invalid_power_rating_raises(self) -> None:
        with self.assertRaises(ValueError):
            BESSConfig(power_rating_mw=-1.0)

    def test_invalid_efficiency_raises(self) -> None:
        with self.assertRaises(ValueError):
            BESSConfig(eta_charge=0.0)
        with self.assertRaises(ValueError):
            BESSConfig(eta_charge=1.2)
        with self.assertRaises(ValueError):
            BESSConfig(eta_discharge=-0.5)

    def test_invalid_soc_bounds_raises(self) -> None:
        with self.assertRaises(ValueError):
            BESSConfig(soc_min=0.8, soc_max=0.2)
        with self.assertRaises(ValueError):
            BESSConfig(soc_min=0.1, soc_max=0.9, soc_initial=0.05)
        with self.assertRaises(ValueError):
            BESSConfig(soc_min=0.1, soc_max=0.9, soc_initial=0.95)


class TestBESSStepDispatch(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = BESSConfig(
            capacity_mwh=10.0,
            power_rating_mw=2.0,
            eta_charge=1.0,
            eta_discharge=1.0,
            soc_min=0.0,
            soc_max=1.0,
            soc_initial=0.5,
            degradation_cost_per_mwh=10.0,
            shortage_penalty_per_mwh=100.0,
            curtailment_penalty_per_mwh=20.0,
            dt_hours=1.0,  # 1 hour for simple mental math
        )
        self.opt = WindBESSRollingOptimizer(self.cfg)

    def test_balanced_step_does_not_cycle_battery(self) -> None:
        res = self.opt.dispatch_step_heuristic(p_wind=5.0, p_commit=5.0, current_energy_mwh=5.0)
        self.assertEqual(res.p_charge, 0.0)
        self.assertEqual(res.p_discharge, 0.0)
        self.assertEqual(res.p_curtail, 0.0)
        self.assertEqual(res.p_shortage, 0.0)
        self.assertEqual(res.p_pcc, 5.0)
        self.assertEqual(res.energy_stored_mwh, 5.0)
        self.assertEqual(res.total_cost, 0.0)

    def test_surplus_charges_battery_up_to_power_limit(self) -> None:
        # Wind = 8 MW, Commit = 5 MW (surplus 3 MW). Power rating = 2 MW.
        # Battery should charge 2 MW, remaining 1 MW curtailed.
        res = self.opt.dispatch_step_heuristic(p_wind=8.0, p_commit=5.0, current_energy_mwh=5.0)
        self.assertAlmostEqual(res.p_charge, 2.0)
        self.assertAlmostEqual(res.p_discharge, 0.0)
        self.assertAlmostEqual(res.p_curtail, 1.0)
        self.assertAlmostEqual(res.p_shortage, 0.0)
        self.assertAlmostEqual(res.p_pcc, 5.0)
        self.assertAlmostEqual(res.energy_stored_mwh, 7.0)  # 5 + 2*1.0
        # Cost: 1 MW curtailment * 20 + 2 MW charge * 10 = 40
        self.assertAlmostEqual(res.cost_curtail, 20.0)
        self.assertAlmostEqual(res.cost_degradation, 20.0)
        self.assertAlmostEqual(res.total_cost, 40.0)

    def test_surplus_respects_soc_headroom(self) -> None:
        # Battery at 9.5 MWh, capacity 10 MWh. Room is 0.5 MWh.
        # Wind = 7 MW, Commit = 5 MW (surplus 2 MW).
        # Battery can only take 0.5 MWh in 1 hr (0.5 MW).
        res = self.opt.dispatch_step_heuristic(p_wind=7.0, p_commit=5.0, current_energy_mwh=9.5)
        self.assertAlmostEqual(res.p_charge, 0.5)
        self.assertAlmostEqual(res.p_curtail, 1.5)
        self.assertAlmostEqual(res.energy_stored_mwh, 10.0)
        self.assertAlmostEqual(res.soc_end, 1.0)

    def test_deficit_discharges_battery_to_mitigate_shortage(self) -> None:
        # Wind = 2 MW, Commit = 5 MW (deficit 3 MW). Power rating = 2 MW.
        # Battery discharges 2 MW, remaining 1 MW is unserved shortage.
        res = self.opt.dispatch_step_heuristic(p_wind=2.0, p_commit=5.0, current_energy_mwh=5.0)
        self.assertAlmostEqual(res.p_discharge, 2.0)
        self.assertAlmostEqual(res.p_charge, 0.0)
        self.assertAlmostEqual(res.p_shortage, 1.0)
        self.assertAlmostEqual(res.p_curtail, 0.0)
        self.assertAlmostEqual(res.p_pcc, 4.0)
        self.assertAlmostEqual(res.energy_stored_mwh, 3.0)  # 5 - 2*1.0
        # Cost: 1 MW shortage * 100 + 2 MW discharge * 10 = 120
        self.assertAlmostEqual(res.cost_shortage, 100.0)
        self.assertAlmostEqual(res.cost_degradation, 20.0)
        self.assertAlmostEqual(res.total_cost, 120.0)

    def test_deficit_respects_soc_floor(self) -> None:
        # Battery at 0.5 MWh, min SoC is 0.0. Max discharge is 0.5 MWh.
        res = self.opt.dispatch_step_heuristic(p_wind=2.0, p_commit=5.0, current_energy_mwh=0.5)
        self.assertAlmostEqual(res.p_discharge, 0.5)
        self.assertAlmostEqual(res.p_shortage, 2.5)
        self.assertAlmostEqual(res.energy_stored_mwh, 0.0)
        self.assertAlmostEqual(res.soc_end, 0.0)

    def test_efficiency_loss_in_energy_conservation(self) -> None:
        cfg = BESSConfig(
            capacity_mwh=10.0,
            power_rating_mw=5.0,
            eta_charge=0.90,
            eta_discharge=0.80,
            soc_min=0.0,
            soc_max=1.0,
            soc_initial=0.5,
            dt_hours=1.0,
        )
        opt = WindBESSRollingOptimizer(cfg)
        # Charging 2 MW for 1 hr with eta_charge=0.9 -> adds 1.8 MWh
        r_ch = opt.dispatch_step_heuristic(p_wind=7.0, p_commit=5.0, current_energy_mwh=5.0)
        self.assertAlmostEqual(r_ch.p_charge, 2.0)
        self.assertAlmostEqual(r_ch.energy_stored_mwh, 5.0 + 2.0 * 0.90)

        # Discharging 2 MW for 1 hr with eta_discharge=0.8 -> removes 2.0 / 0.8 = 2.5 MWh
        r_dis = opt.dispatch_step_heuristic(p_wind=3.0, p_commit=5.0, current_energy_mwh=5.0)
        self.assertAlmostEqual(r_dis.p_discharge, 2.0)
        self.assertAlmostEqual(r_dis.energy_stored_mwh, 5.0 - 2.0 / 0.80)


class TestBESSOptimizerTrajectoryAndLP(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = BESSConfig(
            capacity_mwh=20.0,
            power_rating_mw=5.0,
            eta_charge=0.95,
            eta_discharge=0.95,
            soc_min=0.1,
            soc_max=0.9,
            soc_initial=0.5,
            degradation_cost_per_mwh=15.0,
            shortage_penalty_per_mwh=150.0,
            curtailment_penalty_per_mwh=20.0,
            dt_hours=1.0 / 6.0,
        )
        self.opt = WindBESSRollingOptimizer(self.cfg)

    def test_lp_solver_produces_feasible_and_optimal_solution(self) -> None:
        # 12 steps (2 hours)
        np.random.seed(42)
        wind = np.array([4.0, 3.5, 6.0, 7.0, 5.5, 4.0, 3.0, 2.5, 5.0, 6.5, 7.5, 5.0])
        commit = np.full(12, 5.0)

        p_ch, p_dis, p_curt, p_short, e_traj = self.opt.solve_multi_period_lp(wind, commit)

        # 1. Non-negativity and bounds
        self.assertTrue(np.all(p_ch >= 0.0))
        self.assertTrue(np.all(p_ch <= self.cfg.power_rating_mw + 1e-6))
        self.assertTrue(np.all(p_dis >= 0.0))
        self.assertTrue(np.all(p_dis <= self.cfg.power_rating_mw + 1e-6))
        self.assertTrue(np.all(p_curt >= 0.0))
        self.assertTrue(np.all(p_short >= 0.0))

        # 2. Energy state within [soc_min, soc_max]
        e_min = self.cfg.soc_min * self.cfg.capacity_mwh
        e_max = self.cfg.soc_max * self.cfg.capacity_mwh
        self.assertTrue(np.all(e_traj >= e_min - 1e-6))
        self.assertTrue(np.all(e_traj <= e_max + 1e-6))

        # 3. Power balance: P_pcc = P_wind - P_curt + P_dis - P_ch
        p_pcc = wind - p_curt + p_dis - p_ch
        shortage = np.maximum(commit - p_pcc, 0.0)
        np.testing.assert_allclose(p_short, shortage, atol=1e-5)

        # 4. Strict check that surplus wind actually charges the battery
        # (regression test against one-sided A_ub formulation bug)
        surplus_steps = np.where(wind > commit)[0]
        self.assertGreater(len(surplus_steps), 0)
        self.assertGreater(np.sum(p_ch[surplus_steps]), 0.0)

    def test_lp_charges_battery_during_surplus_and_curtails_excess(self) -> None:
        # 3 steps of 8 MW wind with 5 MW commitment. Surplus is 3 MW each step.
        # Battery has 10 MWh capacity, 2 MW power rating, starts at 5 MWh.
        cfg_small = BESSConfig(capacity_mwh=10.0, power_rating_mw=2.0, dt_hours=1.0)
        opt_small = WindBESSRollingOptimizer(cfg_small)
        wind = np.array([8.0, 8.0, 8.0])
        commit = np.array([5.0, 5.0, 5.0])

        p_ch, p_dis, p_curt, p_short, e_traj = opt_small.solve_multi_period_lp(wind, commit)

        # Must charge up to power/headroom limits and curtail the remainder
        # In all steps, p_ch + p_curt must exactly balance surplus (3 MW)
        np.testing.assert_allclose(p_ch + p_curt, 3.0, atol=1e-5)
        self.assertTrue(np.all(p_ch <= 2.0 + 1e-6))
        self.assertGreater(np.sum(p_curt), 0.0)
        self.assertGreater(np.sum(p_ch), 0.0)
        self.assertAlmostEqual(np.sum(p_short), 0.0)

    def test_rolling_mpc_trajectory_simulation(self) -> None:
        wind = np.array([5.0, 7.0, 2.0, 4.0, 8.0, 1.0])
        commit = np.full(6, 5.0)

        res_mpc = self.opt.simulate_trajectory(wind, commit, mode="mpc")
        self.assertEqual(res_mpc.n_steps, 6)
        self.assertGreater(res_mpc.delivered_mwh, 0.0)
        self.assertGreater(res_mpc.total_cost, 0.0)
        for step in res_mpc.step_results:
            self.assertTrue(self.cfg.soc_min - 1e-5 <= step.soc_end <= self.cfg.soc_max + 1e-5)

    def test_rolling_mpc_with_forecast_error(self) -> None:
        wind_act = np.array([5.0, 3.0, 7.0, 2.0, 6.0, 4.0])
        # Forecast deviates from actuals
        wind_fc = np.array([4.0, 5.0, 5.0, 3.0, 7.0, 3.0])
        commit = np.full(6, 5.0)

        res_mpc = self.opt.simulate_rolling_mpc(
            wind_actual_mw=wind_act,
            wind_forecast_mw=wind_fc,
            commit_schedule_mw=commit,
            lookahead_steps=3,
        )
        self.assertEqual(res_mpc.n_steps, 6)
        for r in res_mpc.step_results:
            self.assertTrue(self.cfg.soc_min - 1e-5 <= r.soc_end <= self.cfg.soc_max + 1e-5)

    def test_trajectory_simulation_heuristic_and_lp(self) -> None:
        wind = np.array([5.0, 7.0, 2.0, 4.0, 8.0, 1.0])
        commit = np.full(6, 5.0)

        res_heur = self.opt.simulate_trajectory(wind, commit, mode="heuristic")
        res_lp = self.opt.simulate_trajectory(wind, commit, mode="lp")

        self.assertEqual(res_heur.n_steps, 6)
        self.assertEqual(res_lp.n_steps, 6)
        self.assertGreater(res_heur.delivered_mwh, 0.0)
        self.assertGreater(res_lp.delivered_mwh, 0.0)

    def test_benchmark_against_unbuffered_wind_proves_savings(self) -> None:
        # Realistic profile fluctuating around commitment
        np.random.seed(123)
        wind = 5.0 + 2.0 * np.sin(np.linspace(0, 4 * np.pi, 36))
        commit = np.full(36, 5.0)

        bench = self.opt.benchmark_against_unbuffered_wind(wind, commit)

        unbuf = bench["unbuffered_wind"]
        bess = bench["wind_bess"]
        comp = bench["comparison"]

        # BESS must reduce total operational cost vs unbuffered
        self.assertLess(bess["total_cost"], unbuf["total_cost"])
        self.assertGreater(comp["cost_savings_dollars"], 0.0)
        self.assertGreater(comp["cost_reduction_pct"], 10.0)  # Substantial savings
        self.assertGreater(comp["avoided_shortage_mwh"] + comp["avoided_curtailment_mwh"], 0.0)

    def test_edge_case_zero_wind(self) -> None:
        # 18 steps of zero wind with 5 MW commitment exceeds usable battery energy (8 MWh / (5 MW / 0.95) = 1.52 h = 9.1 steps)
        wind = np.zeros(18)
        commit = np.full(18, 5.0)
        res = self.opt.simulate_trajectory(wind, commit, mode="heuristic")
        self.assertEqual(res.curtailment_mwh, 0.0)
        # Battery discharges until empty (soc_min), then shortage occurs
        self.assertGreater(res.cost_shortage, 0.0)
        self.assertAlmostEqual(res.step_results[-1].soc_end, self.cfg.soc_min, places=4)


    def test_horizon_mismatch_raises_in_lp(self) -> None:
        with self.assertRaises(ValueError):
            self.opt.solve_multi_period_lp(np.ones(5), np.ones(6))

    def test_lp_terminal_soc_target(self) -> None:
        wind = np.full(6, 5.0)
        commit = np.full(6, 5.0)
        # Force final SoC to be 0.70
        _, _, _, _, e_traj = self.opt.solve_multi_period_lp(
            wind, commit, initial_energy_mwh=10.0, target_final_soc=0.70
        )
        final_soc = e_traj[-1] / self.cfg.capacity_mwh
        self.assertAlmostEqual(final_soc, 0.70, places=4)

    def test_high_degradation_cost_suppresses_battery_cycling(self) -> None:
        # If degradation cost is higher than penalty, battery shouldn't charge or discharge
        cfg_expensive = BESSConfig(
            capacity_mwh=20.0,
            power_rating_mw=5.0,
            degradation_cost_per_mwh=300.0,  # higher than shortage penalty (150) and curtailment (20)
            shortage_penalty_per_mwh=150.0,
            curtailment_penalty_per_mwh=20.0,
        )
        opt_exp = WindBESSRollingOptimizer(cfg_expensive)
        # Surplus step
        res_surplus = opt_exp.dispatch_step_heuristic(p_wind=8.0, p_commit=5.0, current_energy_mwh=10.0)
        self.assertEqual(res_surplus.p_charge, 0.0)
        self.assertEqual(res_surplus.p_curtail, 3.0)

        # Deficit step
        res_deficit = opt_exp.dispatch_step_heuristic(p_wind=2.0, p_commit=5.0, current_energy_mwh=10.0)
        self.assertEqual(res_deficit.p_discharge, 0.0)
        self.assertEqual(res_deficit.p_shortage, 3.0)


if __name__ == "__main__":
    unittest.main()

