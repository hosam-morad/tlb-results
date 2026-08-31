from __future__ import annotations

import csv
from pathlib import Path


def load_coefficients(path: Path) -> dict[tuple[str, str], tuple[float, float]]:
    if not path.is_file():
        raise FileNotFoundError(path)

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"empty coefficients CSV: {path}")

        required = {"benchmark1", "benchmark2", "yaniv_A", "yaniv_B"}
        missing = required.difference(reader.fieldnames)
        if missing:
            raise KeyError(
                f"{path}: missing coefficient column(s): {', '.join(sorted(missing))}"
            )

        models: dict[tuple[str, str], tuple[float, float]] = {}
        for row in reader:
            key = (row["benchmark1"].strip(), row["benchmark2"].strip())
            models[key] = (float(row["yaniv_A"]), float(row["yaniv_B"]))

    return models


def load_training_data(path: Path) -> dict[tuple[str, str], list[dict[str, float | str]]]:
    if not path.is_file():
        raise FileNotFoundError(path)

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"empty training-data CSV: {path}")

        required = {
            "benchmark1",
            "benchmark2",
            "MPKI_4KB",
            "MPKI_2MB",
            "CPI_4KB",
            "CPI_2MB",
        }
        missing = required.difference(reader.fieldnames)
        if missing:
            raise KeyError(
                f"{path}: missing training-data column(s): {', '.join(sorted(missing))}"
            )

        data: dict[tuple[str, str], list[dict[str, float | str]]] = {}
        for row in reader:
            key = (row["benchmark1"].strip(), row["benchmark2"].strip())
            data[key] = [
                {
                    "layout": "4KB",
                    "mpki": float(row["MPKI_4KB"]),
                    "cpi": float(row["CPI_4KB"]),
                },
                {
                    "layout": "2MB",
                    "mpki": float(row["MPKI_2MB"]),
                    "cpi": float(row["CPI_2MB"]),
                },
            ]

    return data


def predict_cpi(a: float, b: float, mpki: float) -> float:
    return a * mpki + b


def speedup(shared_cpi: float, uniform_cpi: float) -> float:
    if uniform_cpi == 0:
        raise ZeroDivisionError("uniform predicted CPI is zero")
    return (shared_cpi / uniform_cpi - 1.0) * 100.0
