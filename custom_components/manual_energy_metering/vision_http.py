"""Authenticated HTTP upload endpoint for original meter photographs."""

from __future__ import annotations

import json
from http import HTTPStatus

from aiohttp import web

from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.components.http import KEY_HASS, KEY_HASS_USER, HomeAssistantView
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .meter import ManualEnergyMetering
from .vision import (
    ALLOWED_IMAGE_TYPES,
    MAX_VISION_IMAGE_BYTES,
    VisionError,
    async_recognize_meter,
)

VISION_RECOGNIZE_URL = f"/api/{DOMAIN}/recognize/{{entity_id}}"
_READ_CHUNK_SIZE = 64 * 1024


def _error_response(
    code: str, message: str, status: HTTPStatus
) -> web.Response:
    """Return a stable error payload that the dashboard card can localize."""
    return web.json_response(
        {"code": code, "message": message}, status=int(status)
    )


async def _stream_event(
    response: web.StreamResponse, payload: dict[str, object]
) -> None:
    """Send one compact server-sent event to the dashboard card."""
    data = json.dumps(payload, separators=(",", ":"))
    await response.write(f"data: {data}\n\n".encode("utf-8"))


class VisionRecognitionView(HomeAssistantView):
    """Accept one original image and return a recognized meter value."""

    url = VISION_RECOGNIZE_URL
    name = f"api:{DOMAIN}:recognize"
    requires_auth = True

    async def post(
        self, request: web.Request, entity_id: str
    ) -> web.StreamResponse:
        """Recognize a reading without storing the photograph or reading."""
        hass: HomeAssistant = request.app[KEY_HASS]
        user = request[KEY_HASS_USER]
        if not user.permissions.check_entity(entity_id, POLICY_CONTROL):
            raise Unauthorized(entity_id=entity_id)

        entity_entry = er.async_get(hass).async_get(entity_id)
        if (
            entity_entry is None
            or entity_entry.platform != DOMAIN
            or entity_entry.config_entry_id is None
        ):
            return _error_response(
                "entity_not_found",
                "The selected meter entity does not exist.",
                HTTPStatus.NOT_FOUND,
            )

        entry = hass.config_entries.async_get_entry(entity_entry.config_entry_id)
        if entry is None or entry.domain != DOMAIN:
            return _error_response(
                "entry_not_found",
                "The selected meter does not exist.",
                HTTPStatus.NOT_FOUND,
            )
        if entry.state is not ConfigEntryState.LOADED:
            return _error_response(
                "entry_not_loaded",
                "The selected meter is not loaded.",
                HTTPStatus.CONFLICT,
            )

        mime_type = request.content_type.lower()
        content_encoding = request.headers.get("Content-Encoding", "identity").lower()
        if (
            mime_type not in ALLOWED_IMAGE_TYPES
            or content_encoding != "identity"
        ):
            return _error_response(
                "vision_invalid_image",
                "Unsupported image format or content encoding.",
                HTTPStatus.BAD_REQUEST,
            )
        if (
            request.content_length is not None
            and request.content_length > MAX_VISION_IMAGE_BYTES
        ):
            return _error_response(
                "vision_image_too_large",
                "The image is too large.",
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )

        image = bytearray()
        async for chunk in request.content.iter_chunked(_READ_CHUNK_SIZE):
            image.extend(chunk)
            if len(image) > MAX_VISION_IMAGE_BYTES:
                return _error_response(
                    "vision_image_too_large",
                    "The image is too large.",
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                )

        meter: ManualEnergyMetering = entry.runtime_data
        stream = web.StreamResponse(
            status=HTTPStatus.OK,
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
        stream.content_type = "text/event-stream"
        stream.charset = "utf-8"
        await stream.prepare(request)

        async def send_progress(stage: str) -> None:
            await _stream_event(
                stream, {"event": "progress", "stage": stage}
            )

        try:
            result = await async_recognize_meter(
                hass,
                meter,
                bytes(image),
                mime_type,
                progress=send_progress,
            )
        except VisionError as err:
            try:
                await _stream_event(
                    stream,
                    {
                        "event": "error",
                        "code": err.code,
                        "message": str(err),
                    },
                )
            except ConnectionResetError:
                return stream
        except ConnectionResetError:
            return stream
        else:
            try:
                await _stream_event(stream, {"event": "result", **result})
            except ConnectionResetError:
                return stream

        try:
            await stream.write_eof()
        except ConnectionResetError:
            pass
        return stream
