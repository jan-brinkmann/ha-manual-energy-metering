"""Portable CSV import and export for manual meter readings."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import io
import math
import re
from typing import Any
import unicodedata

CSV_FORMAT_VERSION = "1"
STATISTICS_CSV_FORMAT_VERSION = "2"
CSV_COLUMNS = (
    "format_version",
    "meter_name",
    "meter_type",
    "unit",
    "timestamp",
    "value",
)
LEGACY_STATISTICS_CSV_COLUMNS = (
    "format_version",
    "meter_name",
    "meter_type",
    "unit",
    "source_statistic_id",
    "start",
    "end",
    "state",
    "change",
    "sum",
)
STATISTICS_CSV_COLUMNS = (
    *LEGACY_STATISTICS_CSV_COLUMNS,
    "original_change",
)
MAX_CSV_BYTES = 20 * 1024 * 1024
MAX_CSV_READINGS = 100_000
MAX_METER_NAME_LENGTH = 255
ONE_HOUR = timedelta(hours=1)
_NUMBER_PATTERN = re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$"
)
_ALLOWED_UNITS = {
    "electricity": frozenset({"Wh", "kWh"}),
    "gas": frozenset({"kWh", "L"}),
    "water": frozenset({"L"}),
}


class CsvTransferError(ValueError):
    """Represent a stable CSV validation failure."""

    def __init__(self, code: str, message: str) -> None:
        """Initialize an import error with a frontend-localizable code."""
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class CsvReading:
    """One validated reading decoded from CSV."""

    timestamp: datetime
    value: float


@dataclass(frozen=True, slots=True)
class CsvStatisticsHour:
    """One hourly long-term statistic exported from Home Assistant."""

    start: datetime
    end: datetime
    state: float | None
    change: float
    sum: float
    original_change: float | None = None


@dataclass(frozen=True, slots=True)
class MeterCsv:
    """Validated meter metadata and readings decoded from CSV."""

    name: str
    meter_type: str
    unit: str
    readings: tuple[CsvReading, ...]
    format_version: str = CSV_FORMAT_VERSION
    source_statistic_id: str | None = None
    statistics: tuple[CsvStatisticsHour, ...] = ()
    excluded_hour_starts: tuple[datetime, ...] = ()


def clamp_negative_statistics_changes(
    statistics: Iterable[CsvStatisticsHour],
) -> tuple[
    tuple[CsvStatisticsHour, ...], tuple[tuple[datetime, float], ...]
]:
    """Replace negative hourly consumption and rebuild the cumulative sum."""
    normalized: list[CsvStatisticsHour] = []
    corrected_changes: list[tuple[datetime, float]] = []
    cumulative = 0.0
    for item in sorted(statistics, key=lambda entry: entry.start):
        change = float(item.change)
        original_change = item.original_change
        if not math.isfinite(change):
            raise CsvTransferError(
                "statistics_invalid_data",
                "The statistic contains a non-finite hourly change.",
            )
        if change < 0:
            corrected_changes.append((item.start, change))
            original_change = change
            change = 0.0
        cumulative = math.fsum((cumulative, change))
        normalized.append(
            CsvStatisticsHour(
                start=item.start,
                end=item.end,
                state=item.state,
                change=change,
                sum=cumulative,
                original_change=original_change,
            )
        )
    return tuple(normalized), tuple(corrected_changes)


def validate_meter_name(value: Any) -> str:
    """Return a usable meter name or raise a stable validation error."""
    name = str(value).strip()
    if not name or len(name) > MAX_METER_NAME_LENGTH:
        raise CsvTransferError("csv_invalid_name", "Invalid meter name.")
    return name


def decode_csv(data: bytes) -> str:
    """Decode a bounded UTF-8 CSV payload, accepting an optional BOM."""
    if not data or len(data) > MAX_CSV_BYTES:
        raise CsvTransferError("csv_invalid_size", "Invalid CSV file size.")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as err:
        raise CsvTransferError(
            "csv_invalid_encoding", "The CSV file is not valid UTF-8."
        ) from err


def parse_meter_csv_bytes(data: bytes) -> MeterCsv:
    """Decode and validate an exported meter CSV file."""
    return parse_meter_csv(decode_csv(data))


def parse_meter_csv(content: str) -> MeterCsv:
    """Validate CSV structure, metadata, timestamps, and monotonic values."""
    try:
        rows = [
            row
            for row in csv.reader(io.StringIO(content, newline=""), strict=True)
            if any(cell.strip() for cell in row)
        ]
    except csv.Error as err:
        raise CsvTransferError("csv_invalid_format", "Invalid CSV syntax.") from err
    if not rows or len(rows) < 2:
        raise CsvTransferError(
            "csv_invalid_format", "The CSV header or metadata row is invalid."
        )

    header = tuple(rows[0])
    if header == CSV_COLUMNS:
        return _parse_reading_rows(rows[1:])
    if header == STATISTICS_CSV_COLUMNS:
        return _parse_statistics_rows(rows[1:], has_original_change=True)
    if header == LEGACY_STATISTICS_CSV_COLUMNS:
        return _parse_statistics_rows(rows[1:], has_original_change=False)
    raise CsvTransferError(
        "csv_invalid_format", "The CSV header is not supported."
    )


def _parse_reading_rows(rows: list[list[str]]) -> MeterCsv:
    """Parse version 1 CSV rows containing original meter readings."""

    metadata: tuple[str, str, str, str] | None = None
    readings: list[CsvReading] = []
    empty_reading_row = False
    for row in rows:
        if len(row) != len(CSV_COLUMNS):
            raise CsvTransferError(
                "csv_invalid_format", "A CSV row has an invalid column count."
            )
        row_metadata = tuple(cell.strip() for cell in row[:4])
        if metadata is None:
            metadata = row_metadata
        elif row_metadata != metadata:
            raise CsvTransferError(
                "csv_inconsistent_metadata",
                "Meter metadata differs between CSV rows.",
            )

        timestamp_text = row[4].strip()
        value_text = row[5].strip()
        if not timestamp_text and not value_text:
            empty_reading_row = True
            continue
        if not timestamp_text or not value_text:
            raise CsvTransferError(
                "csv_invalid_reading", "A timestamp or meter value is missing."
            )
        if len(readings) >= MAX_CSV_READINGS:
            raise CsvTransferError(
                "csv_too_many_readings", "The CSV file contains too many readings."
            )
        readings.append(
            CsvReading(
                timestamp=_parse_timestamp(timestamp_text),
                value=_parse_value(value_text),
            )
        )

    assert metadata is not None
    version, name, meter_type, unit = metadata
    if version != CSV_FORMAT_VERSION:
        raise CsvTransferError(
            "csv_unsupported_version", "Unsupported CSV format version."
        )
    name = validate_meter_name(name)
    if meter_type not in _ALLOWED_UNITS or unit not in _ALLOWED_UNITS[meter_type]:
        raise CsvTransferError(
            "csv_invalid_meter", "The meter type and unit are incompatible."
        )
    if empty_reading_row and readings:
        raise CsvTransferError(
            "csv_invalid_reading", "An empty reading row is mixed with readings."
        )

    ordered = sorted(readings, key=lambda reading: reading.timestamp)
    previous: CsvReading | None = None
    for reading in ordered:
        if previous is not None:
            if reading.timestamp == previous.timestamp:
                raise CsvTransferError(
                    "csv_duplicate_timestamp",
                    "Only one reading is allowed per timestamp.",
                )
            if reading.value < previous.value:
                raise CsvTransferError(
                    "csv_non_monotonic",
                    "Meter readings must not decrease.",
                )
        previous = reading
    return MeterCsv(
        name,
        meter_type,
        unit,
        tuple(ordered),
        format_version=CSV_FORMAT_VERSION,
    )


def _parse_statistics_rows(
    rows: list[list[str]], *, has_original_change: bool
) -> MeterCsv:
    """Parse version 2 rows and derive a monotonic synthetic meter timeline."""
    expected_columns = (
        STATISTICS_CSV_COLUMNS
        if has_original_change
        else LEGACY_STATISTICS_CSV_COLUMNS
    )
    metadata: tuple[str, str, str, str, str] | None = None
    statistics: list[CsvStatisticsHour] = []
    for row in rows:
        if len(row) != len(expected_columns):
            raise CsvTransferError(
                "csv_invalid_format", "A CSV row has an invalid column count."
            )
        row_metadata = tuple(cell.strip() for cell in row[:5])
        if metadata is None:
            metadata = row_metadata
        elif row_metadata != metadata:
            raise CsvTransferError(
                "csv_inconsistent_metadata",
                "Meter metadata differs between CSV rows.",
            )
        if len(statistics) >= MAX_CSV_READINGS:
            raise CsvTransferError(
                "csv_too_many_readings", "The CSV file contains too many hours."
            )

        start = _parse_timestamp(row[5].strip())
        end = _parse_timestamp(row[6].strip())
        if (
            start.minute
            or start.second
            or start.microsecond
            or end != start + ONE_HOUR
        ):
            raise CsvTransferError(
                "csv_invalid_timestamp",
                "Statistics rows must describe one complete UTC hour.",
            )
        state_text = row[7].strip()
        change = _parse_value(row[8].strip())
        original_change_text = row[10].strip() if has_original_change else ""
        original_change = (
            _parse_finite_number(original_change_text)
            if original_change_text
            else None
        )
        if original_change is not None and (
            original_change >= 0 or change != 0
        ):
            raise CsvTransferError(
                "csv_invalid_value",
                "An original hourly change must be negative and replace a zero.",
            )
        statistics.append(
            CsvStatisticsHour(
                start=start,
                end=end,
                state=_parse_value(state_text) if state_text else None,
                change=change,
                sum=_parse_finite_number(row[9].strip()),
                original_change=original_change,
            )
        )

    assert metadata is not None
    version, name, meter_type, unit, source_statistic_id = metadata
    if version != STATISTICS_CSV_FORMAT_VERSION:
        raise CsvTransferError(
            "csv_unsupported_version", "Unsupported CSV format version."
        )
    name = validate_meter_name(name)
    if meter_type not in _ALLOWED_UNITS or unit not in _ALLOWED_UNITS[meter_type]:
        raise CsvTransferError(
            "csv_invalid_meter", "The meter type and unit are incompatible."
        )
    if not source_statistic_id or len(source_statistic_id) > 255:
        raise CsvTransferError(
            "csv_invalid_format", "The source statistic ID is invalid."
        )

    ordered = sorted(statistics, key=lambda item: item.start)
    excluded_hour_starts: list[datetime] = []
    previous: CsvStatisticsHour | None = None
    for item in ordered:
        if previous is not None:
            if item.start < previous.end:
                code = (
                    "csv_duplicate_timestamp"
                    if item.start == previous.start
                    else "csv_invalid_timestamp"
                )
                raise CsvTransferError(code, "Statistics hours overlap.")
            gap_start = previous.end
            gap_hours = int(
                (item.start - gap_start).total_seconds()
                // ONE_HOUR.total_seconds()
            )
            if (
                len(ordered) + len(excluded_hour_starts) + gap_hours
                > MAX_CSV_READINGS
            ):
                raise CsvTransferError(
                    "csv_too_many_readings",
                    "The statistics timeline contains too many hours.",
                )
            while gap_start < item.start:
                excluded_hour_starts.append(gap_start)
                gap_start += ONE_HOUR
        previous = item

    total_change = math.fsum(item.change for item in ordered)
    last_state = ordered[-1].state
    baseline = 0.0
    if last_state is not None:
        candidate = last_state - total_change
        if candidate >= -1e-9:
            baseline = max(0.0, candidate)

    readings_by_timestamp: dict[datetime, float] = {
        ordered[0].start: baseline
    }
    cumulative = baseline
    previous_end = ordered[0].start
    for item in ordered:
        if item.start > previous_end:
            readings_by_timestamp[item.start] = cumulative
        cumulative = math.fsum((cumulative, item.change))
        readings_by_timestamp[item.end] = cumulative
        previous_end = item.end

    readings = tuple(
        CsvReading(timestamp, value)
        for timestamp, value in sorted(readings_by_timestamp.items())
    )
    return MeterCsv(
        name,
        meter_type,
        unit,
        readings,
        format_version=STATISTICS_CSV_FORMAT_VERSION,
        source_statistic_id=source_statistic_id,
        statistics=tuple(ordered),
        excluded_hour_starts=tuple(excluded_hour_starts),
    )


def export_meter_csv(
    name: str,
    meter_type: str,
    unit: str,
    readings: Iterable[Any],
) -> str:
    """Serialize all original readings in a stable, spreadsheet-friendly CSV."""
    validated_name = validate_meter_name(name)
    if meter_type not in _ALLOWED_UNITS or unit not in _ALLOWED_UNITS[meter_type]:
        raise CsvTransferError(
            "csv_invalid_meter", "The meter type and unit are incompatible."
        )
    items = list(readings)
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    if not items:
        writer.writerow(
            (CSV_FORMAT_VERSION, validated_name, meter_type, unit, "", "")
        )
    else:
        for reading in items:
            timestamp = reading.timestamp
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise CsvTransferError(
                    "csv_invalid_reading", "A timestamp has no timezone."
                )
            writer.writerow(
                (
                    CSV_FORMAT_VERSION,
                    validated_name,
                    meter_type,
                    unit,
                    timestamp.astimezone(timezone.utc).isoformat(),
                    repr(float(reading.value)),
                )
            )
    return "\ufeff" + output.getvalue()


def export_statistics_csv(
    name: str,
    meter_type: str,
    unit: str,
    source_statistic_id: str,
    statistics: Iterable[CsvStatisticsHour],
) -> str:
    """Serialize hourly long-term statistics without inventing missing hours."""
    validated_name = validate_meter_name(name)
    if meter_type not in _ALLOWED_UNITS or unit not in _ALLOWED_UNITS[meter_type]:
        raise CsvTransferError(
            "csv_invalid_meter", "The meter type and unit are incompatible."
        )
    source_statistic_id = source_statistic_id.strip()
    if not source_statistic_id or len(source_statistic_id) > 255:
        raise CsvTransferError(
            "csv_invalid_format", "The source statistic ID is invalid."
        )
    items = sorted(statistics, key=lambda item: item.start)
    if not items:
        raise CsvTransferError(
            "statistics_empty", "The selected statistic has no hourly data."
        )
    if len(items) > MAX_CSV_READINGS:
        raise CsvTransferError(
            "csv_too_many_readings", "The statistic contains too many hours."
        )

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(STATISTICS_CSV_COLUMNS)
    previous_end: datetime | None = None
    timeline_hours = 0
    for item in items:
        start = _as_utc_hour(item.start)
        end = _as_utc(item.end)
        if end != start + ONE_HOUR or (
            previous_end is not None and start < previous_end
        ):
            raise CsvTransferError(
                "csv_invalid_timestamp", "Statistics hours overlap or are invalid."
            )
        if previous_end is not None:
            timeline_hours += int(
                (start - previous_end).total_seconds()
                // ONE_HOUR.total_seconds()
            )
        timeline_hours += 1
        if timeline_hours > MAX_CSV_READINGS:
            raise CsvTransferError(
                "csv_too_many_readings",
                "The statistics timeline contains too many hours.",
            )
        state = "" if item.state is None else repr(_validated_value(item.state))
        change = _validated_value(item.change)
        total = _parse_finite_number(repr(float(item.sum)))
        original_change = ""
        if item.original_change is not None:
            parsed_original_change = _parse_finite_number(
                repr(float(item.original_change))
            )
            if parsed_original_change >= 0 or change != 0:
                raise CsvTransferError(
                    "csv_invalid_value",
                    "An original hourly change must be negative and replace a zero.",
                )
            original_change = repr(parsed_original_change)
        writer.writerow(
            (
                STATISTICS_CSV_FORMAT_VERSION,
                validated_name,
                meter_type,
                unit,
                source_statistic_id,
                start.isoformat(),
                end.isoformat(),
                state,
                repr(change),
                repr(total),
                original_change,
            )
        )
        previous_end = end

    content = "\ufeff" + output.getvalue()
    if len(content.encode("utf-8")) > MAX_CSV_BYTES:
        raise CsvTransferError("csv_invalid_size", "The CSV file is too large.")
    return content


def export_filename(name: str) -> str:
    """Return a portable filename without losing the name inside the CSV."""
    ascii_name = (
        unicodedata.normalize("NFKD", validate_meter_name(name))
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-") or "meter"
    return f"manual-energy-metering-{slug}.csv"


def _parse_timestamp(value: str) -> datetime:
    """Parse an ISO timestamp and normalize it to UTC."""
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError as err:
        raise CsvTransferError(
            "csv_invalid_timestamp", "A CSV timestamp is invalid."
        ) from err
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise CsvTransferError(
            "csv_invalid_timestamp", "CSV timestamps must include a timezone."
        )
    return timestamp.astimezone(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Normalize one aware timestamp to UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise CsvTransferError(
            "csv_invalid_timestamp", "CSV timestamps must include a timezone."
        )
    return value.astimezone(timezone.utc)


def _as_utc_hour(value: datetime) -> datetime:
    """Normalize and validate the beginning of one UTC statistics hour."""
    timestamp = _as_utc(value)
    if timestamp.minute or timestamp.second or timestamp.microsecond:
        raise CsvTransferError(
            "csv_invalid_timestamp", "Statistics must start at a full UTC hour."
        )
    return timestamp


def _parse_value(value: str) -> float:
    """Parse one locale-independent, finite, non-negative meter value."""
    parsed = _parse_finite_number(value)
    if parsed < 0:
        raise CsvTransferError(
            "csv_invalid_value", "A CSV meter value is invalid."
        )
    return parsed


def _parse_finite_number(value: str) -> float:
    """Parse one locale-independent finite number."""
    if not _NUMBER_PATTERN.fullmatch(value):
        raise CsvTransferError(
            "csv_invalid_value", "A CSV meter value is invalid."
        )
    parsed = float(value)
    if not math.isfinite(parsed):
        raise CsvTransferError(
            "csv_invalid_value", "A CSV meter value is invalid."
        )
    return parsed


def _validated_value(value: float) -> float:
    """Validate a programmatically supplied non-negative statistic value."""
    return _parse_value(repr(float(value)))
