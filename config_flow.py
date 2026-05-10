

"""Config flow for the BrewSense integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_AUTO_TURN_OFF_DELAY,
    CONF_BREW_THRESHOLD,
    CONF_DRIP_DELAY,
    CONF_POWER_SENSOR,
    CONF_READY_LINGER,
    CONF_SECONDS_PER_CUP,
    CONF_SWITCH_ENTITY,
    DEFAULT_AUTO_TURN_OFF_DELAY,
    DEFAULT_BREW_THRESHOLD,
    DEFAULT_DRIP_DELAY,
    DEFAULT_NAME,
    DEFAULT_READY_LINGER,
    DEFAULT_SECONDS_PER_CUP,
    DOMAIN,
)


class BrewSenseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BrewSense."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial setup step."""

        if user_input is not None:
            return self.async_create_entry(
                title=user_input["name"],
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required("name", default=DEFAULT_NAME): selector.TextSelector(),
                vol.Required(CONF_POWER_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_SWITCH_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch")
                ),
                vol.Optional(
                    CONF_BREW_THRESHOLD,
                    default=DEFAULT_BREW_THRESHOLD,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=100,
                        max=3000,
                        step=10,
                        unit_of_measurement="W",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_SECONDS_PER_CUP,
                    default=DEFAULT_SECONDS_PER_CUP,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5,
                        max=120,
                        step=1,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_DRIP_DELAY,
                    default=DEFAULT_DRIP_DELAY,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=600,
                        step=5,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_READY_LINGER,
                    default=DEFAULT_READY_LINGER,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=7200,
                        step=60,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_AUTO_TURN_OFF_DELAY,
                    default=DEFAULT_AUTO_TURN_OFF_DELAY,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=720,
                        step=1,
                        unit_of_measurement="min",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
        )