"""Authenticated HTTP upload endpoint for original meter photographs."""

from __future__ import annotations

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
_VISION_ERROR_STATUS = {
    "vision_image_too_large": HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
    "vision_provider_error": HTTPStatus.BAD_GATEWAY,
    "vision_provider_unavailable": HTTPStatus.SERVICE_UNAVAILABLE,
    "vision_invalid_response": HTTPStatus.BAD_GATEWAY,
    "vision_not_recognized": HTTPStatus.UNPROCESSABLE_ENTITY,
}


def _error_response(
    code: str, message: str, status: HTTPStatus
) -> web.Response:
    """Return a stable error payload that the dashboard card can localize."""
    return web.json_response(
        {"code": code, "message": message}, status=int(status)
    )


class VisionRecognitionView(HomeAssistantView):
    """Accept one original image and return a recognized meter value."""

    url = VISION_RECOGNIZE_URL
    name = f"api:{DOMAIN}:recognize"
    requires_auth = True

    async def post(self, request: web.Request, entity_id: str) -> web.Response:
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
        try:
            result = await async_recognize_meter(
                hass, meter, bytes(image), mime_type
            )
        except VisionError as err:
            status = _VISION_ERROR_STATUS.get(err.code, HTTPStatus.BAD_REQUEST)
            return _error_response(err.code, str(err), status)
        return web.json_response(result)
