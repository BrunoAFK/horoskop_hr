"""Constants for Horoskop HR."""

DOMAIN = "horoskop_hr"
PLATFORMS = ["sensor"]

DEFAULT_UPDATE_INTERVAL = 3600
DEFAULT_USE_SCHEDULED_REFRESH = True
DEFAULT_SCHEDULED_TIMES = "00:00,08:00"
DEFAULT_TRANSLATION_ENABLED = False
DEFAULT_TRANSLATION_LANGUAGE = "en"
DEFAULT_TRANSLATION_AI_TASK_ENTITY = None

BASE_URL = "https://ehoroskop.net"

SIGNS: dict[str, str] = {
    "ovan": "Ovan",
    "bik": "Bik",
    "blizanci": "Blizanci",
    "rak": "Rak",
    "lav": "Lav",
    "djevica": "Djevica",
    "vaga": "Vaga",
    "skorpion": "Skorpion",
    "strijelac": "Strijelac",
    "jarac": "Jarac",
    "vodenjak": "Vodenjak",
    "ribe": "Ribe",
}

ATTR_ATTRIBUTION = "attribution"
ATTR_SOURCE_URLS = "source_urls"
