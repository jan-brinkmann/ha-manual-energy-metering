"""WebSocket API for the meter-reading frontend."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import config_validation as cv, entity_registry as er

from .const import (
    ATTR_STATISTIC_ID,
    ATTR_TIMESTAMP,
    ATTR_VALUE,
    CONF_CONFIG_ENTRY_ID,
    CONF_METER_TYPE,
    DOMAIN,
)
from .interpolation import paginate_readings
from .meter import ManualEnergyMetering, ReadingError

WS_LIST_READINGS = f"{DOMAIN}/readings/list"
WS_ADD_READING = f"{DOMAIN}/readings/add"
WS_UPDATE_READING = f"{DOMAIN}/readings/update"
WS_DELETE_READING = f"{DOMAIN}/readings/delete"
WS_CARD_ADD_READING = f"{DOMAIN}/card/add"
PAGE_SCHEMA = vol.All(vol.Coerce(int), vol.Range(min=1))


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register commands used by the management panel and dashboard card."""
    websocket_api.async_register_command(hass, websocket_list_readings)
    websocket_api.async_register_command(hass, websocket_add_reading)
    websocket_api.async_register_command(hass, websocket_update_reading)
    websocket_api.async_register_command(hass, websocket_delete_reading)
    websocket_api.async_register_command(hass, websocket_card_add_reading)


def _meter_for_message(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> ManualEnergyMetering | None:
    """Resolve a loaded meter and report a WebSocket error if unavailable."""
    entry = hass.config_entries.async_get_entry(msg[CONF_CONFIG_ENTRY_ID])
    if entry is None or entry.domain != DOMAIN:
        connection.send_error(
            msg["id"], "entry_not_found", "The selected meter does not exist."
        )
        return None
    if entry.state is not ConfigEntryState.LOADED:
        connection.send_error(
            msg["id"], "entry_not_loaded", "The selected meter is not loaded."
        )
        return None
    return entry.runtime_data


def _meter_payload(
    meter: ManualEnergyMetering, requested_page: int | None = None
) -> dict[str, Any]:
    """Serialize one page of readings and its pagination metadata."""
    readings, page, page_count = paginate_readings(
        meter.readings, requested_page
    )
    return {
        "name": meter.name,
        CONF_METER_TYPE: meter.meter_type,
        ATTR_STATISTIC_ID: meter.statistic_id,
        "unit": meter.unit,
        "reading_count": len(meter.readings),
        "page": page,
        "page_count": page_count,
        "is_latest_page": page == 1,
        "readings": [
            {
                ATTR_TIMESTAMP: reading.timestamp.isoformat(),
                ATTR_VALUE: reading.value,
            }
            for reading in readings
        ],
    }


def _card_payload(meter: ManualEnergyMetering) -> dict[str, Any]:
    """Serialize the latest reading for a dashboard card."""
    latest = meter.latest_reading
    return {
        "name": meter.name,
        "unit": meter.unit,
        "last_reading": latest.value if latest else None,
        "last_reading_timestamp": (
            latest.timestamp.isoformat() if latest else None
        ),
    }


def _meter_for_entity(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> ManualEnergyMetering | None:
    """Resolve a card's sensor after checking entity-level permissions."""
    entity_id = msg["entity_id"]
    if not connection.user.permissions.check_entity(entity_id, POLICY_CONTROL):
        raise Unauthorized(entity_id=entity_id)

    entity_entry = er.async_get(hass).async_get(entity_id)
    if (
        entity_entry is None
        or entity_entry.platform != DOMAIN
        or entity_entry.config_entry_id is None
    ):
        connection.send_error(
            msg["id"],
            "entity_not_found",
            "The selected meter entity does not exist.",
        )
        return None

    entry = hass.config_entries.async_get_entry(entity_entry.config_entry_id)
    if entry is None or entry.domain != DOMAIN:
        connection.send_error(
            msg["id"], "entry_not_found", "The selected meter does not exist."
        )
        return None
    if entry.state is not ConfigEntryState.LOADED:
        connection.send_error(
            msg["id"], "entry_not_loaded", "The selected meter is not loaded."
        )
        return None
    return entry.runtime_data


def _send_reading_error(
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    err: ReadingError,
) -> None:
    """Send a stable error code that the panel can localize."""
    connection.send_error(msg["id"], err.translation_key, str(err))


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_LIST_READINGS,
        vol.Required(CONF_CONFIG_ENTRY_ID): str,
        vol.Optional("page"): PAGE_SCHEMA,
    }
)
def websocket_list_readings(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return one reading page, newest timestamp first."""
    if (meter := _meter_for_message(hass, connection, msg)) is None:
        return
    connection.send_result(
        msg["id"], _meter_payload(meter, msg.get("page"))
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_ADD_READING,
        vol.Required(CONF_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_VALUE): vol.Any(int, float, str),
        vol.Required(ATTR_TIMESTAMP): str,
        vol.Optional("page"): PAGE_SCHEMA,
    }
)
@websocket_api.async_response
async def websocket_add_reading(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Add a new reading or correct one with the same timestamp."""
    if (meter := _meter_for_message(hass, connection, msg)) is None:
        return
    try:
        await meter.async_add_reading(msg[ATTR_VALUE], msg[ATTR_TIMESTAMP])
    except ReadingError as err:
        _send_reading_error(connection, msg, err)
        return
    connection.send_result(
        msg["id"], _meter_payload(meter, msg.get("page"))
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_UPDATE_READING,
        vol.Required(CONF_CONFIG_ENTRY_ID): str,
        vol.Required("original_timestamp"): str,
        vol.Required(ATTR_VALUE): vol.Any(int, float, str),
        vol.Required(ATTR_TIMESTAMP): str,
        vol.Optional("page"): PAGE_SCHEMA,
    }
)
@websocket_api.async_response
async def websocket_update_reading(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Atomically update the timestamp and value of one reading."""
    if (meter := _meter_for_message(hass, connection, msg)) is None:
        return
    try:
        await meter.async_update_reading(
            msg["original_timestamp"], msg[ATTR_VALUE], msg[ATTR_TIMESTAMP]
        )
    except ReadingError as err:
        _send_reading_error(connection, msg, err)
        return
    connection.send_result(
        msg["id"], _meter_payload(meter, msg.get("page"))
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_DELETE_READING,
        vol.Required(CONF_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_TIMESTAMP): str,
        vol.Optional("page"): PAGE_SCHEMA,
    }
)
@websocket_api.async_response
async def websocket_delete_reading(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete one reading at its exact timestamp."""
    if (meter := _meter_for_message(hass, connection, msg)) is None:
        return
    try:
        await meter.async_delete_reading(msg[ATTR_TIMESTAMP])
    except ReadingError as err:
        _send_reading_error(connection, msg, err)
        return
    connection.send_result(
        msg["id"], _meter_payload(meter, msg.get("page"))
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_CARD_ADD_READING,
        vol.Required("entity_id"): cv.entity_id,
        vol.Required(ATTR_VALUE): vol.Any(int, float, str),
        vol.Required(ATTR_TIMESTAMP): str,
    }
)
@websocket_api.async_response
async def websocket_card_add_reading(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Add a reading from a dashboard card for an authorized entity."""
    if (meter := _meter_for_entity(hass, connection, msg)) is None:
        return
    try:
        await meter.async_add_reading(msg[ATTR_VALUE], msg[ATTR_TIMESTAMP])
    except ReadingError as err:
        _send_reading_error(connection, msg, err)
        return
    connection.send_result(msg["id"], _card_payload(meter))
