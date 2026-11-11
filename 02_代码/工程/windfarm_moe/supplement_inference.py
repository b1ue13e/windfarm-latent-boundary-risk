"""Fixed-ledger, endpoint-local inference for the retrospective V3 supplement.

This module consumes sealed daily accounting only. It never fits a policy,
changes the comparison population, or uses qualification to select a column.
"""
from __future__ import annotations

from dataclasses import dataclass
import csv
import hashlib
import json
from repo_paths import Path, repository_root
from typing import Any

import numpy as np

from .risk_frontier import shared_block_draws
from .supplement_endpoint_adapter import (
    EndpointCoordinate, adapt_endpoint_family, pooled_mean,
)


FAMILY_COUNTS = {"H_P": 40, "E_P": 94, "E_R": 128, "E_G": 32}
SPANS = (3, 1, 7)
SEEDS = (201, 202, 203, 204, 205)


def _save(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class Estimate:
    point: float | None
    draws: np.ndarray
    population: np.ndarray
    draw_population: np.ndarray
    failure: str | None = None


def _dependencies(values: list[Estimate]) -> tuple[np.ndarray, np.ndarray]:
    """Retain all distinct denominator dependencies, including zero columns."""
    pop = np.concatenate([v.population for v in values])
    draw_pop = np.column_stack([v.draw_population for v in values])
    retained: list[int] = []
    for i in range(len(pop)):
        if not any(pop[i] == pop[j] and np.array_equal(draw_pop[:, i], draw_pop[:, j], equal_nan=True)
                   for j in retained):
            retained.append(i)
    return pop[retained], draw_pop[:, retained]


def _combine(values: list[Estimate], coefficients: list[float]) -> Estimate:
    pop, draw_pop = _dependencies(values)
    failure = next((v.failure for v in values if v.failure), None)
    point = (None if any(v.point is None for v in values) else
             float(sum(c * v.point for c, v in zip(coefficients, values))))
    draws = sum(c * v.draws for c, v in zip(coefficients, values))
    return Estimate(point, draws, pop, draw_pop, failure)


class DailyReader:
    """Read every predefined fit without a qualification field or selector."""

    def __init__(self, base: Path, ledger: list[dict], calendars: dict[str, np.ndarray],
                 weights: dict[str, np.ndarray]):
        expected = [(e, s) for e in ("HGB", "MLP") for s in SEEDS]
        if [(r["estimator"], r["seed"]) for r in ledger] != expected:
            raise ValueError("All ten ordered fit identities are required")
        self.base, self.ledger = Path(base), ledger
        self.calendars, self.weights = calendars, weights
        self._archives: dict[int, dict[str, np.ndarray]] = {}
        self._estimates: dict[tuple, Estimate] = {}

    def _failure(self, family: str, reason: str) -> Estimate:
        n = len(self.weights["H_P" if family == "H_P" else "evaluation"])
        return Estimate(None, np.full(n, np.nan), np.array([np.nan]),
                        np.full((n, 1), np.nan), reason)

    @staticmethod
    def worker(estimator: str, seed: int) -> int:
        return (0 if estimator == "HGB" else 5) + SEEDS.index(seed)

    def get(self, family: str, estimator: str, seed: int | None, arm: str,
            metric: str, axis: str = "", group: str = "") -> Estimate:
        key = (family, estimator, seed, arm, metric, axis, group)
        if key in self._estimates:
            return self._estimates[key]
        if seed is None:
            fits = [self.get(family, estimator, s, arm, metric, axis, group) for s in SEEDS]
            # Missing fits remain dependencies; there is never a four-fit mean.
            result = _combine(fits, [.2] * 5)
        else:
            result = self._single(family, estimator, seed, arm, metric, axis, group)
        self._estimates[key] = result
        return result

    def _single(self, family: str, estimator: str, seed: int, arm: str,
                metric: str, axis: str, group: str) -> Estimate:
        worker = self.worker(estimator, seed)
        calendar_key = "H_P" if family == "H_P" else "evaluation"
        if arm == "Praw":
            phase = "selection" if family == "H_P" else "evaluation"
            path = self.base / "fits" / str(worker) / f"{phase}_blocks.npz"
            row = self.ledger[worker]
            phase_status = row.get("history_compute_status") if phase == "selection" else row.get("compute_status")
            if phase_status == "COMPUTATION_FAILED" or not path.is_file():
                return self._failure(family, f"{row.get('identity_id', worker)}:{phase}:"
                                     + str(row.get(phase + "_failure_reason", row.get("failure_reason"))
                                           or "COMPUTATIONAL_DEPENDENCY_UNAVAILABLE"))
            with np.load(path, allow_pickle=False) as archive:
                block = {k: archive[k] for k in (metric, "N", "days")}
        else:
            if worker not in self._archives:
                path = self.base / "accounting" / str(worker) / "daily_totals.npz"
                if not path.is_file():
                    return self._failure(family, f"OLD_ACCOUNTING_UNAVAILABLE:{worker}")
                with np.load(path, allow_pickle=False) as archive:
                    self._archives[worker] = {k: archive[k] for k in archive.files}
            archive = self._archives[worker]
            prefix = f"{family}|{arm}" + (f"|{axis}|{group}" if family == "E_R" else "")
            try:
                block = {k: archive[prefix + "|" + k] for k in (metric, "N", "days")}
            except KeyError:
                return self._failure(family, f"OLD_ENDPOINT_UNAVAILABLE:{prefix}:{metric}")
        if not np.array_equal(block["days"], self.calendars[calendar_key]):
            return self._failure(family, "SOURCE_CONTRACT_INVALID:calendar_changed")
        try:
            result = pooled_mean(block[metric], block["N"], self.weights[calendar_key])
        except ValueError as exc:
            return self._failure(family, "SOURCE_CONTRACT_INVALID:" + str(exc))
        return Estimate(result.point, result.draws, np.array([result.population_denominator]),
                        result.draw_population_denominators[:, None])


def _coordinate(row: dict[str, str], reader: DailyReader, cstar: float) -> EndpointCoordinate:
    family, estimator, metric = row["family"], row["estimator"], row["metric"]
    seed = int(row["fit_seed"]) if row["fit_seed"] else None
    domain, ref, draw_ref = "SIGNED_REAL", 1., None
    if metric in ("absolute_V", "absolute_V_G"):
        value = reader.get(family, estimator, seed, row["arm"], "V")
        domain = "RISK_0_1"
    elif metric == "gap_U":
        value = reader.get(family, estimator, None, row["arm"], "gap_U")
        domain = "NONNEGATIVE"
    else:
        added, reference = row["comparison"].split("-minus-")
        field = "C" if metric == "D_C" else "U" if metric == "H_U" else metric.rsplit("_", 1)[-1]
        if metric.startswith("interaction_"):
            high = [reader.get(family, estimator, None, arm, field, "wind_proxy", "at_or_above_10p5")
                    for arm in (added, reference)]
            low = [reader.get(family, estimator, None, arm, field, "wind_proxy", "below_10p5")
                   for arm in (added, reference)]
            value = _combine(high + low, [1., -1., -1., 1.])
        else:
            pair = [reader.get(family, estimator, seed, arm, field, row["axis"], row["group"])
                    for arm in (added, reference)]
            value = _combine(pair, [1., -1.])
            if metric == "D_C":
                baseline = pair[1]
                ref = np.nan if baseline.point is None else baseline.point
                draw_ref = baseline.draws[:, None]
                divided = np.full_like(value.draws, np.nan)
                np.divide(value.draws, baseline.draws, out=divided, where=baseline.draws > 0)
                value.point = None if value.point is None or not ref > 0 else value.point / ref
                value.draws = divided
            elif metric == "H_U":
                ref = cstar
                value.point = None if value.point is None else 10. * value.point / cstar
                value.draws = 10. * value.draws / cstar
    metadata = {k: row[k] for k in ("family", "stage", "estimator", "fit_seed", "arm", "comparison",
                                   "axis", "group", "metric", "scale", "unit", "denominator",
                                   "population", "label_rule_or_scope")}
    metadata["block_span"] = int(row["block_span"])
    if family == "E_G":
        deficits = [reader.get(family, estimator, None, arm, "U") for arm in ("OP6", "OPZ6")]
        metadata["observation_annotations"] = (
            ["OBSERVED_BOTH_U_ZERO"] if all(v.failure is None and v.point == 0 and
                                            np.isfinite(v.population).all() and np.all(v.population > 0)
                                            for v in deficits) else [])
    return EndpointCoordinate(
        row["coordinate_id"], value.point, value.draws, value.population, value.draw_population,
        domain=domain, reference_denominator=ref, draw_reference_denominators=draw_ref,
        computation_failure=value.failure,
        metadata=metadata,
    )


def _read_coordinates(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        all_rows = list(csv.DictReader(stream))
    rows = [r for r in all_rows if r["default_scope"] == "True"]
    if len({r["coordinate_id"] for r in rows}) != 882:
        raise ValueError("The complete 882-coordinate default ledger is required")
    for family, count in FAMILY_COUNTS.items():
        for span in SPANS:
            if sum(r["family"] == family and int(r["block_span"]) == span for r in rows) != count:
                raise ValueError("Comparison-family size differs from the frozen V3 ledger")
    if any(r["evaluation_depends_on_qualification"] != "False" or
           r["inferential_exact_predeclared"] != "False" for r in rows):
        raise ValueError("No qualification filter or exact inferential coordinate is permitted")
    return rows


def _calendar(base: Path, family: str) -> np.ndarray:
    with np.load(base / "accounting/0/daily_totals.npz", allow_pickle=False) as archive:
        days = np.asarray(archive[f"{family}|O6|days"], dtype=np.int64)
    if days.ndim != 1 or len(days) < 7 or np.any(np.diff(days) != 1):
        raise ValueError("The complete contiguous natural-day calendar is required")
    return days


def _write_family(output: Path, result: dict, coords: list[EndpointCoordinate],
                  weights: np.ndarray, weights_hash: str, days: np.ndarray) -> str:
    """Keep large numeric arrays losslessly in NPZ, with explicit JSON links."""
    family, span = result["family_id"], result["span"]
    name = f"{family}_span{span}"
    numeric: dict[str, np.ndarray] = {
        "draw_values": np.column_stack([c.draws for c in coords]),
        "coordinate_ids": np.asarray(result["planned_coordinate_ids"]),
        "draw_ids": np.arange(result["draw_count"], dtype=np.int64),
        "day_weights": weights, "natural_days": days,
    }
    for i, endpoint in enumerate(result["coordinates"]):
        endpoint.pop("draw_values")
        for field in ("draw_population_denominators", "draw_reference_denominators", "draw_denominator_valid"):
            numeric[f"c{i}__{field}"] = np.asarray(endpoint.pop(field), dtype=bool if field.endswith("valid") else float)
        endpoint["draw_artifact"] = {
            "path": f"draws/{name}.npz", "draw_values_column": i,
            "draw_population_denominators_key": f"c{i}__draw_population_denominators",
            "draw_reference_denominators_key": f"c{i}__draw_reference_denominators",
            "draw_denominator_valid_key": f"c{i}__draw_denominator_valid",
        }
    artifact = output / "draws" / (name + ".npz")
    np.savez_compressed(artifact, **numeric)
    result.update(shared_draw_schedule_sha256=weights_hash,
                  draw_artifact={"path": f"draws/{name}.npz", "sha256": _sha(artifact)},
                  natural_days=days.tolist(), fits_resampled=False, turbines_resampled=False)
    path = output / "families" / (name + ".json")
    _save(path, result)
    return f"families/{name}.json"


def _new_head_labels(families: list[dict], ledger: list[dict], cap: float) -> dict:
    lookup = {(f["family_id"], c["estimator"], c["fit_seed"]): c
              for f in families if f["span"] == 3 and f["family_id"] in ("H_P", "E_P")
              for c in f["coordinates"] if c["arm"] == "Praw"}
    result = []
    for identity in ledger:
        labels = {}
        for family, phase in (("H_P", "history"), ("E_P", "evaluation")):
            endpoint = lookup[(family, identity["estimator"], str(identity["seed"]))]
            if endpoint["interval_status"] == "NOT_AVAILABLE_COMPUTATION":
                label = "UNAVAILABLE_COMPUTATION"
            elif endpoint["interval_status"] != "ESTIMATED_APPROX":
                label = "UNDETERMINED_INTERVAL"
            else:
                label = "QUALIFIED" if endpoint["upper"] <= cap else "NOT_QUALIFIED_BY_BOUND"
            labels[phase] = {"label": label, "coordinate_id": endpoint["coordinate_id"],
                             "upper": endpoint["upper"], "interval_status": endpoint["interval_status"]}
        result.append({"identity_id": identity["identity_id"], "estimator": identity["estimator"],
                       "seed": identity["seed"], **labels})
    summaries = {}
    for estimator in ("HGB", "MLP"):
        selected = [r for r in result if r["estimator"] == estimator]
        tags = [r[p]["label"] for r in selected for p in ("history", "evaluation")]
        summaries[estimator] = {
            "all_five_history_qualified": all(r["history"]["label"] == "QUALIFIED" for r in selected),
            "all_five_evaluation_qualified": all(r["evaluation"]["label"] == "QUALIFIED" for r in selected),
            "any_bound_failure": "NOT_QUALIFIED_BY_BOUND" in tags,
            "any_undetermined": "UNDETERMINED_INTERVAL" in tags,
            "any_computation_failure": "UNAVAILABLE_COMPUTATION" in tags,
        }
    return {"generated_after_output_seal": True, "labels_control_evaluation": False,
            "original_qualification_labels_preserved": True, "original_ABC_rejudged": False,
            "risk_cap": cap, "primary_span": 3, "heads": result, "estimator_summary": summaries}


def _assemble(base: Path, output: Path, coordinates: Path, rules: dict,
              ledger: list[dict], *, n_boot: int, strict_calendar: bool) -> None:
    """Internal assembly; synthetic tests may supply fewer draws."""
    rows = _read_coordinates(coordinates)
    calendars = {"H_P": _calendar(base, "H_P"), "evaluation": _calendar(base, "E_P")}
    if strict_calendar:
        for key, stage in (("H_P", "historical"), ("evaluation", "evaluation")):
            low, high = rules["stages"][stage]
            expected = np.arange(low // 144, (high - 1) // 144 + 1)
            if not np.array_equal(calendars[key], expected):
                raise ValueError("Original issue calendar cannot be compressed or changed")
    for name in ("families", "draws"):
        (output / name).mkdir(exist_ok=False)
    completed, links = [], []
    for span in SPANS:
        schedules = {k: shared_block_draws(len(days), n_boot, span, 20261030)
                     for k, days in calendars.items()}
        reader = DailyReader(base, ledger, calendars, {k: v[0] for k, v in schedules.items()})
        for family in FAMILY_COUNTS:
            selected = [r for r in rows if r["family"] == family and int(r["block_span"]) == span]
            coords = [_coordinate(r, reader, rules["immutable"]["Cstar"]) for r in selected]
            result = adapt_endpoint_family(coords, family_id=family, span=span, alpha=.05)
            key = "H_P" if family == "H_P" else "evaluation"
            links.append(_write_family(output, result, coords, schedules[key][0], schedules[key][1], calendars[key]))
            completed.append(result)
    _save(output / "families.json", {
        "status": "COMPLETED_APPROXIMATE_FIXED_FIT_SUPPLEMENT", "family_artifacts": links,
        "planned_coordinates": 882, "n_boot_per_coordinate": n_boot, "seed": 20261030,
        "primary_span": 3, "sensitivity_spans": [1, 7], "alpha_per_family": .05,
        "joint_across_families_or_spans": False, "optional_budget_active": False,
        "qualification_used_for_evaluation_selection": False,
    })
    # Every interval, coordinate identity and draw artifact is now on disk.
    sealed = output / "inference_seal.json"
    _save(sealed, {"families_index_sha256": _sha(output / "families.json"),
                   "families": {link: _sha(output / link) for link in links},
                   "draw_artifacts": {f["draw_artifact"]["path"]: f["draw_artifact"]["sha256"] for f in completed},
                   "labels_generated": False, "all_882_slots_retained": True})
    labels = _new_head_labels(completed, ledger, rules["immutable"]["risk_cap"])
    labels["inference_seal_sha256"] = _sha(sealed)
    _save(output / "labels.json", labels)


def assemble_inference(base: Path, output: Path, coordinates: Path,
                       rules: dict, ledger: list[dict]) -> None:
    """Consume sealed fixed outputs with the exact frozen V3 inference settings."""
    inference = rules["inference"]
    if (rules["version"] != "V3" or inference["n_boot"] != 20000 or
            inference["bootstrap_seed"] != 20261030 or inference["alpha_per_family"] != .05 or
            inference["primary_span"] != 3 or inference["sensitivity_spans"] != [1, 7] or
            rules["immutable"]["Cstar"] != 40.04664774157611 or
            rules["immutable"]["risk_cap"] != .1):
        raise ValueError("The frozen inference settings and thresholds cannot be changed")
    if not (output / "sealed_evaluation_ledger.json").is_file():
        raise ValueError("Evaluation outputs must be sealed before any inference or labels")
    sealed_ledger = json.loads((output / "sealed_evaluation_ledger.json").read_text())
    if sealed_ledger != ledger:
        raise ValueError("Evaluation identity ledger differs from the sealed artifact")
    _assemble(Path(base), Path(output), Path(coordinates), rules, ledger,
              n_boot=20000, strict_calendar=True)
