"""Pure interpolation helpers for Manual Energy Metering."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math

ONE_HOUR = timedelta(hours=1)
LATEST_READINGS_PAGE_SIZE = 10
ARCHIVE_READINGS_PAGE_SIZE = 100


class DuplicateTimestampError(ValueError):
    """Raised when moving a reading onto another existing reading."""


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
        (
            Reading(_as_utc(reading.timestamp), float(reading.value))
            for reading in readings
        ),
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


def replace_reading(
    readings: Iterable[Reading], original_timestamp: datetime, reading: Reading
) -> tuple[list[Reading], Reading]:
    """Replace one reading while preserving a unique, monotonic timeline."""
    updated, original = remove_reading(readings, original_timestamp)
    point = _as_utc(reading.timestamp)
    if point != original.timestamp and any(
        item.timestamp == point for item in updated
    ):
        raise DuplicateTimestampError(point)
    updated.append(Reading(point, float(reading.value)))
    return validate_readings(updated), original


def paginate_readings(
    readings: Sequence[Reading], requested_page: int | None = None
) -> tuple[list[Reading], int, int]:
    """Return one reverse-chronological page and its pagination metadata."""
    ordered = list(reversed(validate_readings(readings)))
    archived_count = max(0, len(ordered) - LATEST_READINGS_PAGE_SIZE)
    archive_page_count = (
        archived_count + ARCHIVE_READINGS_PAGE_SIZE - 1
    ) // ARCHIVE_READINGS_PAGE_SIZE
    page_count = archive_page_count + 1

    page = 1 if requested_page is None else requested_page
    page = min(max(page, 1), page_count)
    if page == 1:
        selected = ordered[:LATEST_READINGS_PAGE_SIZE]
    else:
        start = LATEST_READINGS_PAGE_SIZE + (
            page - 2
        ) * ARCHIVE_READINGS_PAGE_SIZE
        end = start + ARCHIVE_READINGS_PAGE_SIZE
        selected = ordered[start:end]

    return selected, page, page_count


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
            return (
                previous.value
                + (current.value - previous.value) * elapsed / duration
            )

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
