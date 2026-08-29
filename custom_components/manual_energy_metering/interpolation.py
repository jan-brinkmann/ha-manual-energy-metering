"""Pure interpolation helpers for Manual Energy Metering."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
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


def upsert_reading(readings: Iterable[Reading], reading: Reading) -> list[Reading]:
    """Insert or replace one reading and validate the resulting timeline."""
    by_timestamp = {item.timestamp: item for item in readings}
    by_timestamp[reading.timestamp] = reading
    return validate_readings(by_timestamp.values())


def remove_reading(
    readings: Iterable[Reading], timestamp: datetime
) -> tuple[list[Reading], Reading]:
    """Remove and return the reading at an exact timestamp."""
    point = _as_utc(timestamp)
    ordered = validate_readings(readings)
    for reading in ordered:
        if reading.timestamp == point:
            return [item for item in ordered if item.timestamp != point], reading
    raise KeyError(point)


def _format_number(
    value: float, *, thousands_separator: str, decimal_separator: str
) -> str:
    """Format a reading without losing meaningful decimal places."""
    formatted = format(Decimal(str(value)), ",f")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")

    integer, separator, fraction = formatted.partition(".")
    integer = integer.replace(",", thousands_separator)
    if not separator:
        return integer
    return f"{integer}{decimal_separator}{fraction}"


def format_reading_summary(
    value: float, unit: str, timestamp: datetime, language: str
) -> str:
    """Format one reading for the German or English flow description."""
    if language == "de":
        number = _format_number(
            value, thousands_separator=".", decimal_separator=","
        )
        date_time = (
            f"{timestamp.day:02d}.{timestamp.month:02d}.{timestamp.year:04d}, "
            f"{timestamp.hour:02d}:{timestamp.minute:02d}:{timestamp.second:02d}"
        )
    else:
        number = _format_number(
            value, thousands_separator=",", decimal_separator="."
        )
        hour = timestamp.hour % 12 or 12
        period = "AM" if timestamp.hour < 12 else "PM"
        date_time = (
            f"{timestamp.month:02d}/{timestamp.day:02d}/{timestamp.year:04d}, "
            f"{hour:02d}:{timestamp.minute:02d}:{timestamp.second:02d} {period}"
        )

    return f"{number} {unit} - {date_time}"


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
