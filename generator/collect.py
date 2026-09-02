#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from statistics import mean, median

from archive_results import ArchiveResults, ArchiveResult
from mosmodel import load_coefficients, load_training_data, speedup
from benchmark_names import full_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect archived baseline/wptlb SMT results for the HTML dashboard."
    )
    parser.add_argument(
        "--baseline-results",
        default="archive/hosam.morad/results/smt/shared/lru/all_workloads.csv",
    )
    parser.add_argument(
        "--wptlb-results",
        default="archive/hosam.morad/results/smt/uniform_ownership/lru/pi_5ms_dw3_oi10p/all_workloads.csv",
    )
    parser.add_argument(
        "--coefficients-csv",
        default="archive/hosam.morad/linear_models/smt/coefficients.csv",
    )
    parser.add_argument(
        "--training-data-csv",
        default="archive/hosam.morad/linear_models/smt/training_data.csv",
    )
    parser.add_argument(
        "--archive-root",
        default="archive/hosam.morad",
    )
    parser.add_argument(
        "--workloads-script",
        default="archive/hosam.morad/common_smt_workloads.py",
    )
    parser.add_argument(
        "--workloads",
        nargs="*",
        help="Optional explicit workload override. By default use current archived common workloads.",
    )
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def load_workloads(
    *,
    explicit_workloads: list[str] | None,
    workloads_script: Path,
    archive_root: Path,
) -> list[str]:
    if explicit_workloads:
        return list(dict.fromkeys(explicit_workloads))

    proc = subprocess.run(
        [
            sys.executable,
            str(workloads_script),
            "--archive-root",
            str(archive_root),
            "--format",
            "plain",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return list(dict.fromkeys(proc.stdout.split()))



def split_pair(workload: str) -> tuple[str, str]:
    parts = workload.split("+")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"invalid workload: {workload!r}")
    return parts[0], parts[1]


def directional_lookup(
    mapping,
    focal_short: str,
    corunner_short: str,
    focal_full: str,
    corunner_full: str,
    what: str,
):
    value = mapping.get((focal_short, corunner_short))
    if value is None:
        value = mapping.get((focal_full, corunner_full))
    if value is None:
        raise KeyError(
            f"missing directional {what}: {focal_short}+{corunner_short} "
            f"({focal_full}+{corunner_full})"
        )
    return value


def build_side(
    *,
    focal_short: str,
    corunner_short: str,
    shared_mpki: float,
    uniform_mpki: float,
    shared_cpi: float,
    uniform_cpi: float,
    coefficients,
    training_data,
    uniform_result: ArchiveResult,
    focal_thread: int,
) -> dict:
    focal_full = full_name(focal_short)
    corunner_full = full_name(corunner_short)

    a, b = directional_lookup(
        coefficients,
        focal_short,
        corunner_short,
        focal_full,
        corunner_full,
        "mosmodel",
    )
    points = directional_lookup(
        training_data,
        focal_short,
        corunner_short,
        focal_full,
        corunner_full,
        "mosmodel training data",
    )
    signed_speedup = speedup(shared_cpi, uniform_cpi)

    result = {
        "focal_short": focal_short,
        "focal_full": focal_full,
        "corunner_short": corunner_short,
        "corunner_full": corunner_full,
        "shared_mpki": shared_mpki,
        "uniform_mpki": uniform_mpki,
        "shared_cpi": shared_cpi,
        "uniform_cpi": uniform_cpi,
        "speedup": signed_speedup,
        "slowdown": max(0.0, -signed_speedup),
        "model_a": a,
        "model_b": b,
        "mosmodel_points": points,
    }
    result.update(uniform_result.directional_stlb_state(focal_thread=focal_thread))
    return result


def main() -> int:
    args = parse_args()

    baseline_results_csv = Path(args.baseline_results)
    wptlb_results_csv = Path(args.wptlb_results)
    coefficients_csv = Path(args.coefficients_csv)
    training_data_csv = Path(args.training_data_csv)
    archive_root = Path(args.archive_root)
    workloads_script = Path(args.workloads_script)

    coefficients = load_coefficients(coefficients_csv)
    training_data = load_training_data(training_data_csv)
    baseline_results = ArchiveResults(baseline_results_csv)
    wptlb_results = ArchiveResults(wptlb_results_csv, require_stlb_state=True)
    workloads = load_workloads(
        explicit_workloads=args.workloads,
        workloads_script=workloads_script,
        archive_root=archive_root,
    )

    pair_results: list[dict] = []
    directional_results: list[dict] = []
    skipped_workloads: list[str] = []

    for workload in workloads:
        benchmark1, benchmark2 = split_pair(workload)

        try:
            shared1 = baseline_results.take(benchmark1, benchmark2)
            shared2 = baseline_results.take(benchmark2, benchmark1)
            uniform1 = wptlb_results.take(benchmark1, benchmark2)
            uniform2 = wptlb_results.take(benchmark2, benchmark1)
        except KeyError as exc:
            skipped_workloads.append(workload)
            print(f"Skipping {workload}: {exc}", file=sys.stderr)
            continue

        side1 = build_side(
            focal_short=benchmark1,
            corunner_short=benchmark2,
            shared_mpki=shared1.mpki,
            uniform_mpki=uniform1.mpki,
            shared_cpi=shared1.cpi,
            uniform_cpi=uniform1.cpi,
            coefficients=coefficients,
            training_data=training_data,
            uniform_result=uniform1,
            focal_thread=1,
        )
        side2 = build_side(
            focal_short=benchmark2,
            corunner_short=benchmark1,
            shared_mpki=shared2.mpki,
            uniform_mpki=uniform2.mpki,
            shared_cpi=shared2.cpi,
            uniform_cpi=uniform2.cpi,
            coefficients=coefficients,
            training_data=training_data,
            uniform_result=uniform2,
            focal_thread=2,
        )

        side1["corunner_speedup"] = side2["speedup"]
        side2["corunner_speedup"] = side1["speedup"]

        pair_results.append(
            {
                "workload": workload,
                "benchmark1_short": benchmark1,
                "benchmark2_short": benchmark2,
                "benchmark1_full": side1["focal_full"],
                "benchmark2_full": side2["focal_full"],
                "baseline_results_csv": str(baseline_results_csv),
                "wptlb_results_csv": str(wptlb_results_csv),
                "side1": side1,
                "side2": side2,
            }
        )

        if benchmark1 == benchmark2:
            # A self-pair contributes one focal/co-runner observation. Average the
            # two identical benchmark instances rather than choosing one arbitrarily.
            combined = dict(side1)
            for key in (
                "shared_mpki",
                "uniform_mpki",
                "shared_cpi",
                "uniform_cpi",
                "speedup",
            ):
                combined[key] = (side1[key] + side2[key]) / 2.0
            combined["slowdown"] = max(0.0, -combined["speedup"])
            combined["corunner_speedup"] = combined["speedup"]
            directional_results.append(combined)
        else:
            directional_results.extend((side1, side2))

    grouped: dict[str, list[dict]] = {}
    for item in directional_results:
        grouped.setdefault(item["focal_short"], []).append(item)

    benchmarks: list[dict] = []
    for short, items in grouped.items():
        values = [item["speedup"] for item in items]
        benchmarks.append(
            {
                "short": short,
                "full": items[0]["focal_full"],
                "co_runner_count": len(items),
                "mean_speedup": mean(values),
                "median_speedup": median(values),
                "min_speedup": min(values),
                "max_slowdown": max(0.0, -min(values)),
                "max_speedup": max(values),
                "speedups": values,
                "pairs": items,
            }
        )

    benchmarks.sort(key=lambda item: (-item["max_speedup"], item["full"]))

    output = {
        "inputs": {
            "baseline_results_csv": str(baseline_results_csv),
            "wptlb_results_csv": str(wptlb_results_csv),
            "coefficients_csv": str(coefficients_csv),
            "training_data_csv": str(training_data_csv),
            "archive_root": str(archive_root),
            "workloads_script": str(workloads_script),
        },
        "collection": {
            "current_workload_count": len(workloads),
            "completed_workload_count": len(pair_results),
            "skipped_workloads": skipped_workloads,
        },
        "benchmarks": benchmarks,
        "pairs": pair_results,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(
        f"Wrote {output_path}: {len(benchmarks)} focal benchmark(s), "
        f"{len(pair_results)}/{len(workloads)} current workload(s) complete, "
        f"{len(skipped_workloads)} skipped"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
