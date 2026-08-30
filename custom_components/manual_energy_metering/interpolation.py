"""Pure interpolation helpers for Manual Energy Metering."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
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


@dataclass(frozen=True, slots=True)
class HourlyStatisticsUpdate:
    """Minimal set of hourly statistic rows changed by a reading edit."""

    delete_starts: tuple[datetime, ...]
    upsert: tuple[HourlyConsumption, ...]


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
    timestamps = [reading.timestamp for reading in ordered]
    return _interpolate_ordered(ordered, timestamps, point)


def _interpolate_ordered(
    ordered: Sequence[Reading], timestamps: Sequence[datetime], point: datetime
) -> float:
    """Interpolate within an already validated reading sequence."""
    if point <= ordered[0].timestamp:
        return ordered[0].value
    if point >= ordered[-1].timestamp:
        return ordered[-1].value

    current_index = bisect_left(timestamps, point)
    current = ordered[current_index]
    if current.timestamp == point:
        return current.value
    previous = ordered[current_index - 1]
    duration = (current.timestamp - previous.timestamp).total_seconds()
    elapsed = (point - previous.timestamp).total_seconds()
    return previous.value + (current.value - previous.value) * elapsed / duration


def _hourly_consumption_at(
    ordered: Sequence[Reading],
    timestamps: Sequence[datetime],
    start: datetime,
    baseline_value: float,
) -> HourlyConsumption | None:
    """Calculate one hour without recalculating the surrounding history."""
    end = start + ONE_HOUR
    if len(ordered) < 2 or end <= ordered[0].timestamp:
        return None
    if start >= ordered[-1].timestamp:
        return None

    contributions: list[float] = []
    segment_index = max(0, bisect_right(timestamps, start) - 1)
    while segment_index < len(ordered) - 1:
        previous = ordered[segment_index]
        current = ordered[segment_index + 1]
        if previous.timestamp >= end:
            break
        overlap_start = max(previous.timestamp, start)
        overlap_end = min(current.timestamp, end)
        if overlap_end > overlap_start:
            duration = (current.timestamp - previous.timestamp).total_seconds()
            delta = current.value - previous.value
            seconds = (overlap_end - overlap_start).total_seconds()
            contributions.append(delta * seconds / duration)
        segment_index += 1

    if not contributions:
        return None
    consumption = math.fsum(contributions)
    cumulative_point = min(end, ordered[-1].timestamp)
    cumulative = math.fsum(
        (
            _interpolate_ordered(ordered, timestamps, cumulative_point),
            -baseline_value,
        )
    )
    return HourlyConsumption(start, consumption, cumulative)


def _range_hour_starts(start: datetime, end: datetime) -> Iterable[datetime]:
    """Yield every statistics hour touched by a time range."""
    hour_start = start.replace(minute=0, second=0, microsecond=0)
    while hour_start < end:
        yield hour_start
        hour_start += ONE_HOUR


def _range_is_covered(
    ordered: Sequence[Reading], start: datetime, end: datetime
) -> bool:
    """Return whether a range is inside a sequence's interpolation span."""
    return (
        len(ordered) >= 2
        and start >= ordered[0].timestamp
        and end <= ordered[-1].timestamp
    )


def _same_number(previous: float, current: float) -> bool:
    """Return whether two calculated values differ only by floating noise."""
    return math.isclose(
        previous,
        current,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )


def _changed_interpolation_hour_starts(
    old_ordered: Sequence[Reading],
    old_timestamps: Sequence[datetime],
    new_ordered: Sequence[Reading],
    new_timestamps: Sequence[datetime],
) -> set[datetime]:
    """Return hours touched by ranges where the piecewise curves differ."""
    breakpoints = sorted(set(old_timestamps) | set(new_timestamps))
    affected_starts: set[datetime] = set()
    for start, end in zip(breakpoints, breakpoints[1:]):
        old_covered = _range_is_covered(old_ordered, start, end)
        new_covered = _range_is_covered(new_ordered, start, end)
        if not old_covered and not new_covered:
            continue
        if old_covered and new_covered:
            old_start = _interpolate_ordered(old_ordered, old_timestamps, start)
            old_end = _interpolate_ordered(old_ordered, old_timestamps, end)
            new_start = _interpolate_ordered(new_ordered, new_timestamps, start)
            new_end = _interpolate_ordered(new_ordered, new_timestamps, end)
            if _same_number(old_start, new_start) and _same_number(
                old_end, new_end
            ):
                continue
        affected_starts.update(_range_hour_starts(start, end))
    return affected_starts


def _same_hourly_value(
    previous: HourlyConsumption, current: HourlyConsumption
) -> bool:
    """Return whether two rows are equal within floating-point noise."""
    return _same_number(
        previous.consumption, current.consumption
    ) and _same_number(previous.cumulative, current.cumulative)


def changed_hourly_statistics(
    old_readings: Iterable[Reading],
    new_readings: Iterable[Reading],
    baseline_value: float | None = None,
) -> HourlyStatisticsUpdate:
    """Return only hourly rows whose interpolated value actually changes."""
    old_ordered = validate_readings(old_readings)
    new_ordered = validate_readings(new_readings)
    if baseline_value is None:
        available = old_ordered or new_ordered
        baseline_value = available[0].value if available else 0.0
    if not math.isfinite(baseline_value):
        raise ValueError("Statistics baseline must be finite")

    old_timestamps = [reading.timestamp for reading in old_ordered]
    new_timestamps = [reading.timestamp for reading in new_ordered]
    affected_starts = _changed_interpolation_hour_starts(
        old_ordered, old_timestamps, new_ordered, new_timestamps
    )
    if not affected_starts:
        return HourlyStatisticsUpdate((), ())

    delete_starts: list[datetime] = []
    upsert: list[HourlyConsumption] = []
    for start in sorted(affected_starts):
        old_value = _hourly_consumption_at(
            old_ordered, old_timestamps, start, baseline_value
        )
        new_value = _hourly_consumption_at(
            new_ordered, new_timestamps, start, baseline_value
        )
        if old_value is not None and new_value is None:
            delete_starts.append(start)
        elif new_value is not None and (
            old_value is None or not _same_hourly_value(old_value, new_value)
        ):
            upsert.append(new_value)

    return HourlyStatisticsUpdate(tuple(delete_starts), tuple(upsert))


def hourly_consumption(
    readings: Iterable[Reading], baseline_value: float | None = None
) -> list[HourlyConsumption]:
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

    if not ordered:
        return []
    baseline = ordered[0].value if baseline_value is None else baseline_value
    if not math.isfinite(baseline):
        raise ValueError("Statistics baseline must be finite")
    timestamps = [reading.timestamp for reading in ordered]
    result: list[HourlyConsumption] = []
    for start in sorted(buckets):
        consumption = math.fsum(buckets[start])
        cumulative_point = min(start + ONE_HOUR, ordered[-1].timestamp)
        cumulative = math.fsum(
            (
                _interpolate_ordered(ordered, timestamps, cumulative_point),
                -baseline,
            )
        )
        result.append(HourlyConsumption(start, consumption, cumulative))
    return result
