"""Compare the former full rebuild with differential interpolation updates."""

# Benchmark design
# ----------------
#
# This benchmark compares two interpolation strategies for the same reading
# edit. It intentionally keeps the former implementation in this file, so a
# later run does not depend on Git history, a previous release, or `git diff`.
# The current differential implementation is imported from the integration and
# therefore changes when the production implementation changes.
#
# Former full-rebuild strategy
# ----------------------------
#
# The legacy implementation validates and sorts every reading, walks every
# interpolation segment, and distributes the complete history into UTC hourly
# buckets. The production code then removed the meter's complete long-term
# statistic from Home Assistant's recorder and imported every calculated hour
# again. Consequently, changing a single recent reading still recalculated and
# rewrote years or decades of unaffected history.
#
# Current differential strategy
# -----------------------------
#
# The current implementation compares the old and new piecewise-linear curves
# between their combined support points. Ranges whose linear functions and
# coverage are identical are discarded before any hourly calculation. Only
# hours touched by a genuinely changed range become candidates.
#
# For each candidate hour, the old and new hourly consumption and cumulative
# value are calculated. The update plan contains only:
#
# - `delete_starts`: hours that existed before but are no longer covered.
# - `upsert`: new hours and existing hours whose calculated values changed.
#
# Candidate hours whose final hourly values are equal are omitted. This also
# means that adding a collinear reading, or changing a curve only inside one
# hour without changing that hour's aggregate, causes no recorder write.
# Unaffected recorder rows retain their database identity and stored values.
#
# What is measured
# ----------------
#
# The `Old ms` and `New ms` columns measure only Python calculation time. They
# deliberately exclude storage writes, recorder queue latency, SQL execution,
# transaction commits, and Home Assistant scheduling. Garbage collection runs
# before every sample, and the table reports the median to reduce noise.
#
# `Old del/upsert` shows how many hourly rows the former production workflow
# discarded and reimported. `New del/upsert` shows the exact row counts in the
# differential update plan. These counts describe recorder work but do not
# pretend to be database timing measurements.
#
# Synthetic data and scenarios
# ----------------------------
#
# The generated readings are monotonic, approximately monthly, and have varying
# deltas so middle corrections and deletions change the neighboring slopes. The
# scenarios cover appending the latest reading, correcting and deleting a
# middle reading, deleting the latest reading, and inserting a collinear middle
# reading that must produce an empty update plan.
#
# Results are machine- and Python-version-dependent. Compare relative timings
# and affected row counts rather than treating absolute milliseconds as a Home
# Assistant end-to-end performance guarantee.
#
# How to run
# ----------
#
# Run the benchmark from the repository root with the system's Python 3:
#
#     python3 benchmarks/benchmark_interpolation.py
#
# The default run generates 20 years of readings and reports the median of
# three measurements per scenario. Use `--years` to change the simulated
# history size and `--repeat` to change the number of timed measurements:
#
#     python3 benchmarks/benchmark_interpolation.py --years 40 --repeat 5
#
# Larger histories make the difference between rebuilding all hourly rows and
# updating only affected hours easier to observe, but require more runtime and
# memory. Increase `--repeat` when comparing code revisions to reduce timing
# noise. Use the same Python version, arguments, and machine for comparable
# results.
#
# `Old ms` and `New ms` contain the median calculation times. `Speedup` is old
# time divided by new time. The final two columns show deleted and upserted
# hourly rows as `delete/upsert`; they are operation counts, not timings.

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import gc
import math
from pathlib import Path
from statistics import median
import sys
from time import perf_counter
from typing import TypeVar

MODULE_DIR = (
    Path(__file__).parents[1] / "custom_components" / "manual_energy_metering"
)
sys.path.insert(0, str(MODULE_DIR))

from interpolation import (  # noqa: E402
    ONE_HOUR,
    HourlyConsumption,
    Reading,
    changed_hourly_statistics,
    validate_readings,
)

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Scenario:
    """One reading edit to benchmark."""

    name: str
    old_readings: tuple[Reading, ...]
    new_readings: tuple[Reading, ...]


def legacy_hourly_consumption(
    readings: Iterable[Reading],
) -> list[HourlyConsumption]:
    """Run the exact full-history calculation used before differential updates."""
    ordered = validate_readings(readings)
    buckets: dict[datetime, list[float]] = {}

    for previous, current in zip(ordered, ordered[1:]):
        duration = (current.timestamp - previous.timestamp).total_seconds()
        delta = current.value - previous.value
        rate = delta / duration

        bucket_start = previous.timestamp.replace(
            minute=0, second=0, microsecond=0
        )
        while bucket_start < current.timestamp:
            bucket_end = bucket_start + ONE_HOUR
            overlap_start = max(previous.timestamp, bucket_start)
            overlap_end = min(current.timestamp, bucket_end)
            if overlap_end > overlap_start:
                seconds = (overlap_end - overlap_start).total_seconds()
                buckets.setdefault(bucket_start, []).append(rate * seconds)
            bucket_start = bucket_end

    result: list[HourlyConsumption] = []
    cumulative = 0.0
    for start in sorted(buckets):
        consumption = math.fsum(buckets[start])
        cumulative = math.fsum((cumulative, consumption))
        result.append(HourlyConsumption(start, consumption, cumulative))
    return result


def build_readings(years: int) -> tuple[Reading, ...]:
    """Create monotonically increasing readings roughly one month apart."""
    timestamp = datetime(2000, 1, 1, tzinfo=timezone.utc)
    value = 10_000.0
    readings = [Reading(timestamp, value)]
    for index in range(years * 12):
        timestamp += timedelta(days=30)
        value += 350.0 + (index % 7) * 17.0
        readings.append(Reading(timestamp, value))
    return tuple(readings)


def build_scenarios(readings: tuple[Reading, ...]) -> list[Scenario]:
    """Build representative add, modify, and delete operations."""
    middle = len(readings) // 2
    previous = readings[middle - 1]
    current = readings[middle]
    following = readings[middle + 1]

    corrected_value = previous.value + (following.value - previous.value) * 0.8
    if math.isclose(corrected_value, current.value):
        corrected_value = previous.value + (
            following.value - previous.value
        ) * 0.2
    corrected = list(readings)
    corrected[middle] = Reading(current.timestamp, corrected_value)

    deleted_middle = list(readings)
    del deleted_middle[middle]

    inserted_collinear = list(readings)
    inserted_collinear.insert(
        middle + 1,
        Reading(
            current.timestamp + (following.timestamp - current.timestamp) / 2,
            current.value + (following.value - current.value) / 2,
        ),
    )

    appended = [
        *readings,
        Reading(
            readings[-1].timestamp + timedelta(days=30),
            readings[-1].value + 450,
        ),
    ]

    return [
        Scenario("append latest", readings, tuple(appended)),
        Scenario("correct middle", readings, tuple(corrected)),
        Scenario("delete middle", readings, tuple(deleted_middle)),
        Scenario("delete latest", readings, readings[:-1]),
        Scenario("collinear insert", readings, tuple(inserted_collinear)),
    ]


def benchmark(function: Callable[[], T], repeat: int) -> float:
    """Return the median runtime in milliseconds."""
    timings: list[float] = []
    for _ in range(repeat):
        gc.collect()
        started = perf_counter()
        result = function()
        timings.append((perf_counter() - started) * 1_000)
        del result
    return median(timings)


def main() -> None:
    """Run and print the comparison."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=20)
    parser.add_argument("--repeat", type=int, default=3)
    args = parser.parse_args()
    if args.years < 1 or args.repeat < 1:
        parser.error("--years and --repeat must be positive")

    readings = build_readings(args.years)
    baseline = readings[0].value
    current_rows = len(legacy_hourly_consumption(readings))
    scenarios = build_scenarios(readings)

    print(
        f"Dataset: {len(readings):,} readings, {current_rows:,} hourly rows, "
        f"{args.years} years, median of {args.repeat} runs"
    )
    print("Python calculation only; recorder I/O is represented by row counts.\n")
    print(
        f"{'Scenario':<18} {'Old ms':>10} {'New ms':>10} {'Speedup':>10} "
        f"{'Old del/upsert':>20} {'New del/upsert':>20}"
    )
    print("-" * 94)

    for scenario in scenarios:
        # Time the preserved full-history calculation used by the old workflow.
        old_ms = benchmark(
            lambda scenario=scenario: legacy_hourly_consumption(
                scenario.new_readings
            ),
            args.repeat,
        )
        # Time production's old-versus-new differential update planner.
        new_ms = benchmark(
            lambda scenario=scenario: changed_hourly_statistics(
                scenario.old_readings,
                scenario.new_readings,
                baseline,
            ),
            args.repeat,
        )
        # Calculate row counts outside the timed samples. The old workflow
        # cleared every current row and imported every row of the new history.
        new_rows = len(legacy_hourly_consumption(scenario.new_readings))
        update = changed_hourly_statistics(
            scenario.old_readings, scenario.new_readings, baseline
        )
        speedup = old_ms / new_ms
        old_operations = f"{current_rows:,}/{new_rows:,}"
        new_operations = f"{len(update.delete_starts):,}/{len(update.upsert):,}"
        print(
            f"{scenario.name:<18} {old_ms:>10.2f} {new_ms:>10.2f} "
            f"{speedup:>9.1f}x {old_operations:>20} {new_operations:>20}"
        )


if __name__ == "__main__":
    main()
