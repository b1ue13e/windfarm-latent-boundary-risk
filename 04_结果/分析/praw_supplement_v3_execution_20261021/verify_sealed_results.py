"""Reconcile sealed V3 values using stored daily totals and stored draw weights.

No random generator, policy learner, resampler or production inference helper is
imported. The script only verifies existing values and writes a separate report.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits


HERE = Path(__file__).resolve().parent
BASE = HERE / "metis_results" / "results"
INFER = BASE / "infer"
ABS_TOL, REL_TOL = 1e-8, 1e-10  # Existing float64 accounting tolerance only.
CSTAR = 40.04664774157611


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def load_npz(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


class Reconciler:
    def __init__(self):
        self.failures = []
        self.max_errors = {}
        self.checks = Counter()
        self.inputs = {}
        self.accounting = {}
        self.new_blocks = {}
        self.cache = {}
        for worker in range(10):
            path = BASE / "accounting" / str(worker) / "daily_totals.npz"
            self.track(path)
            self.accounting[worker] = load_npz(path)
            for phase in ("selection", "evaluation"):
                path = BASE / "fits" / str(worker) / f"{phase}_blocks.npz"
                if path.exists():
                    self.track(path)
                    self.new_blocks[worker, phase] = load_npz(path)

    def track(self, path):
        self.inputs[str(Path(path).relative_to(HERE))] = sha(path)

    def flag(self, condition, name, detail=None):
        self.checks[name] += 1
        if not condition:
            self.failures.append({"check": name, "detail": detail})

    def close(self, expected, observed, name, coordinate):
        a, b = np.asarray(expected, dtype=float), np.asarray(observed, dtype=float)
        if a.shape != b.shape:
            self.flag(False, name, {"id": coordinate, "expected_shape": list(a.shape), "observed_shape": list(b.shape)})
            return
        finite_a, finite_b = np.isfinite(a), np.isfinite(b)
        mask_match = np.array_equal(finite_a, finite_b)
        both = finite_a & finite_b
        delta = np.abs(a[both] - b[both])
        maximum = float(delta.max()) if delta.size else 0.
        self.max_errors[name] = max(maximum, self.max_errors.get(name, 0.))
        ok = mask_match and bool(np.all(delta <= ABS_TOL + REL_TOL * np.abs(a[both])))
        self.flag(ok, name, None if ok else {"id": coordinate, "max_absolute_error": maximum,
                                             "finite_mask_equal": mask_match})

    def pooled(self, endpoint, arm, field, weights, days, *, seed=None, group=None):
        family, estimator = endpoint["family_id"], endpoint["estimator"]
        selected_seed = endpoint["fit_seed"] if seed is None else seed
        seeds = [int(selected_seed)] if str(selected_seed) else list(range(201, 206))
        axis = endpoint["axis"]
        group = endpoint["group"] if group is None else group
        key = (family, estimator, tuple(seeds), arm, field, axis, group)
        if key in self.cache:
            return self.cache[key]
        per_fit_points, per_fit_draws = [], []
        for fit_seed in seeds:
            worker = (0 if estimator == "HGB" else 5) + fit_seed - 201
            if arm == "Praw":
                phase = "selection" if family == "H_P" else "evaluation"
                source = self.new_blocks.get((worker, phase))
                if source is None:
                    return np.nan, np.full(len(weights), np.nan)
                numerator, denominator, source_days = source[field], source["N"], source["days"]
            else:
                prefix = family + "|" + arm
                if family == "E_R":
                    prefix += "|" + axis + "|" + group
                source = self.accounting[worker]
                numerator, denominator, source_days = (source[prefix + "|" + suffix] for suffix in (field, "N", "days"))
            self.flag(np.array_equal(source_days, days), "source_calendar_unchanged", key)
            denominator = np.asarray(denominator, float)
            numerator = np.asarray(numerator, float)
            # Independent direct ratio of totals; no day-mean averaging.
            observed_n = denominator.sum()
            draw_n = np.sum(weights * denominator[None, :], axis=1)
            draw_total = np.sum(weights * numerator[None, :], axis=1)
            draws = np.full(len(weights), np.nan)
            np.divide(draw_total, draw_n, out=draws, where=draw_n > 0)
            per_fit_points.append(numerator.sum() / observed_n if observed_n > 0 else np.nan)
            per_fit_draws.append(draws)
        # All five predefined fits are retained. An unavailable fit propagates
        # NaN; neither nanmean nor a reduced-fit replacement is used.
        result = float(np.mean(per_fit_points)), np.mean(np.stack(per_fit_draws), axis=0)
        self.cache[key] = result
        return result

    def reconstruct(self, endpoint, weights, days):
        metric = endpoint["metric"]
        if metric in ("absolute_V", "absolute_V_G"):
            return self.pooled(endpoint, endpoint["arm"], "V", weights, days)
        if metric == "gap_U":
            return self.pooled(endpoint, endpoint["arm"], "gap_U", weights, days)
        left, right = endpoint["comparison"].split("-minus-")
        field = "C" if metric == "D_C" else "U" if metric == "H_U" else metric.split("_")[-1]
        if metric.startswith("interaction_"):
            a, ad = self.pooled(endpoint, left, field, weights, days, group="at_or_above_10p5")
            b, bd = self.pooled(endpoint, right, field, weights, days, group="at_or_above_10p5")
            c, cd = self.pooled(endpoint, left, field, weights, days, group="below_10p5")
            d, dd = self.pooled(endpoint, right, field, weights, days, group="below_10p5")
            return (a - b) - (c - d), (ad - bd) - (cd - dd)
        a, ad = self.pooled(endpoint, left, field, weights, days)
        b, bd = self.pooled(endpoint, right, field, weights, days)
        point, draws = a - b, ad - bd
        if metric == "D_C":
            point = point / b if b > 0 else np.nan
            ratio = np.full_like(draws, np.nan)
            np.divide(draws, bd, out=ratio, where=bd > 0)
            draws = ratio
        elif metric == "H_U":
            point, draws = point * 10 / CSTAR, draws * 10 / CSTAR
        return point, draws

    def verify_family(self, path):
        self.track(path)
        family = json.loads(path.read_text())
        artifact_path = INFER / family["draw_artifact"]["path"]
        self.track(artifact_path)
        self.flag(sha(artifact_path) == family["draw_artifact"]["sha256"], "draw_artifact_identity", str(path))
        numeric = load_npz(artifact_path)
        weights, days, draws = numeric["day_weights"], numeric["natural_days"], numeric["draw_values"]
        ids = family["planned_coordinate_ids"]
        self.cache = {}  # A different stored draw schedule applies per span.
        self.flag(draws.shape == (20000, len(ids)), "all_draw_rows_and_coordinates_retained", str(path))
        self.flag(np.array_equal(numeric["draw_ids"], np.arange(20000)), "draw_ids_retained", str(path))
        self.flag(np.array_equal(numeric["coordinate_ids"], ids), "coordinate_order_preserved", str(path))
        self.flag(np.all(weights >= 0) and np.isfinite(weights).all() and
                  np.all(weights.sum(axis=1) == len(days)), "stored_weights_valid", str(path))
        self.flag(family["draw_count"] == 20000 and family["draw_rows_deleted"] == 0,
                  "reported_complete_draw_count", str(path))
        self.flag(np.all(np.diff(days) == 1), "uncompressed_natural_calendar", str(path))
        points = []
        eligible = []
        focused = []
        for index, endpoint in enumerate(family["coordinates"]):
            coordinate = endpoint["coordinate_id"]
            point, independent_draw = self.reconstruct(endpoint, weights, days)
            stored_point = np.nan if endpoint["point"] is None else endpoint["point"]
            self.close(point, stored_point, "daily_total_point_reconstruction", coordinate)
            self.close(independent_draw, draws[:, index], "stored_weight_draw_reconstruction", coordinate)
            points.append(stored_point)
            pop = np.asarray(endpoint["population_denominator"], float)
            ref = np.asarray(endpoint["reference_denominator"], float)
            dpop = numeric[f"c{index}__draw_population_denominators"]
            dref = numeric[f"c{index}__draw_reference_denominators"]
            support = (np.isfinite(pop).all() and np.all(pop > 0) and
                       np.isfinite(ref).all() and np.all(ref > 0) and
                       np.isfinite(dpop).all() and np.all(dpop > 0) and
                       np.isfinite(dref).all() and np.all(dref > 0) and
                       np.isfinite(stored_point) and np.isfinite(draws[:, index]).all())
            varying = bool(support and np.std(draws[:, index], ddof=1) > 1e-14)
            if varying:
                eligible.append(index)
            self.flag(varying == (endpoint["interval_status"] == "ESTIMATED_APPROX"),
                      "independent_interval_eligibility", coordinate)
            self.flag(endpoint["exact"] is False, "no_empirical_exact_inference", coordinate)
            if family["span"] == 3 and ((family["family_id"] == "E_P" and endpoint["metric"] in ("D_C", "H_U")) or
                (family["family_id"] == "E_R" and endpoint["metric"].startswith("interaction_")) or family["family_id"] == "E_G"):
                focused.append({"coordinate_id": coordinate, "point": endpoint["point"],
                                "interval_status": endpoint["interval_status"]})
        self.flag([ids[i] for i in eligible] == family["finite_coordinate_ids"], "finite_coordinate_ids_independent", str(path))
        critical = None
        if eligible:
            points = np.asarray(points, float)
            values = draws[:, eligible]
            sd = values.std(axis=0, ddof=1)
            maxima = np.max(np.abs(values - points[eligible]) / sd, axis=1)
            # The higher order statistic is computed explicitly, independently
            # of the original envelope implementation and np.quantile.
            critical = float(np.sort(maxima)[int(np.ceil(.95 * (len(maxima) - 1)))])
            self.close(critical, family["critical"], "manual_family_critical", str(path))
            lower, upper = points[eligible] - critical * sd, points[eligible] + critical * sd
            for column, endpoint_index in enumerate(eligible):
                endpoint = family["coordinates"][endpoint_index]
                self.close(sd[column], endpoint["standard_error"], "manual_standard_error", endpoint["coordinate_id"])
                self.close(lower[column], endpoint["lower"], "manual_lower_endpoint", endpoint["coordinate_id"])
                self.close(upper[column], endpoint["upper"], "manual_upper_endpoint", endpoint["coordinate_id"])
        else:
            self.flag(family["critical"] is None and family["status"] == "NO_ESTIMABLE_INTERVALS",
                      "empty_family_critical_is_na", str(path))
        return ({"family": family["family_id"], "span": family["span"], "planned_coordinates": len(ids),
                 "finite_interval_coordinates": len(eligible), "draw_count": 20000,
                 "manual_critical": critical, "stored_critical": family["critical"],
                 "focused_primary_coordinates": focused}, weights)


def main():
    audit = Reconciler()
    index_path = INFER / "families.json"
    audit.track(index_path)
    index = json.loads(index_path.read_text())
    families, shared_weights = [], {}
    for link in index["family_artifacts"]:
        result, weights = audit.verify_family(INFER / link)
        families.append(result)
        if result["family"] != "H_P":
            previous = shared_weights.setdefault(result["span"], weights)
            audit.flag(np.array_equal(previous, weights), "evaluation_families_share_identical_weights", link)
    audit.flag(len(families) == 12 and sum(f["planned_coordinates"] for f in families) == 882,
               "complete_default_family_ledger")
    after = {name: sha(HERE / name) for name in audit.inputs}
    audit.flag(after == audit.inputs, "sealed_inputs_unchanged")
    report = {
        "status": "PASS" if not audit.failures else "FAIL", "completed_utc": datetime.now(timezone.utc).isoformat(),
        "script_sha256": sha(Path(__file__)), "scope": "Numerical reconstruction of existing sealed values only",
        "method": "Independent daily-total arithmetic and stored-weight multiplication; explicit .95 higher order statistic",
        "numerical_tolerance": {"absolute": ABS_TOL, "relative": REL_TOL,
                                "interpretation": "Existing float64 accounting tolerance; not an effect threshold"},
        "checks": dict(audit.checks), "max_absolute_errors": audit.max_errors,
        "failures": audit.failures, "families": families, "input_sha256": audit.inputs,
        "sealed_inputs_unchanged": after == audit.inputs, "new_random_draws": 0,
        "bootstrap_or_resampler_called": False, "new_model_fits": 0,
        "measurement_arrays_loaded": False, "stored_results_or_intervals_replaced": False,
        "coverage_or_field_safety_certified": False,
    }
    output = HERE / "verification/numeric_reconciliation.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"status": report["status"], "families": len(families),
                      "coordinates": sum(f["planned_coordinates"] for f in families),
                      "max_absolute_errors": audit.max_errors, "failure_count": len(audit.failures)}, ensure_ascii=False))
    return 0 if not audit.failures else 1


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        raise SystemExit(main())
