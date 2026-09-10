"""Export compatible Home Assistant long-term statistics as portable CSV."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
from typing import Any

from homeassistant.components.recorder.statistics import (
    async_list_statistic_ids,
    statistics_during_period,
)
from homeassistant.components.recorder.util import get_instance
from homeassistant.const import UnitOfEnergy, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    DOMAIN,
    METER_TYPE_ELECTRICITY,
    METER_TYPE_GAS,
    METER_TYPE_WATER,
    UNIT_KWH,
    UNIT_LITERS,
)
from .csv_transfer import (
    CsvStatisticsHour,
    CsvTransferError,
    MAX_METER_NAME_LENGTH,
    clamp_negative_statistics_changes,
    export_filename,
    export_statistics_csv,
)

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_ONE_HOUR = timedelta(hours=1)
_ENERGY_UNITS = frozenset(str(unit) for unit in UnitOfEnergy)
_VOLUME_UNITS = frozenset(str(unit) for unit in UnitOfVolume)
_TARGETS = {
    "energy": {
        "unit": UNIT_KWH,
        "meter_types": (METER_TYPE_ELECTRICITY, METER_TYPE_GAS),
    },
    "volume": {
        "unit": UNIT_LITERS,
        "meter_types": (METER_TYPE_GAS, METER_TYPE_WATER),
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


async def async_list_exportable_statistics(
    hass: HomeAssistant,
) -> list[dict[str, Any]]:
    """List summable energy and volume statistics outside this integration."""
    metadata_items = await async_list_statistic_ids(
        hass, statistic_type="sum"
    )
    entity_registry = er.async_get(hass)
    result: list[dict[str, Any]] = []
    for metadata in metadata_items:
        statistic_id = str(metadata.get("statistic_id", ""))
        entity_entry = entity_registry.async_get(statistic_id)
        if (
            not statistic_id
            or statistic_id.startswith(f"{DOMAIN}:")
            or (entity_entry is not None and entity_entry.platform == DOMAIN)
            or not metadata.get("has_sum")
        ):
            continue
        if (unit_class := _normalized_unit_class(metadata)) is None:
            continue
        target = _TARGETS[unit_class]
        result.append(
            {
                "statistic_id": statistic_id,
                "name": _display_name(hass, metadata),
                "source": str(metadata.get("source") or ""),
                "source_unit": str(
                    metadata.get("statistics_unit_of_measurement") or ""
                ),
                "unit_class": unit_class,
                "target_unit": target["unit"],
                "meter_types": list(target["meter_types"]),
            }
        )
    return sorted(
        result,
        key=lambda item: (item["name"].casefold(), item["statistic_id"]),
    )


async def async_export_statistic(
    hass: HomeAssistant,
    statistic_id: str,
    meter_type: str,
) -> dict[str, Any]:
    """Read every available statistics hour and return a version 2 CSV."""
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

    unit_class = metadata["unit_class"]
    target_unit = metadata["target_unit"]
    result = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        _EPOCH,
        None,
        {statistic_id},
        "hour",
        {unit_class: target_unit},
        {"change", "state", "sum"},
    )
    rows = result.get(statistic_id, [])
    statistics: list[CsvStatisticsHour] = []
    for row in rows:
        try:
            start = datetime.fromtimestamp(float(row["start"]), timezone.utc)
            change = float(row["change"])
            total = float(row["sum"])
            state_value = row.get("state")
            state = None if state_value is None else float(state_value)
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
