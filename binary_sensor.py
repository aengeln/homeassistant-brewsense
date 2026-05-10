

"""Binary sensor platform for BrewSense."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up BrewSense binary sensors."""

    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            BrewSenseCoffeeAvailableBinarySensor(coordinator, entry),
        ]
    )


class BrewSenseCoffeeAvailableBinarySensor(BinarySensorEntity):
    """Coffee available binary sensor."""

    _attr_has_entity_name = True
    _attr_name = "Coffee available"
    _attr_icon = "mdi:coffee"

    def __init__(self, coordinator, entry) -> None:
        """Initialize the binary sensor."""

        self.coordinator = coordinator

        self._attr_unique_id = f"{entry.entry_id}_coffee_available"

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
        """Return true if coffee is available."""

        return self.coordinator.coffee_available