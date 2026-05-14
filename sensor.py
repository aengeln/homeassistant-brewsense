

"""Sensor platform for BrewSense."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up BrewSense sensors."""

    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            BrewSenseStateSensor(coordinator, entry),
            BrewSenseSessionCupsSensor(coordinator, entry),
            BrewSenseMonthCupsSensor(coordinator, entry),
            BrewSenseLastMonthCupsSensor(coordinator, entry),
            BrewSenseAverageMonthlyCupsSensor(coordinator, entry),
        ]
    )


class BrewSenseBaseSensor(SensorEntity):
    """Base BrewSense sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, key: str, name: str | None) -> None:
        """Initialize the sensor."""

        self.coordinator = coordinator

        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name

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


class BrewSenseStateSensor(BrewSenseBaseSensor):
    """Main BrewSense state sensor."""

    _attr_icon = "mdi:coffee-maker"

    def __init__(self, coordinator, entry) -> None:
        """Initialize the sensor."""

        super().__init__(coordinator, entry, "state", "State")

    @property
    def native_value(self):
        """Return current state."""

        return self.coordinator.state

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""

        return self.coordinator.extra_attributes


class BrewSenseSessionCupsSensor(BrewSenseBaseSensor):
    """Session cups sensor."""

    _attr_icon = "mdi:coffee"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry) -> None:
        """Initialize the sensor."""

        super().__init__(
            coordinator,
            entry,
            "session_cups",
            "Session cups",
        )

    @property
    def native_value(self):
        """Return current session cups."""

        return self.coordinator.session_cups


class BrewSenseMonthCupsSensor(BrewSenseBaseSensor):
    """Current month cups sensor."""

    _attr_icon = "mdi:calendar-month"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, entry) -> None:
        """Initialize the sensor."""

        super().__init__(
            coordinator,
            entry,
            "month_cups",
            "Cups this month",
        )

    @property
    def native_value(self):
        """Return current month cups."""

        return self.coordinator.month_cups


class BrewSenseLastMonthCupsSensor(BrewSenseBaseSensor):
    """Last month cups sensor."""

    _attr_icon = "mdi:calendar-arrow-left"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry) -> None:
        """Initialize the sensor."""

        super().__init__(
            coordinator,
            entry,
            "last_month_cups",
            "Cups last month",
        )

    @property
    def native_value(self):
        """Return last month cups."""

        return self.coordinator.last_month_cups


class BrewSenseAverageMonthlyCupsSensor(BrewSenseBaseSensor):
    """Average monthly cups sensor."""

    _attr_icon = "mdi:chart-line"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry) -> None:
        """Initialize the sensor."""

        super().__init__(
            coordinator,
            entry,
            "average_monthly_cups",
            "Average cups per month",
        )

    @property
    def native_value(self):
        """Return average monthly cups."""

        return self.coordinator.average_monthly_cups