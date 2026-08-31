from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


FIGURE_FORMATS = ("svg", "png", "pdf")


def _save(fig, output_base: Path) -> None:
    output_base.parent.mkdir(parents=True, exist_ok=True)
    for suffix in FIGURE_FORMATS:
        kwargs = {"bbox_inches": "tight"}
        if suffix == "png":
            kwargs["dpi"] = 180
        fig.savefig(output_base.with_suffix(f".{suffix}"), format=suffix, **kwargs)
    plt.close(fig)


def _pct_label(value: float) -> str:
    return f"{value:+.1f}%"


def _expand_limits(values: list[float], pad_ratio: float = 0.12) -> tuple[float, float]:
    if not values:
        return -1.0, 1.0
    low = min(values)
    high = max(values)
    if low == high:
        pad = max(abs(low) * pad_ratio, 1.0)
        return low - pad, high + pad
    span = high - low
    pad = max(span * pad_ratio, 0.6)
    return low - pad, high + pad


def summary_boxplot(benchmarks: list[dict], output_base: Path) -> None:
    if not benchmarks:
        return

    width = max(11.0, 0.62 * len(benchmarks))
    fig, ax = plt.subplots(figsize=(width, 5.8))

    series = [benchmark["speedups"] for benchmark in benchmarks]
    labels = [benchmark["short"] for benchmark in benchmarks]
    positions = list(range(1, len(benchmarks) + 1))

    boxplot = ax.boxplot(
        series,
        labels=labels,
        showmeans=True,
        showfliers=False,
        whis=(0, 100),
    )

    all_values: list[float] = []
    for x, values in zip(positions, series):
        all_values.extend(values)
        if len(values) == 1:
            offsets = [0.0]
        else:
            spread = 0.18
            offsets = [
                (-spread / 2.0) + spread * i / (len(values) - 1)
                for i in range(len(values))
            ]
        ax.scatter(
            [x + offset for offset in offsets],
            values,
            s=22,
            marker="o",
            alpha=0.85,
        )

        min_value = min(values)
        max_value = max(values)
        ax.annotate(
            _pct_label(max_value),
            xy=(x, max_value),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )
        ax.annotate(
            _pct_label(min_value),
            xy=(x, min_value),
            xytext=(0, -9),
            textcoords="offset points",
            ha="center",
            va="top",
            fontsize=8,
        )

    ax.axhline(0.0, linewidth=0.9)
    ax.set_ylabel("Predicted speedup (%)")
    ax.set_title("Speedup distribution by benchmark")
    ax.tick_params(axis="x", labelrotation=45)
    ax.grid(axis="y", linewidth=0.5, alpha=0.35)
    ax.set_ylim(*_expand_limits(all_values, pad_ratio=0.14))

    point_handle = Line2D(
        [], [], marker="o", linestyle="None", markersize=5, label="Co-runner point"
    )
    ax.legend(
        [
            boxplot["boxes"][0],
            boxplot["medians"][0],
            boxplot["means"][0],
            boxplot["whiskers"][0],
            point_handle,
        ],
        ["IQR", "Median", "Mean", "Min/Max", "Co-runner point"],
        loc="best",
        fontsize=8,
        ncol=5,
    )
    fig.tight_layout()
    _save(fig, output_base)


def benchmark_speedup_barplot(benchmark: dict, output_base: Path) -> None:
    pairs = benchmark["pairs"]
    if not pairs:
        return

    labels = [item["corunner_short"] for item in pairs]
    benchmark_speedups = [item["speedup"] for item in pairs]
    corunner_speedups = [item["corunner_speedup"] for item in pairs]

    positions = list(range(len(pairs)))
    bar_width = 0.38
    width = max(8.0, 0.72 * len(pairs))
    fig, ax = plt.subplots(figsize=(width, 4.8))

    benchmark_bars = ax.bar(
        [position - bar_width / 2.0 for position in positions],
        benchmark_speedups,
        width=bar_width,
        label="Benchmark",
    )
    corunner_bars = ax.bar(
        [position + bar_width / 2.0 for position in positions],
        corunner_speedups,
        width=bar_width,
        label="Co-runner",
    )

    def annotate_bar(bar) -> None:
        value = float(bar.get_height())
        x = bar.get_x() + bar.get_width() / 2.0
        if value >= 0:
            offset = 3
            va = "bottom"
        else:
            offset = -3
            va = "top"
        ax.annotate(
            _pct_label(value),
            xy=(x, value),
            xytext=(0, offset),
            textcoords="offset points",
            ha="center",
            va=va,
            fontsize=8,
            rotation=90,
        )

    for benchmark_bar, corunner_bar in zip(benchmark_bars, corunner_bars):
        benchmark_value = float(benchmark_bar.get_height())
        corunner_value = float(corunner_bar.get_height())
        if max(abs(benchmark_value), abs(corunner_value)) < 1.0:
            continue
        annotate_bar(benchmark_bar)
        annotate_bar(corunner_bar)

    all_values = benchmark_speedups + corunner_speedups + [0.0]
    ax.axhline(0.0, linewidth=0.9)
    ax.set_xticks(positions, labels=labels, rotation=45, ha="right")
    ax.set_ylabel("Predicted speedup (%)")
    ax.set_title(f'{benchmark["short"]} speedup by co-runner')
    ax.grid(axis="y", linewidth=0.5, alpha=0.35)
    ax.legend(loc="best")
    ax.set_ylim(*_expand_limits(all_values, pad_ratio=0.18))
    fig.tight_layout()
    _save(fig, output_base)


def mosmodel_y_limits(items: list[dict]) -> tuple[float, float] | None:
    cpi_values: list[float] = []
    for item in items:
        cpi_values.extend(
            [
                float(item["shared_cpi"]),
                float(item["uniform_cpi"]),
            ]
        )
        cpi_values.extend(float(point["cpi"]) for point in item["mosmodel_points"])

    if not cpi_values:
        return None

    low = min(cpi_values)
    high = max(cpi_values)

    # Keep low-CPI plots on a stable 0..1 scale instead of letting
    # autoscaling exaggerate tiny differences.
    if high < 1.0:
        return 0.0, 1.0

    # When every meaningful CPI point is at least 1, use CPI=1 as the
    # common visual baseline. Otherwise retain zero as the baseline.
    lower = 1.0 if low >= 1.0 else 0.0
    span = max(high - lower, 0.0)
    upper_padding = max(0.10 * span, 0.05)
    return lower, high + upper_padding


def mosmodel_plot(
    item: dict,
    output_base: Path,
    y_limits: tuple[float, float] | None = None,
) -> None:
    a = item["model_a"]
    b = item["model_b"]
    shared_mpki = item["shared_mpki"]
    uniform_mpki = item["uniform_mpki"]
    measured = item["mosmodel_points"]

    x_values = [shared_mpki, uniform_mpki] + [point["mpki"] for point in measured]
    x_min = min(x_values)
    x_max = max(x_values)
    span = max(x_max - x_min, 1.0)
    start = max(0.0, x_min - 0.12 * span)
    end = x_max + 0.12 * span
    line_x = [start + (end - start) * i / 100.0 for i in range(101)]
    line_y = [a * x + b for x in line_x]

    fig, ax = plt.subplots(figsize=(5.0, 3.6))
    ax.plot(line_x, line_y, label="_nolegend_")

    handles = []
    labels = []
    for point in measured:
        handle = ax.scatter(
            [point["mpki"]],
            [point["cpi"]],
            s=40,
            label=f'{point["layout"]} measured',
        )
        handles.append(handle)
        labels.append(f'{point["layout"]} measured')

    baseline_handle = ax.scatter(
        [shared_mpki],
        [item["shared_cpi"]],
        s=60,
        marker="o",
        label="baseline",
    )
    ptlb_handle = ax.scatter(
        [uniform_mpki],
        [item["uniform_cpi"]],
        s=90,
        marker="*",
        label="wptlb",
    )
    handles.extend([baseline_handle, ptlb_handle])
    labels.extend(["baseline", "wptlb"])

    ax.set_xlabel("MPKI")
    ax.set_ylabel("CPI")
    ax.set_title(item["corunner_full"])
    if y_limits is not None:
        ax.set_ylim(*y_limits)
    ax.grid(linewidth=0.5, alpha=0.3)
    ax.legend(handles, labels, fontsize=7, loc="best")
    fig.tight_layout()
    _save(fig, output_base)
