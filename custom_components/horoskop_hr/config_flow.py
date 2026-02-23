"""Config flow for Horoskop HR."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DEFAULT_SCHEDULED_TIMES,
    DEFAULT_TRANSLATION_AI_TASK_ENTITY,
    DEFAULT_TRANSLATION_ENABLED,
    DEFAULT_TRANSLATION_LANGUAGE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_USE_SCHEDULED_REFRESH,
    DOMAIN,
)


class HoroskopHrConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Horoskop HR."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Create a single instance with sane defaults."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(
            title="Horoskop HR",
            data={},
            options={
                "update_interval": DEFAULT_UPDATE_INTERVAL,
                "use_scheduled_refresh": DEFAULT_USE_SCHEDULED_REFRESH,
                "scheduled_times": DEFAULT_SCHEDULED_TIMES,
                "translation_enabled": DEFAULT_TRANSLATION_ENABLED,
                "translation_language": DEFAULT_TRANSLATION_LANGUAGE,
                "translation_ai_task_entity": DEFAULT_TRANSLATION_AI_TASK_ENTITY,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HoroskopHrOptionsFlow()


class HoroskopHrOptionsFlow(config_entries.OptionsFlowWithReload):
    """Handle options for Horoskop HR."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opt = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required("update_interval", default=opt.get("update_interval", DEFAULT_UPDATE_INTERVAL)): vol.All(
                    vol.Coerce(int), vol.Range(min=300, max=86400)
                ),
                vol.Required(
                    "use_scheduled_refresh",
                    default=opt.get("use_scheduled_refresh", DEFAULT_USE_SCHEDULED_REFRESH),
                ): bool,
                vol.Required(
                    "scheduled_times",
                    default=opt.get("scheduled_times", DEFAULT_SCHEDULED_TIMES),
                ): str,
                vol.Required(
                    "translation_enabled",
                    default=opt.get("translation_enabled", DEFAULT_TRANSLATION_ENABLED),
                ): bool,
                vol.Required(
                    "translation_language",
                    default=opt.get("translation_language", DEFAULT_TRANSLATION_LANGUAGE),
                ): selector.LanguageSelector(),
                vol.Optional(
                    "translation_ai_task_entity",
                    default=opt.get("translation_ai_task_entity", DEFAULT_TRANSLATION_AI_TASK_ENTITY),
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="ai_task")),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
