"""
Settings loader for TTAB toolkit.

Reads configuration from settings.toml in the project root.
"""

import tomllib
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Resolve settings.toml relative to this file's location (src/ -> project root)
_SETTINGS_PATH = Path(__file__).parent.parent / "settings.toml"

_settings: Optional[dict] = None


def load_settings() -> dict:
    """Load settings from settings.toml. Returns cached result after first load."""
    global _settings
    if _settings is not None:
        return _settings

    if not _SETTINGS_PATH.exists():
        logger.warning(
            f"settings.toml not found at {_SETTINGS_PATH}. "
            "Copy settings-example.toml to settings.toml and fill in your API keys."
        )
        _settings = {}
        return _settings

    with open(_SETTINGS_PATH, "rb") as f:
        _settings = tomllib.load(f)

    return _settings


def get(section: str, key: str, default: Any = None) -> Any:
    """Get a value from settings by section and key."""
    settings = load_settings()
    return settings.get(section, {}).get(key, default)
