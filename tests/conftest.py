"""Pytest configuration for One2Track tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add the repo root to sys.path so custom_components is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Mock homeassistant and its submodules so the client package can be imported
# without a full HA installation
ha_mock = MagicMock()
sys.modules.setdefault("homeassistant", ha_mock)
sys.modules.setdefault("homeassistant.config_entries", ha_mock)
sys.modules.setdefault("homeassistant.core", ha_mock)
sys.modules.setdefault("homeassistant.const", ha_mock)
sys.modules.setdefault("homeassistant.exceptions", ha_mock)
sys.modules.setdefault("homeassistant.helpers", ha_mock)
sys.modules.setdefault("homeassistant.helpers.aiohttp_client", ha_mock)
sys.modules.setdefault("homeassistant.helpers.config_validation", ha_mock)
sys.modules.setdefault("homeassistant.helpers.device_registry", ha_mock)
sys.modules.setdefault("homeassistant.helpers.entity_platform", ha_mock)
sys.modules.setdefault("homeassistant.helpers.entity_registry", ha_mock)
sys.modules.setdefault("homeassistant.helpers.update_coordinator", ha_mock)
sys.modules.setdefault("homeassistant.components.zone", ha_mock)
sys.modules.setdefault("homeassistant.components.device_tracker", ha_mock)
sys.modules.setdefault("homeassistant.components.device_tracker.config_entry", ha_mock)
sys.modules.setdefault("homeassistant.components.sensor", ha_mock)
sys.modules.setdefault("homeassistant.components.binary_sensor", ha_mock)
sys.modules.setdefault("homeassistant.util", ha_mock)
sys.modules.setdefault("homeassistant.util.dt", ha_mock)
sys.modules.setdefault("voluptuous", MagicMock())
