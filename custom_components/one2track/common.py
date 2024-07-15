from datetime import timedelta
import logging

DOMAIN = "one2track"
DEFAULT_PREFIX = "one2track"
DEFAULT_UPDATE_RATE_MIN = 5

UPDATE_DELAY = timedelta(minutes=DEFAULT_UPDATE_RATE_MIN)
CHECK_TIME_DELTA = timedelta(hours=1, minutes=00)

# Config keys
CONF_USER_NAME = "Username"
CONF_PASSWORD = "Password"
CONF_ID = "AccountID"

LOGGER = logging.getLogger(__package__)
