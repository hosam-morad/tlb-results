from __future__ import annotations

import csv
from pathlib import Path


REQUIRED_COLUMNS = (
    "L2/Thread1/Misses",
    "L2/Thread2/Misses",
    "Thread1/InstructionCount",
    "Thread2/InstructionCount",
)


def read_mpki(path: Path) -> tuple[float, float]:
    """Return final cumulative STLB MPKI for thread 1 and thread 2."""
    if not path.is_file():
        raise FileNotFoundError(path)

    last_row: dict[str, str] | None = None
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"empty simulator CSV: {path}")

        missing = [name for name in REQUIRED_COLUMNS if name not in reader.fieldnames]
        if missing:
            raise KeyError(
                f"{path}: missing simulator column(s): {', '.join(missing)}"
            )

        for row in reader:
            last_row = row

    if last_row is None:
        raise ValueError(f"simulator CSV has no data rows: {path}")

    values: list[float] = []
    for side in (1, 2):
        misses = float(last_row[f"L2/Thread{side}/Misses"])
        instructions = float(last_row[f"Thread{side}/InstructionCount"])
        if instructions <= 0:
            raise ValueError(
                f"{path}: Thread{side}/InstructionCount must be > 0, got {instructions}"
            )
        values.append(1000.0 * misses / instructions)

    return values[0], values[1]
