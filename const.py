"""Constants for the BrewSense integration."""

DOMAIN = "brewsense"

DEFAULT_NAME = "BrewSense"

# States
STATE_OFF = "off"
STATE_BREWING = "brewing"
STATE_DRIPPING = "dripping"
STATE_WARMING = "warming"

# Configuration keys
CONF_POWER_SENSOR = "power_sensor"
CONF_SWITCH_ENTITY = "switch_entity"
CONF_BREW_THRESHOLD = "brew_threshold"
CONF_SECONDS_PER_CUP = "seconds_per_cup"
CONF_DRIP_DELAY = "drip_delay"
CONF_READY_LINGER = "ready_linger"
CONF_AUTO_TURN_OFF = "auto_turn_off"
CONF_AUTO_TURN_OFF_DELAY = "auto_turn_off_delay"

# Defaults
DEFAULT_BREW_THRESHOLD = 1000
DEFAULT_SECONDS_PER_CUP = 35
DEFAULT_DRIP_DELAY = 90
DEFAULT_READY_LINGER = 900
DEFAULT_AUTO_TURN_OFF = False
DEFAULT_AUTO_TURN_OFF_DELAY = 2700

# Attributes
ATTR_CURRENT_POWER = "current_power"
ATTR_LAST_BREW_CUPS = "last_brew_cups"
ATTR_LAST_BREW_DURATION = "last_brew_duration"
ATTR_LAST_BREW_FINISHED = "last_brew_finished"
ATTR_COFFEE_AVAILABLE = "coffee_available"
ATTR_SESSION_CUPS = "session_cups"
ATTR_MONTH_CUPS = "month_cups"
ATTR_CURRENT_MONTH = "current_month"
ATTR_LAST_MONTH_CUPS = "last_month_cups"
ATTR_AVERAGE_MONTHLY_CUPS = "average_monthly_cups"

# Internal timing helpers
MINIMUM_VALID_BREW_TIME = 60
POWER_DEBOUNCE_SECONDS = 5