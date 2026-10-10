"""Konštanty integrácie Recuair."""

from datetime import timedelta

DOMAIN = "recuair"

DEFAULT_HOST = "recuair.local"
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 15

CONF_CLOUD_USERNAME = "cloud_username"
CONF_CLOUD_PASSWORD = "cloud_password"
CONF_CLOUD_DEVICE_ID = "cloud_device_id"

CLOUD_SCAN_INTERVAL = timedelta(minutes=5)

# Režimy podľa webového rozhrania jednotky (POST /setting mode=...)
MODES = ["auto", "1", "2", "3", "4", "holiday", "bypass", "off"]
PRESET_MODES = ["auto", "holiday", "bypass"]
SPEED_MODES = ["1", "2", "3", "4"]
LIGHT_MAX_INTENSITY = 5
