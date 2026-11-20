"""Export manual readings and compatible long-term statistics as CSV."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
from typing import Any

from homeassistant.components.recorder.db_schema import Statistics
from homeassistant.components.recorder.statistics import (
    async_list_statistic_ids,
    statistics_during_period,
)
from homeassistant.components.recorder.util import get_instance, session_scope
from homeassistant.const import UnitOfEnergy, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from sqlalchemy import and_, func
from sqlalchemy.orm import aliased

from .const import (
    DOMAIN,
    METER_TYPE_ELECTRICITY,
    METER_TYPE_GAS,
    METER_TYPE_WATER,
    UNIT_CUBIC_METERS,
    UNIT_KWH,
    UNIT_LITERS,
)
from .csv_transfer import (
    DEFAULT_GAS_CONVERSION,
    CsvStatisticsHour,
    CsvTransferError,
    GasConversion,
    MAX_METER_NAME_LENGTH,
    clamp_negative_statistics_changes,
    convert_meter_value,
    convert_readings_unit,
    csv_unit_options,
    export_filename,
    export_meter_csv,
    export_statistics_csv,
)
from .meter import ManualEnergyMetering

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_ONE_HOUR = timedelta(hours=1)
_STATISTICS_QUERY_BATCH_SIZE = 500
_ENERGY_UNITS = frozenset(str(unit) for unit in UnitOfEnergy)
_VOLUME_UNITS = frozenset(str(unit) for unit in UnitOfVolume)
_TARGETS = {
    "energy": {
        METER_TYPE_ELECTRICITY: UNIT_KWH,
        METER_TYPE_GAS: UNIT_KWH,
    },
    "volume": {
        METER_TYPE_GAS: UNIT_CUBIC_METERS,
        METER_TYPE_WATER: UNIT_LITERS,
    },
}


def _normalized_unit_class(metadata: dict[str, Any]) -> str | None:
    """Return the supported converter class for one statistic."""
    unit_class = metadata.get("unit_class")
    unit = metadata.get("statistics_unit_of_measurement")
    if unit in _ENERGY_UNITS and unit_class in (None, "energy"):
        return "energy"
    if unit in _VOLUME_UNITS and unit_class in (None, "volume"):
        return "volume"
    return None


def _display_name(hass: HomeAssistant, metadata: dict[str, Any]) -> str:
    """Prefer the current entity name over an empty statistics name."""
    statistic_id = metadata["statistic_id"]
    state = hass.states.get(statistic_id)
    if state is not None and state.name:
        name = state.name
    else:
        name = str(metadata.get("name") or statistic_id)
    return name.strip()[:MAX_METER_NAME_LENGTH] or statistic_id[
        :MAX_METER_NAME_LENGTH
    ]


def _statistics_reading(
    start_timestamp: float | None,
    state: float | None,
    total: float | None,
) -> dict[str, Any] | None:
    """Convert one hourly statistics row into a displayable meter reading."""
    value = state if state is not None else total
    if start_timestamp is None or value is None or not math.isfinite(value):
        return None
    return {
        "timestamp": (
            datetime.fromtimestamp(start_timestamp, timezone.utc).replace(
                microsecond=0
            )
            + _ONE_HOUR
        ).isoformat(),
        "value": value,
    }


def _loaded_manual_meters(
    hass: HomeAssistant,
) -> dict[str, ManualEnergyMetering]:
    """Return loaded manual meters indexed by their external statistic ID."""
    domain_data = hass.data.get(DOMAIN, {})
    return {
        meter.statistic_id: meter
        for meter in domain_data.values()
        if isinstance(meter, ManualEnergyMetering)
    }


def _manual_meter_item(meter: ManualEnergyMetering) -> dict[str, Any]:
    """Describe a manual meter's entered readings and compatible CSV units."""
    readings = meter.readings
    first = readings[0] if readings else None
    last = readings[-1] if readings else None
    return {
        "statistic_id": meter.statistic_id,
        "name": meter.name,
        "source": DOMAIN,
        "source_unit": meter.unit,
        "unit_class": meter.unit_class,
        "target_unit": meter.unit,
        "meter_types": [meter.meter_type],
        "available_units": {
            meter.meter_type: csv_unit_options(
                meter.meter_type,
                meter.unit,
                allow_gas_conversion=meter.gas_conversion is not None,
            )
        },
        "known_meter_type": meter.meter_type,
        "export_mode": "readings",
        "first_reading": (
            {"timestamp": first.timestamp.isoformat(), "value": first.value}
            if first is not None
            else None
        ),
        "last_reading": (
            {"timestamp": last.timestamp.isoformat(), "value": last.value}
            if last is not None
            else None
        ),
        "reading_count": len(readings),
    }


def _statistics_reading_bounds(
    hass: HomeAssistant, statistic_ids: set[str]
) -> dict[str, dict[str, Any]]:
    """Fetch the oldest and newest hourly rows for many statistics efficiently."""
    if not statistic_ids:
        return {}

    with session_scope(hass=hass, read_only=True) as session:
        metadata = get_instance(hass).statistics_meta_manager.get_many(
            session, statistic_ids=statistic_ids
        )
        statistic_ids_by_metadata_id = {
            metadata_id: statistic_id
            for statistic_id, (metadata_id, _) in metadata.items()
        }
        metadata_ids = list(statistic_ids_by_metadata_id)
        result: dict[str, dict[str, Any]] = {}

        for offset in range(0, len(metadata_ids), _STATISTICS_QUERY_BATCH_SIZE):
            batch = metadata_ids[offset : offset + _STATISTICS_QUERY_BATCH_SIZE]
            bounds = (
                session.query(
                    Statistics.metadata_id.label("metadata_id"),
                    func.min(Statistics.start_ts).label("first_start"),
                    func.max(Statistics.start_ts).label("last_start"),
                    func.count(Statistics.start_ts).label("reading_count"),
                )
                .filter(Statistics.metadata_id.in_(batch))
                .group_by(Statistics.metadata_id)
                .subquery()
            )
            first_row = aliased(Statistics)
            last_row = aliased(Statistics)
            rows = (
                session.query(
                    bounds.c.metadata_id,
                    first_row.start_ts,
                    first_row.state,
                    first_row.sum,
                    last_row.start_ts,
                    last_row.state,
                    last_row.sum,
                    bounds.c.reading_count,
                )
                .select_from(bounds)
                .join(
                    first_row,
                    and_(
                        first_row.metadata_id == bounds.c.metadata_id,
                        first_row.start_ts == bounds.c.first_start,
                    ),
                )
                .join(
                    last_row,
                    and_(
                        last_row.metadata_id == bounds.c.metadata_id,
                        last_row.start_ts == bounds.c.last_start,
                    ),
                )
                .all()
            )
            for row in rows:
                statistic_id = statistic_ids_by_metadata_id[row[0]]
                result[statistic_id] = {
                    "first_reading": _statistics_reading(*row[1:4]),
                    "last_reading": _statistics_reading(*row[4:7]),
                    "reading_count": int(row[7]),
                }
        return result


async def async_list_exportable_statistics(
    hass: HomeAssistant,
) -> list[dict[str, Any]]:
    """List exportable meters with CSV unit choices ordered by preference."""
    metadata_items = await async_list_statistic_ids(
        hass, statistic_type="sum"
    )
    entity_registry = er.async_get(hass)
    manual_meters = _loaded_manual_meters(hass)
    result = [_manual_meter_item(meter) for meter in manual_meters.values()]
    for metadata in metadata_items:
        statistic_id = str(metadata.get("statistic_id", ""))
        entity_entry = entity_registry.async_get(statistic_id)
        if (
            not statistic_id
            or str(metadata.get("source") or "") == DOMAIN
            or (entity_entry is not None and entity_entry.platform == DOMAIN)
            or not metadata.get("has_sum")
        ):
            continue
        if (unit_class := _normalized_unit_class(metadata)) is None:
            continue
        target_units = _TARGETS[unit_class]
        result.append(
            {
                "statistic_id": statistic_id,
                "name": _display_name(hass, metadata),
                "source": str(metadata.get("source") or ""),
                "source_unit": str(
                    metadata.get("statistics_unit_of_measurement") or ""
                ),
                "unit_class": unit_class,
                # Older panels use this single default for the whole unit class.
                "target_unit": UNIT_KWH if unit_class == "energy" else UNIT_LITERS,
                "meter_types": list(target_units),
                "available_units": {
                    meter_type: csv_unit_options(
                        meter_type,
                        unit,
                        allow_gas_conversion=meter_type == METER_TYPE_GAS,
                    )
                    for meter_type, unit in target_units.items()
                },
                "gas_conversion": DEFAULT_GAS_CONVERSION.as_input(),
                "known_meter_type": None,
                "export_mode": "statistics",
            }
        )
    reading_bounds = await get_instance(hass).async_add_executor_job(
        _statistics_reading_bounds,
        hass,
        {
            item["statistic_id"]
            for item in result
            if item["export_mode"] == "statistics"
        },
    )
    for item in result:
        if item["export_mode"] == "readings":
            continue
        item.update(
            reading_bounds.get(
                item["statistic_id"],
                {
                    "first_reading": None,
                    "last_reading": None,
                    "reading_count": 0,
                },
            )
        )
    return sorted(
        result,
        key=lambda item: (item["name"].casefold(), item["statistic_id"]),
    )


async def async_export_statistic(
    hass: HomeAssistant,
    statistic_id: str,
    meter_type: str,
    requested_unit: str | None = None,
    *,
    gas_conversion: GasConversion | None = None,
) -> dict[str, Any]:
    """Export readings or hourly history using the meter's or caller's gas factors."""
    available = {
        item["statistic_id"]: item
        for item in await async_list_exportable_statistics(hass)
    }
    if (metadata := available.get(statistic_id)) is None:
        raise CsvTransferError(
            "statistics_not_found",
            "The selected long-term statistic is not available for export.",
        )
    if meter_type not in metadata["meter_types"]:
        raise CsvTransferError(
            "statistics_invalid_meter_type",
            "The meter type is incompatible with this statistic.",
        )
    available_units = metadata["available_units"][meter_type]
    target_unit = str(requested_unit or available_units[0]).strip()
    if target_unit not in available_units:
        raise CsvTransferError(
            "statistics_invalid_unit",
            "The selected export unit is incompatible with this meter.",
        )

    if metadata["export_mode"] == "readings":
        meter = _loaded_manual_meters(hass).get(statistic_id)
        if meter is None:
            raise CsvTransferError(
                "statistics_not_found",
                "The selected manual meter is not loaded.",
            )
        return {
            "filename": export_filename(meter.name),
            "content": export_meter_csv(
                meter.name,
                meter.meter_type,
                target_unit,
                convert_readings_unit(
                    meter.readings,
                    meter.meter_type,
                    meter.unit,
                    target_unit,
                    gas_conversion=meter.gas_conversion,
                ),
            ),
            "unit": target_unit,
            "corrected_negative_hours": [],
        }

    unit_class = metadata["unit_class"]
    default_unit = _TARGETS[unit_class][meter_type]
    recorder_unit = (
        target_unit
        if target_unit in csv_unit_options(meter_type, default_unit)
        else default_unit
    )
    factor = convert_meter_value(
        1.0,
        meter_type,
        recorder_unit,
        target_unit,
        gas_conversion=gas_conversion or DEFAULT_GAS_CONVERSION,
    )
    result = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        _EPOCH,
        None,
        {statistic_id},
        "hour",
        {unit_class: recorder_unit},
        {"change", "state", "sum"},
    )
    rows = result.get(statistic_id, [])
    statistics: list[CsvStatisticsHour] = []
    for row in rows:
        try:
            start = datetime.fromtimestamp(float(row["start"]), timezone.utc)
            change = float(row["change"]) * factor
            total = float(row["sum"]) * factor
            state_value = row.get("state")
            state = None if state_value is None else float(state_value) * factor
        except (KeyError, TypeError, ValueError, OverflowError) as err:
            raise CsvTransferError(
                "statistics_invalid_data",
                "The statistic contains an invalid hourly row.",
            ) from err
        if not all(
            math.isfinite(value)
            for value in (change, total)
            if value is not None
        ) or (state is not None and not math.isfinite(state)):
            raise CsvTransferError(
                "statistics_invalid_data",
                "The statistic contains a non-finite value.",
            )
        if state is not None and state < 0:
            raise CsvTransferError(
                "statistics_decreasing",
                "The statistic contains a negative meter state.",
            )
        statistics.append(
            CsvStatisticsHour(
                start=start,
                end=start + _ONE_HOUR,
                state=state,
                change=change,
                sum=total,
            )
        )

    statistics, corrected_changes = clamp_negative_statistics_changes(statistics)
    content = export_statistics_csv(
        metadata["name"],
        meter_type,
        target_unit,
        statistic_id,
        statistics,
    )
    return {
        "filename": export_filename(metadata["name"]),
        "content": content,
        "unit": target_unit,
        "corrected_negative_hours": [
            {"start": start.isoformat(), "value": value}
            for start, value in corrected_changes
        ],
    }
