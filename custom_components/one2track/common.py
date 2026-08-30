import logging

DOMAIN = "one2track"
DEFAULT_UPDATE_RATE_MIN = 2
MAX_UPDATE_RATE_MIN = 30
BACKOFF_MULTIPLIER = 2

# Config keys
CONF_USER_NAME = "Username"
CONF_PASSWORD = "Password"
CONF_ID = "AccountID"

LOGGER = logging.getLogger(__package__)
