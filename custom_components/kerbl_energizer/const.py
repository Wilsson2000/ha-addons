"""Constants for Kerbl Smart Energizer."""

DOMAIN = "kerbl_energizer"
BASE_URL = "https://backend.kerbl-iot.com/api/v0.1"
SCAN_INTERVAL_SECONDS = 120

# Keys in GET /device that hold energizers. The exact key is not documented;
# the satellite list is "smartSatellite", so "smartEnergizer" is the likely one.
ENERGIZER_KEYS = ("smartEnergizer", "smartEnergizers", "smart-energizer")

CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
