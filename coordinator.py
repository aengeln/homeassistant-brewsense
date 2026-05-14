"""Coordinator for the BrewSense integration."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
)
from homeassistant.helpers.storage import Store

from .const import (
    ATTR_AVERAGE_MONTHLY_CUPS,
    ATTR_COFFEE_AVAILABLE,
    ATTR_CURRENT_MONTH,
    ATTR_CURRENT_POWER,
    ATTR_LAST_BREW_CUPS,
    ATTR_LAST_BREW_DURATION,
    ATTR_LAST_BREW_FINISHED,
    ATTR_LAST_MONTH_CUPS,
    ATTR_MONTH_CUPS,
    ATTR_SESSION_CUPS,
    CONF_BREW_THRESHOLD,
    CONF_DRIP_DELAY,
    CONF_POWER_SENSOR,
    CONF_READY_LINGER,
    CONF_SECONDS_PER_CUP,
    CONF_SWITCH_ENTITY,
    DEFAULT_BREW_THRESHOLD,
    DEFAULT_DRIP_DELAY,
    DEFAULT_READY_LINGER,
    DEFAULT_SECONDS_PER_CUP,
    MINIMUM_VALID_BREW_TIME,
    STATE_BREWING,
    STATE_DRIPPING,
    STATE_OFF,
    STATE_WARMING,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1


class BrewSenseCoordinator:
    """Main runtime coordinator for BrewSense."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        """Initialize the coordinator."""

        self.hass = hass
        self.entry = entry

        self._store = Store(
            hass,
            STORAGE_VERSION,
            f"brewsense_{entry.entry_id}",
        )

        # Config
        self.name = entry.data["name"]
        self._power_sensor = entry.data[CONF_POWER_SENSOR]
        self.switch_entity = entry.data[CONF_SWITCH_ENTITY]

        self._brew_threshold = entry.data.get(
            CONF_BREW_THRESHOLD,
            DEFAULT_BREW_THRESHOLD,
        )

        self._seconds_per_cup = entry.data.get(
            CONF_SECONDS_PER_CUP,
            DEFAULT_SECONDS_PER_CUP,
        )

        self._drip_delay = entry.data.get(
            CONF_DRIP_DELAY,
            DEFAULT_DRIP_DELAY,
        )

        self._ready_linger = entry.data.get(
            CONF_READY_LINGER,
            DEFAULT_READY_LINGER,
        )


        # Runtime state
        self._state = STATE_OFF
        self._coffee_available = False
        self._current_power = 0.0

        self._brew_started_at: datetime | None = None
        self._brew_finished_at: datetime | None = None
        self._last_brew_duration = 0
        self._last_brew_finished_at: datetime | None = None
        self._dripping_ends_at: datetime | None = None

        # Statistics
        self._session_cups = 0
        self._active_brew_start_cups = 0
        self._last_brew_cups = 0
        self._month_cups = 0
        self._last_month_cups = 0
        self._monthly_history: dict[str, int] = {}
        self._current_month = self._month_key()

        # Timer unsubscribers
        self._drip_timer: Callable | None = None
        self._linger_timer: Callable | None = None
        self._brew_update_timer: Callable | None = None
        self._dripping_update_timer: Callable | None = None

        # Event unsubscribers
        self._power_listener: Callable | None = None
        self._switch_listener: Callable | None = None

        self._listeners: list[Callable[[], None]] = []

    async def async_setup(self) -> None:
        """Set up the coordinator."""

        await self._load_storage()
        self._rollover_month_if_needed()

        self._power_listener = async_track_state_change_event(
            self.hass,
            [self._power_sensor],
            self._handle_power_change,
        )
        self._switch_listener = async_track_state_change_event(
            self.hass,
            [self.switch_entity],
            self._handle_switch_change,
        )

        self._update_current_power()
        self._reconstruct_state_from_power()
        self.async_update_listeners()

        _LOGGER.debug("BrewSense coordinator initialized")

    async def async_shutdown(self) -> None:
        """Clean up the coordinator."""

        if self._power_listener:
            self._power_listener()
            self._power_listener = None

        if self._switch_listener:
            self._switch_listener()
            self._switch_listener = None

        self._cancel_timers()

    @callback
    def async_add_listener(self, update_callback: Callable[[], None]) -> Callable[[], None]:
        """Add a listener for coordinator updates."""

        self._listeners.append(update_callback)

        @callback
        def remove_listener() -> None:
            if update_callback in self._listeners:
                self._listeners.remove(update_callback)

        return remove_listener

    @callback
    def async_update_listeners(self) -> None:
        """Update all coordinator listeners."""

        for update_callback in list(self._listeners):
            update_callback()

    @callback
    def _handle_power_change(self, event) -> None:
        """Handle power sensor changes."""

        self._update_current_power()

        _LOGGER.debug(
            "Power %.1fW | State=%s | Threshold=%.1f | CoffeeAvailable=%s",
            self._current_power,
            self._state,
            self._brew_threshold,
            self._coffee_available,
        )

        # Brewing started
        if (
            self._current_power >= self._brew_threshold
            and self._state == STATE_OFF
        ):
            self._enter_brewing()
            return

        # Brewing finished
        if self._current_power < self._brew_threshold and self._state == STATE_BREWING:
            self._enter_dripping()
            return

        # Machine fully off
        if self._current_power <= 0 and self._state in (STATE_DRIPPING, STATE_WARMING):
            self._handle_machine_off()

    @callback
    def _handle_switch_change(self, event) -> None:
        """Handle switch state changes."""

        new_state = event.data.get("new_state")

        if new_state is None:
            return

        if new_state.state != "on":
            _LOGGER.debug("Switch turned off, forcing off state")
            self._handle_machine_off()

    def _update_current_power(self) -> None:
        """Update the cached current power value."""

        state = self.hass.states.get(self._power_sensor)

        try:
            self._current_power = float(state.state)
        except (TypeError, ValueError, AttributeError):
            self._current_power = 0.0

    def _reconstruct_state_from_power(self) -> None:
        """Set a sensible startup state from current power."""

        if self._current_power >= self._brew_threshold:
            _LOGGER.debug("Reconstructing active brewing state")

            self._state = STATE_BREWING
            self._coffee_available = False

            if not self._brew_started_at:
                self._brew_started_at = datetime.now()

            self._start_brew_update_timer()
            return

        if self._current_power > 0:
            self._state = STATE_WARMING
            self._coffee_available = True
            return

        self._state = STATE_OFF

    def _enter_brewing(self) -> None:
        """Enter brewing state."""

        _LOGGER.debug("Entering brewing state")

        self._cancel_timers()

        self._state = STATE_BREWING
        self._coffee_available = False
        self._brew_started_at = datetime.now()
        self._brew_finished_at = None
        self._active_brew_start_cups = self._session_cups

        self._start_brew_update_timer()
        self.async_update_listeners()

    def _enter_dripping(self) -> None:
        """Enter dripping state."""

        _LOGGER.debug("Entering dripping state")

        self._state = STATE_DRIPPING
        self._brew_finished_at = datetime.now()
        self._last_brew_finished_at = self._brew_finished_at
        self._dripping_ends_at = (
            datetime.now() + timedelta(seconds=self._drip_delay)
        )

        self._stop_brew_update_timer()

        finalized_cups = self._calculate_finalized_cups()

        if finalized_cups == 0:
            self._last_brew_cups = 0
            self._session_cups = 0
            self._state = STATE_OFF
            self.async_update_listeners()
            return

        self._last_brew_cups = finalized_cups
        self._session_cups = self._active_brew_start_cups + finalized_cups
        self._month_cups += finalized_cups
        self._monthly_history[self._current_month] = self._month_cups

        self.hass.async_create_task(self._save_storage())
        self.async_update_listeners()
        self._schedule_dripping_update()

        if self._drip_delay <= 0:
            self._enter_warming()
            return

        self._drip_timer = async_call_later(
            self.hass,
            self._drip_delay,
            self._dripping_finished,
        )

    @callback
    def _dripping_finished(self, _now) -> None:
        """Handle dripping finished."""

        self._drip_timer = None
        self._dripping_ends_at = None
        self._enter_warming()

    def _enter_warming(self) -> None:
        """Enter warming state."""

        _LOGGER.debug("Entering warming state")

        self._state = STATE_WARMING
        self._coffee_available = True
        self.async_update_listeners()


    def _handle_machine_off(self) -> None:
        """Handle machine turning off."""

        _LOGGER.debug("Machine turned off")

        self._cancel_timers()
        self._state = STATE_OFF

        if self._coffee_available and self._ready_linger > 0:
            self._linger_timer = async_call_later(
                self.hass,
                self._ready_linger,
                self._clear_coffee_available,
            )
        else:
            self._clear_coffee_available(None)

        self.async_update_listeners()

    @callback
    def _clear_coffee_available(self, _now) -> None:
        """Clear coffee available state."""

        _LOGGER.debug("Coffee availability expired")

        self._linger_timer = None
        self._coffee_available = False
        self._session_cups = 0
        self.async_update_listeners()

    def _start_brew_update_timer(self) -> None:
        """Start periodic brewing updates."""

        self._schedule_brew_update()

    def _schedule_brew_update(self) -> None:
        """Schedule next brewing update."""

        self._brew_update_timer = async_call_later(
            self.hass,
            5,
            self._brew_update,
        )

    @callback
    def _brew_update(self, _now) -> None:
        """Update live brewing cup count."""

        self._brew_update_timer = None

        if self._state != STATE_BREWING:
            return

        self._session_cups = round(
            self._active_brew_start_cups + self._calculate_live_cups(),
            1,
        )
        self.async_update_listeners()

        self._schedule_brew_update()

    def _stop_brew_update_timer(self) -> None:
        """Stop brewing update timer."""

        if self._brew_update_timer:
            self._brew_update_timer()
            self._brew_update_timer = None

    def _schedule_dripping_update(self) -> None:
        """Schedule next dripping countdown refresh."""

        self._dripping_update_timer = async_call_later(
            self.hass,
            1,
            self._dripping_update,
        )

    @callback
    def _dripping_update(self, _now) -> None:
        """Refresh dripping countdown."""

        self._dripping_update_timer = None

        if self._state != STATE_DRIPPING:
            return

        self.async_update_listeners()
        self._schedule_dripping_update()

    def _calculate_live_cups(self) -> float:
        """Calculate live cups during brewing."""

        if not self._brew_started_at:
            return 0

        duration = (datetime.now() - self._brew_started_at).total_seconds()

        return duration / self._seconds_per_cup

    def _calculate_finalized_cups(self) -> int:
        """Calculate finalized brew cups."""

        if not self._brew_started_at or not self._brew_finished_at:
            return 0

        duration = (self._brew_finished_at - self._brew_started_at).total_seconds()
        self._last_brew_duration = round(duration)

        if duration < MINIMUM_VALID_BREW_TIME:
            _LOGGER.debug("Discarding brew shorter than minimum duration")
            return 0

        cups = round(duration / self._seconds_per_cup)

        return max(1, cups)

    def _rollover_month_if_needed(self) -> None:
        """Roll monthly statistics if the month changed."""

        month_key = self._month_key()

        if month_key == self._current_month:
            return

        self._last_month_cups = self._month_cups
        self._month_cups = 0
        self._current_month = month_key
        self._monthly_history.setdefault(month_key, 0)

        self.hass.async_create_task(self._save_storage())

    @staticmethod
    def _month_key() -> str:
        """Return current month key."""

        return datetime.now().strftime("%Y-%m")

    async def _load_storage(self) -> None:
        """Load persistent statistics."""

        data = await self._store.async_load()

        if not data:
            self._monthly_history[self._current_month] = 0
            return

        self._current_month = data.get("current_month", self._current_month)
        self._month_cups = data.get("month_cups", 0)
        self._last_month_cups = data.get("last_month_cups", 0)
        self._monthly_history = data.get("monthly_history", {})
        self._last_brew_cups = data.get("last_brew_cups", 0)

    async def _save_storage(self) -> None:
        """Save persistent statistics."""

        await self._store.async_save(
            {
                "current_month": self._current_month,
                "month_cups": self._month_cups,
                "last_month_cups": self._last_month_cups,
                "monthly_history": self._monthly_history,
                "last_brew_cups": self._last_brew_cups,
            }
        )

    def _cancel_timers(self) -> None:
        """Cancel all active timers."""

        for timer_attr in [
            "_drip_timer",
            "_linger_timer",
            "_dripping_update_timer",
        ]:
            timer = getattr(self, timer_attr)
            if timer:
                timer()
                setattr(self, timer_attr, None)

        self._stop_brew_update_timer()

    @property
    def dripping_remaining(self) -> int:
        """Return remaining drip time in seconds."""

        if self._dripping_ends_at is None:
            return 0

        remaining = (
            self._dripping_ends_at - datetime.now()
        ).total_seconds()

        return max(0, round(remaining))

    @property
    def state(self) -> str:
        """Return current machine state."""

        return self._state

    @property
    def coffee_available(self) -> bool:
        """Return whether coffee is available."""

        return self._coffee_available

    @property
    def session_cups(self) -> float | int:
        """Return current session cups."""

        return self._session_cups

    @property
    def month_cups(self) -> int:
        """Return cups brewed this month."""

        self._rollover_month_if_needed()
        return self._month_cups

    @property
    def last_month_cups(self) -> int:
        """Return cups brewed last month."""

        self._rollover_month_if_needed()
        return self._last_month_cups

    @property
    def average_monthly_cups(self) -> float:
        """Return average cups per month."""

        values = [value for value in self._monthly_history.values() if value > 0]

        if not values:
            return 0

        return round(sum(values) / len(values), 1)

    @property
    def current_power(self) -> float:
        """Return current power."""

        return self._current_power

    @property
    def extra_attributes(self) -> dict:
        """Return coordinator attributes."""

        return {
            ATTR_CURRENT_POWER: self._current_power,
            ATTR_COFFEE_AVAILABLE: self._coffee_available,
            ATTR_SESSION_CUPS: self._session_cups,
            ATTR_LAST_BREW_CUPS: self._last_brew_cups,
            ATTR_LAST_BREW_DURATION: self._last_brew_duration,
            ATTR_LAST_BREW_FINISHED: self._last_brew_finished_at.isoformat()
            if self._last_brew_finished_at
            else None,
            ATTR_MONTH_CUPS: self.month_cups,
            ATTR_LAST_MONTH_CUPS: self.last_month_cups,
            ATTR_AVERAGE_MONTHLY_CUPS: self.average_monthly_cups,
            ATTR_CURRENT_MONTH: self._current_month,
        }