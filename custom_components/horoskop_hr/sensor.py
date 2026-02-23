"""Sensors for Horoskop HR."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_ATTRIBUTION, ATTR_SOURCE_URLS, DOMAIN


SENSOR_DEFS = [
    ("horoskop_dnevni_raw", "dnevni_raw", "mdi:zodiac-taurus"),
    ("horoskop_tjedni_raw", "tjedni_raw", "mdi:zodiac"),
    ("horoskop_mjesecni_raw", "mjesecni_raw", "mdi:calendar-month"),
    ("horoskop_dnevni_formatted", "dnevni_formatted", "mdi:format-text"),
    ("horoskop_tjedni_formatted", "tjedni_formatted", "mdi:format-list-bulleted"),
    ("horoskop_mjesecni_formatted", "mjesecni_formatted", "mdi:text-box-multiple"),
    ("horoskop_dnevni_translated", "dnevni_translated", "mdi:translate"),
    ("horoskop_tjedni_translated", "tjedni_translated", "mdi:translate-variant"),
    ("horoskop_mjesecni_translated", "mjesecni_translated", "mdi:translate"),
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up Horoskop HR sensors."""
    data_coordinator, translation_coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        HoroskopPayloadSensor(data_coordinator, object_id, payload_key, icon)
        for object_id, payload_key, icon in SENSOR_DEFS
    ]
    entities.append(HoroskopTranslationStatusSensor(translation_coordinator))
    async_add_entities(entities)


class HoroskopPayloadSensor(CoordinatorEntity, SensorEntity):
    """Payload sensor with short state + large attributes."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, object_id: str, payload_key: str, icon: str) -> None:
        super().__init__(coordinator)
        self._object_id = object_id
        self._payload_key = payload_key
        self._attr_unique_id = object_id
        self._attr_name = object_id
        self._attr_icon = icon

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return data.get("generated_at")

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        payload = data.get(self._payload_key)
        return {
            "data": payload,
            ATTR_SOURCE_URLS: data.get(ATTR_SOURCE_URLS, {}),
            ATTR_ATTRIBUTION: data.get(ATTR_ATTRIBUTION),
        }


class HoroskopTranslationStatusSensor(CoordinatorEntity, SensorEntity):
    """Translation status sensor."""

    _attr_has_entity_name = True
    _attr_unique_id = "horoskop_translation_status"
    _attr_name = "horoskop_translation_status"
    _attr_icon = "mdi:translate"

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return data.get("status", "idle")

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {
            "last_attempt": data.get("last_attempt"),
            "last_success": data.get("last_success"),
            "error_message": data.get("error_message"),
            "language": data.get("language"),
        }
