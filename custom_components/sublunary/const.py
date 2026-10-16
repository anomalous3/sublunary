"""Constants for Sublunary."""

DOMAIN = "sublunary"

CONF_TICK_MINUTES = "tick_minutes"

# every definition is always computed; users enable/disable the entities
DEFINITIONS = ("modern", "traditional", "lilly", "lilly_unbounded")
DISABLED_BY_DEFAULT = ("lilly_unbounded",)
DEFAULT_TICK_MINUTES = 5

HORIZON_DAYS = 14      # timeline span ahead of now (lunar quarters are up to ~7.6 days apart)
REBUILD_MARGIN_DAYS = 4  # rebuild when this close to the horizon

PHASE_NAMES = (
    "new_moon", "waxing_crescent", "first_quarter", "waxing_gibbous",
    "full_moon", "waning_gibbous", "last_quarter", "waning_crescent",
)
