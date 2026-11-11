"""Wind-BESS Rolling Dispatch Decision Optimizer for IEEE TSTE / Q1 standard.

Replaces legacy single-step Newsvendor toy models with a full power-engineering
rolling-horizon dispatch formulation combining:
1. Battery Energy Storage System (BESS) State of Charge (SoC) dynamics and efficiency losses
2. Cell degradation cost per unit energy throughput
3. Point of Common Coupling (PCC) power balancing
4. Grid tracking shortage penalty and wind curtailment opportunity cost
5. Receding horizon / Model Predictive Control (MPC) rolling dispatch with HiGHS LP solver
6. Fast deterministic closed-loop dispatcher for long-horizon benchmarking
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from scipy.optimize import linprog


@dataclass
class BESSConfig:
    """Configuration parameters for Battery Energy Storage System (BESS)."""
    capacity_mwh: float = 20.0
    power_rating_mw: float = 5.0
    eta_charge: float = 0.95
    eta_discharge: float = 0.95
    soc_min: float = 0.10
    soc_max: float = 0.90
    soc_initial: float = 0.50
    degradation_cost_per_mwh: float = 15.0      # $/MWh battery throughput wear
    shortage_penalty_per_mwh: float = 150.0     # $/MWh unserved committed power
    curtailment_penalty_per_mwh: float = 20.0   # $/MWh opportunity / curtailment loss
    dt_hours: float = 1.0 / 6.0                 # 10 minutes default step size

    def __post_init__(self) -> None:
        if self.capacity_mwh <= 0:
            raise ValueError(f"capacity_mwh must be positive, got {self.capacity_mwh}")
        if self.power_rating_mw < 0:
            raise ValueError(f"power_rating_mw must be non-negative, got {self.power_rating_mw}")
        if not (0.0 < self.eta_charge <= 1.0):
            raise ValueError(f"eta_charge must be in (0, 1], got {self.eta_charge}")
        if not (0.0 < self.eta_discharge <= 1.0):
            raise ValueError(f"eta_discharge must be in (0, 1], got {self.eta_discharge}")
        if not (0.0 <= self.soc_min < self.soc_max <= 1.0):
            raise ValueError(f"Invalid SoC bounds: min={self.soc_min}, max={self.soc_max}")
        if not (self.soc_min <= self.soc_initial <= self.soc_max):
            raise ValueError(
                f"Initial SoC {self.soc_initial} out of bounds [{self.soc_min}, {self.soc_max}]"
            )
        if self.dt_hours <= 0:
            raise ValueError(f"dt_hours must be positive, got {self.dt_hours}")


@dataclass
class DispatchStepResult:
    """Results for a single dispatch time step."""
    step: int
    p_wind: float
    p_commit: float
    p_charge: float
    p_discharge: float
    p_curtail: float
    p_shortage: float
    p_pcc: float
    soc_start: float
    soc_end: float
    energy_stored_mwh: float
    cost_shortage: float
    cost_curtail: float
    cost_degradation: float
    total_cost: float


@dataclass
class DispatchTrajectoryResult:
    """Aggregated results across a complete dispatch horizon/simulation."""
    n_steps: int
    total_cost: float
    cost_shortage: float
    cost_curtail: float
    cost_degradation: float
    shortage_mwh: float
    curtailment_mwh: float
    wind_generation_mwh: float
    committed_mwh: float
    delivered_mwh: float
    bess_throughput_mwh: float
    equivalent_full_cycles: float
    violation_rate: float
    mean_soc: float
    step_results: List[DispatchStepResult] = field(default_factory=list)

    def to_summary_dict(self) -> Dict[str, float]:
        return {
            "total_cost": self.total_cost,
            "cost_shortage": self.cost_shortage,
            "cost_curtail": self.cost_curtail,
            "cost_degradation": self.cost_degradation,
            "shortage_mwh": self.shortage_mwh,
            "curtailment_mwh": self.curtailment_mwh,
            "wind_generation_mwh": self.wind_generation_mwh,
            "committed_mwh": self.committed_mwh,
            "delivered_mwh": self.delivered_mwh,
            "bess_throughput_mwh": self.bess_throughput_mwh,
            "equivalent_full_cycles": self.equivalent_full_cycles,
            "violation_rate": self.violation_rate,
            "mean_soc": self.mean_soc,
        }


class WindBESSRollingOptimizer:
    """Wind-BESS Rolling Dispatch Decision Optimizer.

    Implements:
    - Step-level physical dispatch with battery energy conservation
    - Multi-period deterministic Linear Programming (LP) optimization via HiGHS
    - Model Predictive Control (MPC) rolling horizon execution
    - Benchmark comparison against unbuffered wind generation
    """

    def __init__(self, config: Optional[BESSConfig] = None) -> None:
        self.config = config or BESSConfig()

    def dispatch_step_heuristic(
        self,
        p_wind: float,
        p_commit: float,
        current_energy_mwh: float,
        step: int = 0,
    ) -> DispatchStepResult:
        """Instantaneous physically constrained closed-loop dispatch step.

        Balances power at PCC to minimize shortage penalties and curtailment costs
        while respecting battery power and SoC constraints.
        """
        cfg = self.config
        p_wind = max(0.0, float(p_wind))
        p_commit = max(0.0, float(p_commit))
        dt = cfg.dt_hours

        e_min = cfg.soc_min * cfg.capacity_mwh
        e_max = cfg.soc_max * cfg.capacity_mwh
        current_energy_mwh = min(max(current_energy_mwh, e_min), e_max)
        soc_start = current_energy_mwh / cfg.capacity_mwh

        # Determine generation vs commitment mismatch
        diff = p_wind - p_commit

        p_charge = 0.0
        p_discharge = 0.0
        p_curtail = 0.0
        p_shortage = 0.0

        if diff > 1e-9:
            # Wind surplus: attempt to charge BESS to prevent curtailment
            # Energy headroom available:
            e_headroom = max(0.0, e_max - current_energy_mwh)
            p_charge_max_energy = e_headroom / (cfg.eta_charge * dt) if dt > 0 else 0.0
            p_charge_max = min(cfg.power_rating_mw, p_charge_max_energy)

            # Check economic viability: charging throughput cost vs curtailment penalty
            if cfg.degradation_cost_per_mwh <= cfg.curtailment_penalty_per_mwh:
                p_charge = min(diff, p_charge_max)
            else:
                # If battery degradation cost is higher than curtailment penalty, prefer curtailing
                p_charge = 0.0

            p_curtail = diff - p_charge

        elif diff < -1e-9:
            # Wind deficit: attempt to discharge BESS to avoid shortage penalty
            deficit = -diff
            # Energy available for discharge:
            e_available = max(0.0, current_energy_mwh - e_min)
            p_discharge_max_energy = (e_available * cfg.eta_discharge) / dt if dt > 0 else 0.0
            p_discharge_max = min(cfg.power_rating_mw, p_discharge_max_energy)

            # Check economic viability: discharging degradation cost vs shortage penalty
            if cfg.degradation_cost_per_mwh <= cfg.shortage_penalty_per_mwh:
                p_discharge = min(deficit, p_discharge_max)
            else:
                p_discharge = 0.0

            p_shortage = deficit - p_discharge
        else:
            # Exactly balanced
            pass

        # Update battery energy state
        next_energy_mwh = (
            current_energy_mwh
            + (cfg.eta_charge * p_charge - p_discharge / cfg.eta_discharge) * dt
        )
        # Numerical guard against float drift
        next_energy_mwh = min(max(next_energy_mwh, e_min), e_max)
        soc_end = next_energy_mwh / cfg.capacity_mwh

        # Delivered power at PCC
        p_pcc = p_wind - p_curtail + p_discharge - p_charge

        # Calculate operational costs
        cost_shortage = cfg.shortage_penalty_per_mwh * p_shortage * dt
        cost_curtail = cfg.curtailment_penalty_per_mwh * p_curtail * dt
        cost_deg = cfg.degradation_cost_per_mwh * (p_charge + p_discharge) * dt
        total_cost = cost_shortage + cost_curtail + cost_deg

        return DispatchStepResult(
            step=step,
            p_wind=p_wind,
            p_commit=p_commit,
            p_charge=p_charge,
            p_discharge=p_discharge,
            p_curtail=p_curtail,
            p_shortage=p_shortage,
            p_pcc=p_pcc,
            soc_start=soc_start,
            soc_end=soc_end,
            energy_stored_mwh=next_energy_mwh,
            cost_shortage=cost_shortage,
            cost_curtail=cost_curtail,
            cost_degradation=cost_deg,
            total_cost=total_cost,
        )

    def solve_multi_period_lp(
        self,
        wind_forecast_mw: np.ndarray,
        commit_schedule_mw: np.ndarray,
        initial_energy_mwh: Optional[float] = None,
        target_final_soc: Optional[float] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Solves exact multi-period Linear Program over a lookahead horizon.

        Decision variables for each step k in 0..H-1:
        [P_ch[k], P_dis[k], P_curt[k], P_short[k], E[k+1]]

        Returns:
            p_charge: (H,)
            p_discharge: (H,)
            p_curtail: (H,)
            p_shortage: (H,)
            energy_trajectory: (H+1,)
        """
        cfg = self.config
        H = len(wind_forecast_mw)
        if H != len(commit_schedule_mw):
            raise ValueError(
                f"Horizon mismatch: wind has {H} steps, commit has {len(commit_schedule_mw)}"
            )

        if initial_energy_mwh is None:
            initial_energy_mwh = cfg.soc_initial * cfg.capacity_mwh

        e_min = cfg.soc_min * cfg.capacity_mwh
        e_max = cfg.soc_max * cfg.capacity_mwh
        initial_energy_mwh = min(max(initial_energy_mwh, e_min), e_max)
        dt = cfg.dt_hours

        # 5 variables per step: P_ch, P_dis, P_curt, P_short, E_next
        n_vars = 5 * H

        # Objective vector c:
        # Cost = sum_k ( c_deg*(P_ch + P_dis) + lambda_curt*P_curt + lambda_short*P_short ) * dt
        c = np.zeros(n_vars)
        for k in range(H):
            idx = 5 * k
            c[idx + 0] = cfg.degradation_cost_per_mwh * dt      # P_ch
            c[idx + 1] = cfg.degradation_cost_per_mwh * dt      # P_dis
            c[idx + 2] = cfg.curtailment_penalty_per_mwh * dt   # P_curt
            c[idx + 3] = cfg.shortage_penalty_per_mwh * dt      # P_short
            c[idx + 4] = 0.0                                    # E_next

        # Equality constraints: A_eq @ x == b_eq
        # Energy dynamics: E[k+1] - E[k] - eta_ch*dt*P_ch[k] + (dt/eta_dis)*P_dis[k] == 0
        A_eq_list = []
        b_eq_list = []
        for k in range(H):
            row = np.zeros(n_vars)
            idx = 5 * k
            row[idx + 0] = -cfg.eta_charge * dt
            row[idx + 1] = dt / cfg.eta_discharge
            row[idx + 4] = 1.0  # E[k+1]
            if k > 0:
                row[5 * (k - 1) + 4] = -1.0  # -E[k]
                b_val = 0.0
            else:
                b_val = initial_energy_mwh  # E[0] is fixed
            A_eq_list.append(row)
            b_eq_list.append(b_val)

        if target_final_soc is not None:
            # Target final SoC constraint: E[H] == target_final_soc * capacity
            row = np.zeros(n_vars)
            row[5 * (H - 1) + 4] = 1.0
            A_eq_list.append(row)
            b_eq_list.append(target_final_soc * cfg.capacity_mwh)

        # Power balance equality constraint:
        # P_pcc[k] = P_wind[k] - P_curt[k] + P_dis[k] - P_ch[k] == P_commit[k] - P_short[k]
        # => P_ch[k] - P_dis[k] + P_curt[k] - P_short[k] == P_wind[k] - P_commit[k]
        for k in range(H):
            row = np.zeros(n_vars)
            idx = 5 * k
            row[idx + 0] = 1.0   # +P_ch
            row[idx + 1] = -1.0  # -P_dis
            row[idx + 2] = 1.0   # +P_curt
            row[idx + 3] = -1.0  # -P_short
            A_eq_list.append(row)
            b_eq_list.append(float(wind_forecast_mw[k] - commit_schedule_mw[k]))

        A_eq = np.array(A_eq_list)
        b_eq = np.array(b_eq_list)

        # Variable bounds: (lb, ub)
        bounds = []
        for k in range(H):
            bounds.append((0.0, cfg.power_rating_mw))               # P_ch
            bounds.append((0.0, cfg.power_rating_mw))               # P_dis
            bounds.append((0.0, max(0.0, float(wind_forecast_mw[k])))) # P_curt <= P_wind
            bounds.append((0.0, None))                              # P_short
            bounds.append((e_min, e_max))                           # E_next

        res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
        if not res.success:
            # Fallback to step heuristic if LP solver reports infeasibility or numerical warning
            p_ch = np.zeros(H)
            p_dis = np.zeros(H)
            p_curt = np.zeros(H)
            p_short = np.zeros(H)
            e_traj = np.zeros(H + 1)
            e_traj[0] = initial_energy_mwh
            curr_e = initial_energy_mwh
            for k in range(H):
                st = self.dispatch_step_heuristic(wind_forecast_mw[k], commit_schedule_mw[k], curr_e, step=k)
                p_ch[k] = st.p_charge
                p_dis[k] = st.p_discharge
                p_curt[k] = st.p_curtail
                p_short[k] = st.p_shortage
                curr_e = st.energy_stored_mwh
                e_traj[k + 1] = curr_e
            return p_ch, p_dis, p_curt, p_short, e_traj

        sol = res.x
        p_charge = np.array([sol[5 * k + 0] for k in range(H)])
        p_discharge = np.array([sol[5 * k + 1] for k in range(H)])
        p_curtail = np.array([sol[5 * k + 2] for k in range(H)])
        p_shortage = np.array([sol[5 * k + 3] for k in range(H)])
        energy_traj = np.zeros(H + 1)
        energy_traj[0] = initial_energy_mwh
        for k in range(H):
            energy_traj[k + 1] = sol[5 * k + 4]

        return p_charge, p_discharge, p_curtail, p_shortage, energy_traj

    def simulate_rolling_mpc(
        self,
        wind_actual_mw: np.ndarray,
        wind_forecast_mw: np.ndarray,
        commit_schedule_mw: np.ndarray,
        lookahead_steps: int = 6,
    ) -> DispatchTrajectoryResult:
        """Runs a receding-horizon Model Predictive Control (MPC) dispatch simulation.

        At each step k:
        1. Solves multi-period LP over lookahead window [k, min(k + lookahead_steps, N)]
           using forecasted wind and committed schedule, starting from current BESS energy.
        2. Applies first-step planned BESS dispatch against realized wind_actual_mw[k].
        3. Enforces real-time power balancing at PCC:
           - Over-delivery above commitment is curtailed.
           - Under-delivery below commitment constitutes shortage.
        4. Updates physical battery SoC and operational cost accounting.
        5. Rolls forward to step k + 1.

        Args:
            wind_actual_mw: Realized wind generation trajectory (MW).
            wind_forecast_mw: Forecasted wind generation trajectory (MW).
            commit_schedule_mw: Contracted commitment schedule (MW).
            lookahead_steps: MPC lookahead horizon in steps (default: 6 steps = 1 hr).

        Returns:
            DispatchTrajectoryResult with complete closed-loop performance metrics.
        """
        cfg = self.config
        N = len(wind_actual_mw)
        if N != len(commit_schedule_mw) or N != len(wind_forecast_mw):
            raise ValueError(
                f"Array length mismatch: wind_actual={N}, forecast={len(wind_forecast_mw)}, commit={len(commit_schedule_mw)}"
            )

        step_results: List[DispatchStepResult] = []
        current_energy = cfg.soc_initial * cfg.capacity_mwh
        e_min = cfg.soc_min * cfg.capacity_mwh
        e_max = cfg.soc_max * cfg.capacity_mwh
        dt = cfg.dt_hours

        for k in range(N):
            w_end = min(k + lookahead_steps, N)
            H_step = w_end - k

            # Real-time state feedback: at step k, current realized generation is observed at PCC bus.
            # Lookahead steps 1..H-1 utilize the receding horizon forecast.
            w_fc_receding = np.empty(H_step, dtype=np.float64)
            w_fc_receding[0] = max(0.0, float(wind_actual_mw[k]))
            if H_step > 1:
                w_fc_receding[1:] = wind_forecast_mw[k + 1:w_end]

            c_fc = commit_schedule_mw[k:w_end]

            p_ch_plan, p_dis_plan, _, _, _ = self.solve_multi_period_lp(
                w_fc_receding, c_fc, initial_energy_mwh=current_energy
            )

            ch_exec = float(p_ch_plan[0])
            dis_exec = float(p_dis_plan[0])

            w_act = max(0.0, float(wind_actual_mw[k]))
            c_act = max(0.0, float(commit_schedule_mw[k]))
            soc_start = current_energy / cfg.capacity_mwh

            max_ch_e = max(0.0, (e_max - current_energy) / (cfg.eta_charge * dt)) if dt > 0 else 0.0
            max_dis_e = max(0.0, (current_energy - e_min) * cfg.eta_discharge / dt) if dt > 0 else 0.0
            ch_exec = min(ch_exec, max_ch_e, cfg.power_rating_mw)
            dis_exec = min(dis_exec, max_dis_e, cfg.power_rating_mw)

            next_energy = current_energy + (cfg.eta_charge * ch_exec - dis_exec / cfg.eta_discharge) * dt
            next_energy = min(max(next_energy, e_min), e_max)
            soc_end = next_energy / cfg.capacity_mwh

            p_raw = w_act + dis_exec - ch_exec
            diff = p_raw - c_act

            if diff >= 0:
                p_curt = diff
                p_short = 0.0
                p_pcc = c_act
            else:
                p_curt = 0.0
                p_short = -diff
                p_pcc = p_raw

            c_short = cfg.shortage_penalty_per_mwh * p_short * dt
            c_curt = cfg.curtailment_penalty_per_mwh * p_curt * dt
            c_deg = cfg.degradation_cost_per_mwh * (ch_exec + dis_exec) * dt
            tot_step_cost = c_short + c_curt + c_deg

            step_res = DispatchStepResult(
                step=k,
                p_wind=w_act,
                p_commit=c_act,
                p_charge=ch_exec,
                p_discharge=dis_exec,
                p_curtail=p_curt,
                p_shortage=p_short,
                p_pcc=p_pcc,
                soc_start=soc_start,
                soc_end=soc_end,
                energy_stored_mwh=next_energy,
                cost_shortage=c_short,
                cost_curtail=c_curt,
                cost_degradation=c_deg,
                total_cost=tot_step_cost,
            )
            step_results.append(step_res)
            current_energy = next_energy

        # Aggregate metrics
        tot_cost = sum(r.total_cost for r in step_results)
        tot_cost_shortage = sum(r.cost_shortage for r in step_results)
        tot_cost_curtail = sum(r.cost_curtail for r in step_results)
        tot_cost_deg = sum(r.cost_degradation for r in step_results)

        tot_shortage_mwh = sum(r.p_shortage for r in step_results) * dt
        tot_curtail_mwh = sum(r.p_curtail for r in step_results) * dt
        tot_wind_mwh = sum(r.p_wind for r in step_results) * dt
        tot_commit_mwh = sum(r.p_commit for r in step_results) * dt
        tot_delivered_mwh = sum(r.p_pcc for r in step_results) * dt

        throughput_mwh = sum(r.p_charge + r.p_discharge for r in step_results) * dt
        efc = throughput_mwh / (2.0 * cfg.capacity_mwh)
        violations = sum(1 for r in step_results if r.p_shortage > 1e-4)
        violation_rate = violations / max(1, N)
        mean_soc = float(np.mean([r.soc_end for r in step_results]))

        return DispatchTrajectoryResult(
            n_steps=N,
            total_cost=tot_cost,
            cost_shortage=tot_cost_shortage,
            cost_curtail=tot_cost_curtail,
            cost_degradation=tot_cost_deg,
            shortage_mwh=tot_shortage_mwh,
            curtailment_mwh=tot_curtail_mwh,
            wind_generation_mwh=tot_wind_mwh,
            committed_mwh=tot_commit_mwh,
            delivered_mwh=tot_delivered_mwh,
            bess_throughput_mwh=throughput_mwh,
            equivalent_full_cycles=efc,
            violation_rate=violation_rate,
            mean_soc=mean_soc,
            step_results=step_results,
        )

    def simulate_trajectory(
        self,
        wind_actual_mw: np.ndarray,
        commit_schedule_mw: np.ndarray,
        mode: str = "heuristic",
    ) -> DispatchTrajectoryResult:
        """Runs a complete forward simulation of the wind-BESS system.

        Args:
            wind_actual_mw: Array of realized wind power (MW)
            commit_schedule_mw: Array of contracted committed power (MW)
            mode: 'heuristic' for fast closed-loop rule, 'lp' for full horizon optimal, or 'mpc' for rolling horizon MPC

        Returns:
            DispatchTrajectoryResult with comprehensive IEEE TSTE metrics.
        """
        cfg = self.config
        N = len(wind_actual_mw)
        if N != len(commit_schedule_mw):
            raise ValueError(f"Length mismatch: {N} vs {len(commit_schedule_mw)}")

        if mode == "mpc":
            return self.simulate_rolling_mpc(wind_actual_mw, wind_actual_mw, commit_schedule_mw)

        step_results: List[DispatchStepResult] = []
        current_energy = cfg.soc_initial * cfg.capacity_mwh

        if mode == "lp":
            p_ch, p_dis, p_curt, p_short, e_traj = self.solve_multi_period_lp(
                wind_actual_mw, commit_schedule_mw, initial_energy_mwh=current_energy
            )
            for k in range(N):
                soc_start = e_traj[k] / cfg.capacity_mwh
                soc_end = e_traj[k + 1] / cfg.capacity_mwh
                p_pcc = wind_actual_mw[k] - p_curt[k] + p_dis[k] - p_ch[k]
                c_short = cfg.shortage_penalty_per_mwh * p_short[k] * cfg.dt_hours
                c_curt = cfg.curtailment_penalty_per_mwh * p_curt[k] * cfg.dt_hours
                c_deg = cfg.degradation_cost_per_mwh * (p_ch[k] + p_dis[k]) * cfg.dt_hours
                step_res = DispatchStepResult(
                    step=k,
                    p_wind=float(wind_actual_mw[k]),
                    p_commit=float(commit_schedule_mw[k]),
                    p_charge=float(p_ch[k]),
                    p_discharge=float(p_dis[k]),
                    p_curtail=float(p_curt[k]),
                    p_shortage=float(p_short[k]),
                    p_pcc=float(p_pcc),
                    soc_start=float(soc_start),
                    soc_end=float(soc_end),
                    energy_stored_mwh=float(e_traj[k + 1]),
                    cost_shortage=float(c_short),
                    cost_curtail=float(c_curt),
                    cost_degradation=float(c_deg),
                    total_cost=float(c_short + c_curt + c_deg),
                )
                step_results.append(step_res)
        else:
            for k in range(N):
                step_res = self.dispatch_step_heuristic(
                    wind_actual_mw[k], commit_schedule_mw[k], current_energy, step=k
                )
                current_energy = step_res.energy_stored_mwh
                step_results.append(step_res)

        # Aggregate metrics
        dt = cfg.dt_hours
        tot_cost = sum(r.total_cost for r in step_results)
        tot_cost_shortage = sum(r.cost_shortage for r in step_results)
        tot_cost_curtail = sum(r.cost_curtail for r in step_results)
        tot_cost_deg = sum(r.cost_degradation for r in step_results)

        tot_shortage_mwh = sum(r.p_shortage for r in step_results) * dt
        tot_curtail_mwh = sum(r.p_curtail for r in step_results) * dt
        tot_wind_mwh = sum(r.p_wind for r in step_results) * dt
        tot_commit_mwh = sum(r.p_commit for r in step_results) * dt
        tot_delivered_mwh = sum(r.p_pcc for r in step_results) * dt

        throughput_mwh = sum(r.p_charge + r.p_discharge for r in step_results) * dt
        efc = throughput_mwh / (2.0 * cfg.capacity_mwh)
        violations = sum(1 for r in step_results if r.p_shortage > 1e-4)
        violation_rate = violations / max(1, N)
        mean_soc = float(np.mean([r.soc_end for r in step_results]))

        return DispatchTrajectoryResult(
            n_steps=N,
            total_cost=tot_cost,
            cost_shortage=tot_cost_shortage,
            cost_curtail=tot_cost_curtail,
            cost_degradation=tot_cost_deg,
            shortage_mwh=tot_shortage_mwh,
            curtailment_mwh=tot_curtail_mwh,
            wind_generation_mwh=tot_wind_mwh,
            committed_mwh=tot_commit_mwh,
            delivered_mwh=tot_delivered_mwh,
            bess_throughput_mwh=throughput_mwh,
            equivalent_full_cycles=efc,
            violation_rate=violation_rate,
            mean_soc=mean_soc,
            step_results=step_results,
        )

    def benchmark_against_unbuffered_wind(
        self,
        wind_actual_mw: np.ndarray,
        commit_schedule_mw: np.ndarray,
    ) -> Dict[str, Any]:
        """Compares BESS dispatch against Standalone Unbuffered Wind (legacy toy baseline).

        Returns comparative economic value metrics for IEEE TSTE reporting:
        - Avoided imbalance shortage
        - Avoided wind curtailment
        - Net operational cost savings ($ and %)
        - Levelized BESS utilization
        """
        cfg = self.config
        dt = cfg.dt_hours

        # 1. Unbuffered Standalone Wind (No BESS)
        diff = wind_actual_mw - commit_schedule_mw
        unbuffered_shortage_mw = np.maximum(-diff, 0.0)
        unbuffered_curtail_mw = np.maximum(diff, 0.0)

        unbuf_cost_short = float(np.sum(unbuffered_shortage_mw) * cfg.shortage_penalty_per_mwh * dt)
        unbuf_cost_curt = float(np.sum(unbuffered_curtail_mw) * cfg.curtailment_penalty_per_mwh * dt)
        unbuf_total_cost = unbuf_cost_short + unbuf_cost_curt
        unbuf_violation_rate = float(np.mean(unbuffered_shortage_mw > 1e-4))

        # 2. Wind + BESS Dispatch
        bess_traj = self.simulate_trajectory(wind_actual_mw, commit_schedule_mw, mode="heuristic")

        # Savings calculations
        cost_savings = unbuf_total_cost - bess_traj.total_cost
        cost_reduction_pct = (cost_savings / unbuf_total_cost * 100.0) if unbuf_total_cost > 0 else 0.0
        avoided_shortage_mwh = (float(np.sum(unbuffered_shortage_mw) * dt)) - bess_traj.shortage_mwh
        avoided_curtail_mwh = (float(np.sum(unbuffered_curtail_mw) * dt)) - bess_traj.curtailment_mwh

        return {
            "unbuffered_wind": {
                "total_cost": unbuf_total_cost,
                "cost_shortage": unbuf_cost_short,
                "cost_curtail": unbuf_cost_curt,
                "shortage_mwh": float(np.sum(unbuffered_shortage_mw) * dt),
                "curtailment_mwh": float(np.sum(unbuffered_curtail_mw) * dt),
                "violation_rate": unbuf_violation_rate,
            },
            "wind_bess": bess_traj.to_summary_dict(),
            "comparison": {
                "cost_savings_dollars": cost_savings,
                "cost_reduction_pct": cost_reduction_pct,
                "avoided_shortage_mwh": avoided_shortage_mwh,
                "avoided_curtailment_mwh": avoided_curtail_mwh,
                "violation_rate_reduction": unbuf_violation_rate - bess_traj.violation_rate,
            },
        }
