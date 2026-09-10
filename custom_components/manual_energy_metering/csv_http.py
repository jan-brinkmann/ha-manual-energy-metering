"""Authenticated endpoints supporting the external CSV import flow."""

from __future__ import annotations

from http import HTTPStatus

from aiohttp import web

from homeassistant import data_entry_flow
from homeassistant.components.http import (
    KEY_HASS,
    KEY_HASS_USER,
    HomeAssistantView,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized

from .const import CONF_CSV_CONTENT, DOMAIN
from .csv_transfer import (
    MAX_CSV_BYTES,
    CsvTransferError,
    MeterCsv,
    decode_csv,
    parse_meter_csv,
    validate_meter_name,
)

CSV_INSPECT_URL = f"/api/{DOMAIN}/csv/inspect"
CSV_IMPORT_URL = f"/api/{DOMAIN}/csv/import"
_READ_CHUNK_SIZE = 64 * 1024


def _error_response(
    code: str, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST
) -> web.Response:
    """Return a stable error that the import page can localize."""
    return web.json_response(
        {"code": code, "message": message}, status=int(status)
    )


async def _read_csv(request: web.Request) -> tuple[str, MeterCsv]:
    """Read and validate a bounded CSV request body."""
    if (
        request.content_length is not None
        and request.content_length > MAX_CSV_BYTES
    ):
        raise CsvTransferError("csv_invalid_size", "The CSV file is too large.")
    data = bytearray()
    async for chunk in request.content.iter_chunked(_READ_CHUNK_SIZE):
        data.extend(chunk)
        if len(data) > MAX_CSV_BYTES:
            raise CsvTransferError(
                "csv_invalid_size", "The CSV file is too large."
            )
    content = decode_csv(bytes(data))
    return content, parse_meter_csv(content)


def _require_admin(request: web.Request) -> None:
    """Restrict meter creation and inspection to administrators."""
    if not request[KEY_HASS_USER].is_admin:
        raise Unauthorized()


class CsvInspectView(HomeAssistantView):
    """Validate an exported CSV and return its import summary."""

    url = CSV_INSPECT_URL
    name = f"api:{DOMAIN}:csv_inspect"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Inspect a CSV file without persisting it."""
        _require_admin(request)
        try:
            _, imported = await _read_csv(request)
        except CsvTransferError as err:
            return _error_response(err.code, str(err))
        return web.json_response(
            {
                "name": imported.name,
                "meter_type": imported.meter_type,
                "unit": imported.unit,
                "reading_count": len(imported.readings),
            }
        )


class CsvImportView(HomeAssistantView):
    """Submit a validated CSV file to a waiting external config-flow step."""

    url = CSV_IMPORT_URL
    name = f"api:{DOMAIN}:csv_import"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Validate the file and advance its Manual Energy Metering flow."""
        _require_admin(request)
        flow_id = request.query.get("flow_id", "").strip()
        try:
            name = validate_meter_name(request.query.get("name", ""))
            content, imported = await _read_csv(request)
        except CsvTransferError as err:
            return _error_response(err.code, str(err))
        if not flow_id:
            return _error_response("csv_flow_not_found", "Missing config flow ID.")

        hass: HomeAssistant = request.app[KEY_HASS]
        try:
            result = await hass.config_entries.flow.async_configure(
                flow_id,
                {"name": name, CONF_CSV_CONTENT: content},
            )
        except data_entry_flow.UnknownFlow:
            return _error_response(
                "csv_flow_not_found",
                "The CSV import flow no longer exists.",
                HTTPStatus.NOT_FOUND,
            )
        if result["type"] != data_entry_flow.FlowResultType.EXTERNAL_STEP_DONE:
            return _error_response(
                "csv_import_failed", "The CSV import flow rejected the file."
            )
        return web.json_response(
            {
                "name": name,
                "meter_type": imported.meter_type,
                "unit": imported.unit,
                "reading_count": len(imported.readings),
            }
        )
