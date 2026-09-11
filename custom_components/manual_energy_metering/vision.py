"""OpenAI-compatible vision client for reading meter photographs."""

from __future__ import annotations

import asyncio
import base64
import json
import math
import re
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .meter import ManualEnergyMetering

ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
MAX_VISION_IMAGE_BYTES = 20 * 1024 * 1024
MAX_PROVIDER_RESPONSE_BYTES = 1024 * 1024
PROVIDER_CONNECT_TIMEOUT_SECONDS = 5
PROVIDER_RESPONSE_TIMEOUT_SECONDS = 90
PROVIDER_TOTAL_TIMEOUT_SECONDS = 105
_NUMBER_PATTERN = re.compile(r"^[+]?(?:\d+(?:\.\d*)?|\.\d+)$")

VisionProgressCallback = Callable[[str], Awaitable[None]]


class VisionError(RuntimeError):
    """A stable, user-facing image-recognition error."""

    def __init__(self, code: str, message: str) -> None:
        """Initialize a vision error with a localizable code."""
        super().__init__(message)
        self.code = code


def normalize_vision_url(api_url: str) -> str:
    """Add an HTTP scheme when an administrator entered only host and port."""
    normalized = api_url.strip()
    if normalized and "://" not in normalized:
        return f"http://{normalized}"
    return normalized


def chat_completions_url(api_url: str) -> str:
    """Normalize an OpenAI-compatible base URL or full endpoint."""
    normalized = api_url.strip().rstrip("/")
    parsed = urlsplit(normalized)
    try:
        _ = parsed.port
    except ValueError as err:
        raise VisionError(
            "vision_invalid_url", "Invalid vision provider URL."
        ) from err
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise VisionError("vision_invalid_url", "Invalid vision provider URL.")
    if parsed.path.rstrip("/").endswith("/chat/completions"):
        return normalized
    if parsed.path.rstrip("/").endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"


def validate_image(image: bytes, mime_type: str) -> None:
    """Reject unsupported, malformed, empty, or oversized image data."""
    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise VisionError("vision_invalid_image", "Unsupported image format.")
    if not image:
        raise VisionError("vision_invalid_image", "The image is empty.")
    if len(image) > MAX_VISION_IMAGE_BYTES:
        raise VisionError("vision_image_too_large", "The image is too large.")

    has_signature = (
        mime_type == "image/jpeg"
        and image.startswith(b"\xff\xd8\xff")
        or mime_type == "image/png"
        and image.startswith(b"\x89PNG\r\n\x1a\n")
        or mime_type == "image/webp"
        and len(image) >= 12
        and image.startswith(b"RIFF")
        and image[8:12] == b"WEBP"
    )
    if not has_signature:
        raise VisionError(
            "vision_invalid_image", "The image content does not match its format."
        )


def _response_text(response: Any) -> str:
    """Extract assistant text from an OpenAI-compatible response."""
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as err:
        raise VisionError(
            "vision_invalid_response", "The provider response has no content."
        ) from err

    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text = "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ).strip()
        if text:
            return text
    raise VisionError(
        "vision_invalid_response", "The provider response has no text content."
    )


def _json_object(text: str) -> dict[str, Any] | None:
    """Find the first JSON object even when it is wrapped in Markdown."""
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def recognized_value(response: Any) -> float:
    """Parse and validate one recognized reading from a provider response."""
    text = _response_text(response)
    result = _json_object(text)
    if result is not None:
        if result.get("error"):
            raise VisionError(
                "vision_not_recognized", "The meter value was not recognized."
            )
        raw_value = result.get("value")
    else:
        raw_value = text

    if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float, str)):
        raise VisionError(
            "vision_invalid_response", "The response contains no numeric value."
        )
    normalized = str(raw_value).strip()
    if "," in normalized and "." not in normalized:
        normalized = normalized.replace(",", ".")
    if not _NUMBER_PATTERN.fullmatch(normalized):
        raise VisionError(
            "vision_invalid_response", "The recognized value is not numeric."
        )
    value = float(normalized)
    if not math.isfinite(value) or value < 0:
        raise VisionError(
            "vision_invalid_response",
            "The recognized value must be finite and non-negative.",
        )
    return value


def recognition_request(
    model: str,
    prompt: str,
    image_base64: str,
    mime_type: str,
) -> dict[str, Any]:
    """Build an OpenAI-compatible, non-streaming vision request."""
    return {
        "model": model,
        "stream": False,
        "temperature": 0,
        "max_tokens": 128,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}"
                        },
                    },
                ],
            }
        ],
    }


async def async_recognize_meter(
    hass: HomeAssistant,
    meter: ManualEnergyMetering,
    image: bytes,
    mime_type: str,
    progress: VisionProgressCallback | None = None,
) -> dict[str, Any]:
    """Send the original meter image bytes to this meter's provider."""
    import aiohttp

    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .const import (
        CONF_VISION_API_TOKEN,
        CONF_VISION_API_URL,
        CONF_VISION_MODEL,
        CONF_VISION_PROMPT,
        DEFAULT_VISION_MODEL,
        DEFAULT_VISION_PROMPT,
    )

    validate_image(image, mime_type)
    data = meter.entry.data
    api_url = str(data.get(CONF_VISION_API_URL, "")).strip()
    model = str(data.get(CONF_VISION_MODEL, DEFAULT_VISION_MODEL)).strip()
    prompt = str(data.get(CONF_VISION_PROMPT, DEFAULT_VISION_PROMPT)).strip()
    if not api_url or not model or not prompt:
        raise VisionError(
            "vision_not_configured", "Photo recognition is not configured."
        )

    endpoint = chat_completions_url(api_url)
    headers: dict[str, str] = {}
    token = str(data.get(CONF_VISION_API_TOKEN, "")).strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    image_base64 = base64.b64encode(image).decode("ascii")
    payload = recognition_request(model, prompt, image_base64, mime_type)

    async def report_progress(stage: str) -> None:
        """Forward a recognition stage when a progress callback was supplied."""
        if progress is not None:
            await progress(stage)

    class ProgressBytesPayload(aiohttp.payload.BytesPayload):
        """Report once aiohttp has written the complete provider request body."""

        def __init__(self, value: bytes) -> None:
            """Initialize the JSON payload and its one-shot reporting state."""
            super().__init__(value, content_type="application/json")
            self._reported = False

        async def _report_sent(self) -> None:
            """Emit the request-sent stage at most once."""
            if not self._reported:
                self._reported = True
                await report_progress("request_sent")

        async def write(self, writer: Any) -> None:
            """Write the payload and report that transmission completed."""
            await super().write(writer)
            await self._report_sent()

        async def write_with_length(
            self, writer: Any, content_length: int
        ) -> None:
            """Write with aiohttp's optional length-aware payload API."""
            parent_write = getattr(super(), "write_with_length", None)
            if parent_write is None:
                await super().write(writer)
            else:
                await parent_write(writer, content_length)
            await self._report_sent()

    request_body = ProgressBytesPayload(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )

    session = async_get_clientsession(hass)
    try:
        await report_progress("connecting")
        async with session.post(
            endpoint,
            headers=headers,
            data=request_body,
            timeout=aiohttp.ClientTimeout(
                total=PROVIDER_TOTAL_TIMEOUT_SECONDS,
                connect=PROVIDER_CONNECT_TIMEOUT_SECONDS,
                sock_connect=PROVIDER_CONNECT_TIMEOUT_SECONDS,
                sock_read=PROVIDER_RESPONSE_TIMEOUT_SECONDS,
            ),
        ) as response:
            await report_progress("response_received")
            body = bytearray()
            while len(body) <= MAX_PROVIDER_RESPONSE_BYTES:
                chunk = await response.content.read(
                    min(64 * 1024, MAX_PROVIDER_RESPONSE_BYTES + 1 - len(body))
                )
                if not chunk:
                    break
                body.extend(chunk)
            if response.status < 200 or response.status >= 300:
                raise VisionError(
                    "vision_provider_error",
                    f"The vision provider returned HTTP {response.status}.",
                )
    except VisionError:
        raise
    except asyncio.TimeoutError as err:
        raise VisionError(
            "vision_provider_timeout",
            "The vision provider did not respond within the time limit.",
        ) from err
    except aiohttp.ClientError as err:
        raise VisionError(
            "vision_provider_unavailable", "The vision provider is unavailable."
        ) from err

    if len(body) > MAX_PROVIDER_RESPONSE_BYTES:
        raise VisionError(
            "vision_invalid_response", "The provider response is too large."
        )
    try:
        response_data = json.loads(bytes(body))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise VisionError(
            "vision_invalid_response", "The provider returned invalid JSON."
        ) from err
    result = {"value": recognized_value(response_data), "model": model}
    await report_progress("completed")
    return result
