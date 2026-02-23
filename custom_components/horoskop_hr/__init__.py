"""Horoskop HR integration."""
from __future__ import annotations

import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, PLATFORMS
from .coordinator import HoroskopDataCoordinator, HoroskopTranslationCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_REFRESH = "refresh"
SERVICE_TRANSLATE = "translate"

SERVICE_SCHEMA = vol.Schema({vol.Optional("entry_id"): cv.string})


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up domain-level services."""

    def _get_entry_data(entry_id: str | None) -> tuple[HoroskopDataCoordinator, HoroskopTranslationCoordinator] | None:
        entries = hass.data.get(DOMAIN, {})
        if entry_id:
            return entries.get(entry_id)
        if len(entries) == 1:
            return next(iter(entries.values()))
        return None

    async def handle_refresh(call: ServiceCall) -> None:
        entry_data = _get_entry_data(call.data.get("entry_id"))
        if not entry_data:
            _LOGGER.warning("No Horoskop HR entry found to refresh")
            return
        data_coordinator, _ = entry_data
        await data_coordinator.async_request_refresh()

    async def handle_translate(call: ServiceCall) -> None:
        entry_data = _get_entry_data(call.data.get("entry_id"))
        if not entry_data:
            _LOGGER.warning("No Horoskop HR entry found to translate")
            return
        _, translation_coordinator = entry_data
        hass.async_create_task(translation_coordinator.async_translate())

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, handle_refresh, schema=SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_TRANSLATE, handle_translate, schema=SERVICE_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Horoskop HR from a config entry."""
    data_coordinator = HoroskopDataCoordinator(hass, entry)
    translation_coordinator = HoroskopTranslationCoordinator(hass, entry, data_coordinator)
    data_coordinator.translation_coordinator = translation_coordinator

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = (data_coordinator, translation_coordinator)

    await translation_coordinator.async_initialize()
    await data_coordinator.async_config_entry_first_refresh()
    await data_coordinator.async_setup_schedule()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    entry_data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if entry_data:
        data_coordinator, _ = entry_data
        data_coordinator.async_unload_schedule()
    if not hass.data.get(DOMAIN):
        hass.data.pop(DOMAIN, None)
    return unload_ok
