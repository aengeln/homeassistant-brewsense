"""Switch platform for BrewSense."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up BrewSense switch."""

    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([BrewSenseSwitch(coordinator, entry)])


class BrewSenseSwitch(SwitchEntity):
    """BrewSense wrapper switch."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:coffee-maker"

    def __init__(self, coordinator, entry) -> None:
        """Initialize the switch."""

        self.coordinator = coordinator

        self._attr_unique_id = f"{entry.entry_id}_switch"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": coordinator.name,
            "manufacturer": "BrewSense",
        }

    async def async_added_to_hass(self) -> None:
        """Register coordinator listener."""

        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def is_on(self) -> bool:
        """Return true if the wrapped switch is on."""

        state = self.hass.states.get(self.coordinator.switch_entity)

        if state is None:
            return False

        return state.state == "on"

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the wrapped switch."""

        domain = self.coordinator.switch_entity.split(".")[0]

        await self.hass.services.async_call(
            domain,
            "turn_on",
            {
                "entity_id": self.coordinator.switch_entity,
            },
            blocking=True,
        )

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the wrapped switch."""

        domain = self.coordinator.switch_entity.split(".")[0]

        await self.hass.services.async_call(
            domain,
            "turn_off",
            {
                "entity_id": self.coordinator.switch_entity,
            },
            blocking=True,
        )

        self.async_write_ha_state()