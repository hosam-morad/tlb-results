#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
from pathlib import Path

from plots import (
    benchmark_speedup_barplot,
    mosmodel_plot,
    mosmodel_y_limits,
    summary_boxplot,
)


def fmt(value: float | None, digits: int = 3) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "—"
    css_class = "num-pos" if value > 0 else "num-neg" if value < 0 else ""
    return f'<span class="{css_class}">{value:+.1f}%</span>'


def fmt_slowdown(value: float | None) -> str:
    return "—" if value is None else f"{value:.1f}%"


def render_stlb_state(item: dict) -> str:
    shared = item.get("stlb_shared_percent")
    focal = item.get("stlb_focal_only_percent")
    corunner = item.get("stlb_corunner_only_percent")
    if shared is None or focal is None or corunner is None:
        return "—"

    return (
        '<div class="stlb-state">'
        f'<span>baseline <b>{shared:.1f}%</b></span>'
        f'<span>Benchmark-only <b>{focal:.1f}%</b></span>'
        f'<span>Co-runner-only <b>{corunner:.1f}%</b></span>'
        '</div>'
    )


def slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")
    return value or "item"


def benchmark_anchor(full_name: str) -> str:
    return f"benchmark-{slug(full_name)}"


def model_equation(a: float, b: float) -> str:
    sign = "+" if b >= 0 else "−"
    return f"CPI = {a:.6g} × MPKI {sign} {abs(b):.6g}"


def figure_version(figures_dir: Path, base_name: str) -> str:
    svg_path = figures_dir / f"{base_name}.svg"
    return hashlib.sha256(svg_path.read_bytes()).hexdigest()[:12]


def figure_html(
    base_name: str,
    alt: str,
    css_class: str = "",
    version: str | None = None,
) -> str:
    cls = f' class="{css_class}"' if css_class else ""
    escaped_alt = html.escape(alt, quote=True)
    cache_suffix = f"?v={version}" if version else ""
    return (
        f'<a href="figures/{base_name}.pdf{cache_suffix}" title="Open PDF figure">'
        f'<img{cls} src="figures/{base_name}.svg{cache_suffix}" alt="{escaped_alt}">'
        '</a>'
    )


def render_summary_table(benchmarks: list[dict]) -> str:
    rows = [
        "<table><thead><tr>",
        "<th>Benchmark</th>",
        "<th>Co-runners</th>",
        "<th>Mean speedup</th>",
        "<th>Median speedup</th>",
        "<th>Max slowdown</th>",
        "<th>Max speedup</th>",
        "</tr></thead><tbody>",
    ]

    for benchmark in benchmarks:
        rows.extend(
            [
                "<tr>",
                f'<td><a href="#{benchmark_anchor(benchmark["full"])}">'
                f'{html.escape(benchmark["full"])}</a></td>',
                f'<td>{benchmark["co_runner_count"]}</td>',
                f'<td>{fmt_pct(benchmark["mean_speedup"])}</td>',
                f'<td>{fmt_pct(benchmark["median_speedup"])}</td>',
                f'<td>{fmt_slowdown(benchmark["max_slowdown"])}</td>',
                f'<td>{fmt_pct(benchmark["max_speedup"])}</td>',
                "</tr>",
            ]
        )

    rows.append("</tbody></table>")
    return "".join(rows)


def render_pair_table(items: list[dict]) -> str:
    rows = [
        "<table><thead><tr>",
        "<th>Co-runner</th>",
        "<th>baseline MPKI</th>",
        "<th>wptlb MPKI</th>",
        "<th>baseline CPI</th>",
        "<th>wptlb CPI</th>",
        "<th>Benchmark speedup</th>",
        "<th>Co-runner speedup</th>",
        "<th>wptlb STLB state</th>",
        "</tr></thead><tbody>",
    ]

    for item in items:
        rows.extend(
            [
                "<tr>",
                f'<td>{html.escape(item["corunner_full"])}</td>',
                f'<td>{fmt(item["shared_mpki"], 1)}</td>',
                f'<td>{fmt(item["uniform_mpki"], 1)}</td>',
                f'<td>{fmt(item["shared_cpi"], 2)}</td>',
                f'<td>{fmt(item["uniform_cpi"], 2)}</td>',
                f'<td>{fmt_pct(item["speedup"])}</td>',
                f'<td>{fmt_pct(item["corunner_speedup"])}</td>',
                f'<td>{render_stlb_state(item)}</td>',
                "</tr>",
            ]
        )

    rows.append("</tbody></table>")
    return "".join(rows)




def sort_pairs_by_focal_speedup(items: list[dict]) -> list[dict]:
    def sort_key(item: dict) -> tuple[float, str]:
        speedup = item.get("speedup")
        numeric = float("inf") if speedup is None else -float(speedup)
        return (numeric, item.get("corunner_full", ""))

    return sorted(items, key=sort_key)

def render_benchmark_sections(benchmarks: list[dict], figures_dir: Path) -> str:
    sections: list[str] = []

    for benchmark in benchmarks:
        sorted_pairs = sort_pairs_by_focal_speedup(benchmark["pairs"])
        plot_benchmark = dict(benchmark)
        plot_benchmark["pairs"] = sorted_pairs

        speedup_base_name = "speedup_" + slug(benchmark["short"])
        benchmark_speedup_barplot(plot_benchmark, figures_dir / speedup_base_name)
        speedup_plot_html = figure_html(
            speedup_base_name,
            f'{benchmark["full"]} benchmark and co-runner speedups',
            version=figure_version(figures_dir, speedup_base_name),
        )

        mosmodel_ylim = mosmodel_y_limits(sorted_pairs)
        plots: list[str] = []
        for item in sorted_pairs:
            base_name = (
                "mosmodel_"
                + slug(item["focal_short"])
                + "__"
                + slug(item["corunner_short"])
            )
            mosmodel_plot(
                item,
                figures_dir / base_name,
                y_limits=mosmodel_ylim,
            )
            plots.append(
                '<div class="plot-card">'
                + figure_html(
                    base_name,
                    f'{item["focal_full"]} with {item["corunner_full"]} mosmodel',
                    version=figure_version(figures_dir, base_name),
                )
                + '<div class="model-equation">'
                + html.escape(model_equation(item["model_a"], item["model_b"]))
                + "</div></div>"
            )

        sections.append(
            f'<section id="{benchmark_anchor(benchmark["full"])}">'
            f'<h2>{html.escape(benchmark["full"])}'
            '<a class="back" href="#top">Back to top ↑</a></h2>'
            '<h3>Speedup by co-runner</h3>'
            '<div class="card benchmark-speedup-plot">'
            + speedup_plot_html
            + "</div>"
            '<h3>Pair results</h3>'
            '<div class="card">'
            + render_pair_table(sorted_pairs)
            + "</div>"
            '<h3>mosmodel graphs with co-runners</h3>'
            '<div class="plot-grid">'
            + "".join(plots)
            + "</div></section>"
        )

    return "".join(sections)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the SMT results website")
    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--template",
        default=str(Path(__file__).with_name("template.html")),
    )
    parser.add_argument(
        "--style",
        default=str(Path(__file__).with_name("style.css")),
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--figures-dir")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    template = Path(args.template).read_text(encoding="utf-8")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    figures_dir = (
        Path(args.figures_dir)
        if args.figures_dir
        else output.parent / "figures"
    )

    if figures_dir.exists():
        shutil.rmtree(figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)

    summary_base = "summary_speedup"
    summary_boxplot(data["benchmarks"], figures_dir / summary_base)
    summary_html = (
        figure_html(
            summary_base,
            "Speedup distribution by benchmark",
            version=figure_version(figures_dir, summary_base),
        )
        if data["benchmarks"]
        else ""
    )

    page = template.replace("__SUMMARY_TABLE__", render_summary_table(data["benchmarks"]))
    page = page.replace("__SUMMARY_PLOT__", summary_html)
    page = page.replace(
        "__BENCHMARK_SECTIONS__",
        render_benchmark_sections(data["benchmarks"], figures_dir),
    )

    output.write_text(page, encoding="utf-8")
    shutil.copyfile(args.style, output.parent / "style.css")
    (output.parent / ".nojekyll").touch()

    print(f"Wrote {output}")
    print(f"Wrote figures to {figures_dir} (SVG, PNG, PDF)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
