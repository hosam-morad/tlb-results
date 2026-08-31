from __future__ import annotations

import csv
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path


STLB_COLUMNS = (
    "stlb_shared_percent",
    "stlb_thread1_only_percent",
    "stlb_thread2_only_percent",
)


@dataclass(frozen=True)
class ArchiveResult:
    mpki: float
    cpi: float
    stlb_shared_percent: float | None = None
    stlb_thread1_only_percent: float | None = None
    stlb_thread2_only_percent: float | None = None

    def directional_stlb_state(self, *, focal_thread: int) -> dict[str, float | int | None]:
        if self.stlb_shared_percent is None:
            return {
                "stlb_shared_percent": None,
                "stlb_focal_only_percent": None,
                "stlb_corunner_only_percent": None,
                "stlb_state_sample_count": None,
            }

        if focal_thread == 1:
            focal = self.stlb_thread1_only_percent
            corunner = self.stlb_thread2_only_percent
        elif focal_thread == 2:
            focal = self.stlb_thread2_only_percent
            corunner = self.stlb_thread1_only_percent
        else:
            raise ValueError(f"focal_thread must be 1 or 2, got {focal_thread!r}")

        return {
            "stlb_shared_percent": self.stlb_shared_percent,
            "stlb_focal_only_percent": focal,
            "stlb_corunner_only_percent": corunner,
            # The compact archive stores percentages rather than raw decision rows.
            "stlb_state_sample_count": None,
        }


class ArchiveResults:
    """Directional rows from an archived all_workloads.csv.

    Rows are kept in file order so self-pairs (A|A) can consume the two
    directional thread rows independently.

    Shared results contain benchmark/mpki/cpi. Uniform-ownership results also
    contain the three archived STLB ownership percentages.
    """

    def __init__(self, path: Path, *, require_stlb_state: bool = False) -> None:
        self.path = path
        self._rows: dict[tuple[str, str], deque[ArchiveResult]] = defaultdict(deque)

        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            required = {"benchmark", "mpki", "cpi"}
            missing = sorted(required - set(fieldnames))
            if missing:
                raise ValueError(f"{path}: missing required column(s): {', '.join(missing)}")

            present_stlb = [column for column in STLB_COLUMNS if column in fieldnames]
            if present_stlb and len(present_stlb) != len(STLB_COLUMNS):
                missing_stlb = [column for column in STLB_COLUMNS if column not in fieldnames]
                raise ValueError(
                    f"{path}: incomplete STLB columns; missing {', '.join(missing_stlb)}"
                )
            has_stlb_state = len(present_stlb) == len(STLB_COLUMNS)
            if require_stlb_state and not has_stlb_state:
                raise ValueError(
                    f"{path}: expected archived STLB columns: {', '.join(STLB_COLUMNS)}"
                )

            for line_number, row in enumerate(reader, start=2):
                benchmark = row["benchmark"]
                parts = benchmark.split("|")
                if len(parts) != 2 or not parts[0] or not parts[1]:
                    raise ValueError(
                        f"{path}:{line_number}: invalid benchmark key {benchmark!r}"
                    )
                try:
                    mpki = float(row["mpki"])
                    cpi = float(row["cpi"])
                    if has_stlb_state:
                        stlb_values = tuple(float(row[column]) for column in STLB_COLUMNS)
                    else:
                        stlb_values = (None, None, None)
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"{path}:{line_number}: invalid numeric result"
                    ) from exc

                if has_stlb_state:
                    assert all(value is not None for value in stlb_values)
                    if any(value < 0.0 or value > 100.0 for value in stlb_values):
                        raise ValueError(
                            f"{path}:{line_number}: STLB percentage outside [0, 100]"
                        )
                    total = sum(stlb_values)  # type: ignore[arg-type]
                    if abs(total - 100.0) > 0.02:
                        raise ValueError(
                            f"{path}:{line_number}: STLB percentages sum to {total:.4f}, not 100"
                        )

                self._rows[(parts[0], parts[1])].append(
                    ArchiveResult(
                        mpki=mpki,
                        cpi=cpi,
                        stlb_shared_percent=stlb_values[0],
                        stlb_thread1_only_percent=stlb_values[1],
                        stlb_thread2_only_percent=stlb_values[2],
                    )
                )

    def take(self, focal: str, corunner: str) -> ArchiveResult:
        key = (focal, corunner)
        values = self._rows.get(key)
        if not values:
            raise KeyError(f"{self.path}: missing archived result for {focal}|{corunner}")
        return values.popleft()
