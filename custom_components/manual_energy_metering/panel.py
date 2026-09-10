"""Frontend panel registration for Manual Energy Metering."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from homeassistant.components import panel_custom
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import CONF_RESOURCE_TYPE_WS
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.const import CONF_ID, CONF_TYPE, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN
from .csv_http import CsvImportView, CsvInspectView

PANEL_URL = f"/{DOMAIN}_static"
PANEL_COMPONENT = f"{DOMAIN.replace('_', '-')}-panel"
CARD_URL = f"{PANEL_URL}/card.js"
RESOURCE_TYPE_MODULE = "module"
_IMPORT_UI_REGISTERED = "_csv_import_ui_registered"
_CARD_RESOURCE_REGISTERED = "_card_resource_registered"


def _get_lovelace_resources(hass: HomeAssistant) -> Any:
    """Return the resource collection across supported Lovelace data layouts."""
    lovelace = hass.data["lovelace"]
    if hasattr(lovelace, "resources"):
        return lovelace.resources
    return lovelace["resources"]


async def _async_register_card_resource(
    hass: HomeAssistant, card_url: str
) -> None:
    """Register the card as a dashboard-managed Lovelace resource when possible."""
    resources = _get_lovelace_resources(hass)
    await resources.async_get_info()
    existing = next(
        (
            item
            for item in resources.async_items()
            if item.get(CONF_URL, "").partition("?")[0] == CARD_URL
        ),
        None,
    )

    if isinstance(resources, ResourceStorageCollection):
        if existing is None:
            await resources.async_create_item(
                {CONF_URL: card_url, CONF_RESOURCE_TYPE_WS: RESOURCE_TYPE_MODULE}
            )
            return

        updates: dict[str, str] = {}
        if existing.get(CONF_URL) != card_url:
            updates[CONF_URL] = card_url
        if existing.get(CONF_TYPE) != RESOURCE_TYPE_MODULE:
            updates[CONF_RESOURCE_TYPE_WS] = RESOURCE_TYPE_MODULE
        if updates:
            await resources.async_update_item(existing[CONF_ID], updates)
        return

    # YAML-managed resources cannot be changed through the collection API.
    if existing is None:
        add_extra_js_url(hass, card_url)


async def async_register_import_ui(hass: HomeAssistant) -> None:
    """Register the panel and endpoints needed by the external import step."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_IMPORT_UI_REGISTERED):
        return
    frontend_dir = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_URL, str(frontend_dir), False)]
    )
    hass.http.register_view(CsvInspectView)
    hass.http.register_view(CsvImportView)
    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path=DOMAIN,
        webcomponent_name=PANEL_COMPONENT,
        module_url=f"{PANEL_URL}/panel.js",
        require_admin=True,
        config_panel_domain=DOMAIN,
    )
    domain_data[_IMPORT_UI_REGISTERED] = True


async def async_register_readings_panel(hass: HomeAssistant) -> None:
    """Register the management panel, dashboard card, and static assets."""
    await async_register_import_ui(hass)
    domain_data = hass.data[DOMAIN]
    if domain_data.get(_CARD_RESOURCE_REGISTERED):
        return
    integration = await async_get_integration(hass, DOMAIN)
    await _async_register_card_resource(
        hass, f"{CARD_URL}?v={integration.version}"
    )
    domain_data[_CARD_RESOURCE_REGISTERED] = True
