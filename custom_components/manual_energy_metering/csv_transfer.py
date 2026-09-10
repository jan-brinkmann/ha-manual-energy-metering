"""Portable CSV import and export for manual meter readings."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
import io
import math
import re
from typing import Any
import unicodedata

CSV_FORMAT_VERSION = "1"
CSV_COLUMNS = (
    "format_version",
    "meter_name",
    "meter_type",
    "unit",
    "timestamp",
    "value",
)
MAX_CSV_BYTES = 20 * 1024 * 1024
MAX_CSV_READINGS = 100_000
MAX_METER_NAME_LENGTH = 255
_NUMBER_PATTERN = re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$"
)
_ALLOWED_UNITS = {
    "electricity": frozenset({"Wh", "kWh"}),
    "gas": frozenset({"kWh"}),
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
class MeterCsv:
    """Validated meter metadata and readings decoded from CSV."""

    name: str
    meter_type: str
    unit: str
    readings: tuple[CsvReading, ...]


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
    if not rows or tuple(rows[0]) != CSV_COLUMNS or len(rows) < 2:
        raise CsvTransferError(
            "csv_invalid_format", "The CSV header or metadata row is invalid."
        )

    metadata: tuple[str, str, str, str] | None = None
    readings: list[CsvReading] = []
    empty_reading_row = False
    for row in rows[1:]:
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
    return MeterCsv(name, meter_type, unit, tuple(ordered))


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


def _parse_value(value: str) -> float:
    """Parse one locale-independent, finite, non-negative meter value."""
    if not _NUMBER_PATTERN.fullmatch(value):
        raise CsvTransferError(
            "csv_invalid_value", "A CSV meter value is invalid."
        )
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0:
        raise CsvTransferError(
            "csv_invalid_value", "A CSV meter value is invalid."
        )
    return parsed
