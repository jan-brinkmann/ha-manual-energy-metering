"""Frontend panel registration for Manual Energy Metering."""

from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PANEL_URL = f"/{DOMAIN}_static"
PANEL_COMPONENT = f"{DOMAIN.replace('_', '-')}-panel"


async def async_register_readings_panel(hass: HomeAssistant) -> None:
    """Register the integration configuration panel and its static assets."""
    frontend_dir = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_URL, str(frontend_dir), False)]
    )
    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path=DOMAIN,
        webcomponent_name=PANEL_COMPONENT,
        module_url=f"{PANEL_URL}/panel.js",
        require_admin=True,
        config_panel_domain=DOMAIN,
    )
