"""Pure interpolation helpers for Manual Energy Metering."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from typing import Iterable

ONE_HOUR = timedelta(hours=1)


@dataclass(frozen=True, slots=True)
class Reading:
    """A meter reading at an exact point in time."""

    timestamp: datetime
    value: float


@dataclass(frozen=True, slots=True)
class HourlyConsumption:
    """Consumption assigned to one UTC statistics hour."""

    start: datetime
    consumption: float
    cumulative: float


def _as_utc(value: datetime) -> datetime:
    """Return an aware datetime as UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamps must include timezone information")
    return value.astimezone(timezone.utc)


def validate_readings(readings: Iterable[Reading]) -> list[Reading]:
    """Sort and validate a sequence of readings."""
    ordered = sorted(
        (Reading(_as_utc(reading.timestamp), float(reading.value)) for reading in readings),
        key=lambda reading: reading.timestamp,
    )

    previous: Reading | None = None
    for reading in ordered:
        if not math.isfinite(reading.value) or reading.value < 0:
            raise ValueError("Meter readings must be finite and non-negative")
        if previous is not None:
            if reading.timestamp == previous.timestamp:
                raise ValueError("Only one reading is allowed per timestamp")
            if reading.value < previous.value:
                raise ValueError("Meter readings must not decrease")
        previous = reading

    return ordered


def interpolate_value(readings: Iterable[Reading], at: datetime) -> float | None:
    """Interpolate the meter value at a point in time."""
    ordered = validate_readings(readings)
    if not ordered:
        return None

    point = _as_utc(at)
    if point <= ordered[0].timestamp:
        return ordered[0].value
    if point >= ordered[-1].timestamp:
        return ordered[-1].value

    for previous, current in zip(ordered, ordered[1:]):
        if point <= current.timestamp:
            duration = (current.timestamp - previous.timestamp).total_seconds()
            elapsed = (point - previous.timestamp).total_seconds()
            return previous.value + (current.value - previous.value) * elapsed / duration

    return ordered[-1].value


def hourly_consumption(readings: Iterable[Reading]) -> list[HourlyConsumption]:
    """Linearly distribute deltas over intersected UTC clock hours."""
    ordered = validate_readings(readings)
    buckets: dict[datetime, list[float]] = {}

    for previous, current in zip(ordered, ordered[1:]):
        duration = (current.timestamp - previous.timestamp).total_seconds()
        delta = current.value - previous.value
        rate = delta / duration

        bucket_start = previous.timestamp.replace(minute=0, second=0, microsecond=0)
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
