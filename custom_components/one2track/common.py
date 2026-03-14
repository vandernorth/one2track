from datetime import timedelta
import logging

VERSION = "1.0.5"
DOMAIN = "one2track"
DEFAULT_PREFIX = "one2track"
DEFAULT_UPDATE_RATE_SEC = 30

CHECK_TIME_DELTA = timedelta(hours=1, minutes=00)

# Config keys
CONF_USER_NAME = "Username"
CONF_PASSWORD = "Password"
CONF_ID = "AccountID"

LOGGER = logging.getLogger(__package__)
