"""
Windsurf Extension Discovery
=============================

Dynamically analyzes the installed Windsurf extension.js to discover
Protobuf field numbers that may change between versions.

Ported from opencode-windsurf-auth/src/plugin/discovery.ts
"""

import logging
import os
import platform
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Default metadata field numbers (matches most common Windsurf versions)
DEFAULT_METADATA_FIELDS: dict[str, int] = {
    "api_key": 1,
    "ide_name": 2,
    "ide_version": 3,
    "extension_version": 4,
    "session_id": 5,
    "locale": 6,
}

_cached_fields: dict[str, int] | None = None


def _find_extension_file() -> Path | None:
    """Locate the Windsurf extension.js file on the current platform."""
    system = platform.system()
    home = Path.home()

    candidates = []

    if system == "Darwin":
        candidates = [
            Path("/Applications/Windsurf.app/Contents/Resources/app/extensions/windsurf/dist/extension.js"),
            home / "Applications" / "Windsurf.app" / "Contents" / "Resources" / "app" / "extensions" / "windsurf" / "dist" / "extension.js",
        ]
    elif system == "Linux":
        candidates = [
            Path("/usr/share/windsurf/resources/app/extensions/windsurf/dist/extension.js"),
            home / ".local" / "share" / "windsurf" / "resources" / "app" / "extensions" / "windsurf" / "dist" / "extension.js",
        ]
    elif system == "Windows":
        candidates = [
            Path("C:/Program Files/Windsurf/resources/app/extensions/windsurf/dist/extension.js"),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Windsurf" / "resources" / "app" / "extensions" / "windsurf" / "dist" / "extension.js",
        ]

    for path in candidates:
        if path.exists():
            return path
    return None


def _parse_metadata_fields(content: str) -> dict[str, int] | None:
    """Analyze extension.js content to find Metadata field numbers.

    Looks for protobuf field definitions in the minified code like:
    newFieldList(()=>[{no:1,name:"api_key",...},...])
    """
    # Find all field list definitions
    field_lists = re.findall(r"newFieldList\(\(\)=>\[(.+?)\]\)", content)

    for list_content in field_lists:
        # The Metadata message must contain both api_key and ide_name
        # AND must NOT contain event_name (which indicates telemetry)
        if '"api_key"' in list_content and '"ide_name"' in list_content and '"event_name"' not in list_content:
            fields = dict(DEFAULT_METADATA_FIELDS)

            for field_name in fields:
                match = re.search(rf'\{{no:(\d+),name:"{field_name}"', list_content)
                if match:
                    fields[field_name] = int(match.group(1))

            # Only return if we found at least api_key and ide_name
            if "api_key" in fields and "ide_name" in fields:
                return fields

    return None


def get_metadata_fields() -> dict[str, int]:
    """Get Metadata protobuf field mapping.

    Attempts to dynamically discover field numbers from the installed
    Windsurf extension. Falls back to defaults if discovery fails.

    Returns:
        Dict mapping field names to protobuf field numbers.
    """
    global _cached_fields

    if _cached_fields is not None:
        return _cached_fields

    try:
        ext_path = _find_extension_file()
        if ext_path:
            content = ext_path.read_text(encoding="utf-8")
            discovered = _parse_metadata_fields(content)
            if discovered:
                logger.debug(f"[WindsurfDiscovery] Discovered metadata fields: {discovered}")
                _cached_fields = discovered
                return _cached_fields
    except Exception as e:
        logger.debug(f"[WindsurfDiscovery] Failed to discover extension fields: {e}")

    # Fallback to defaults
    logger.debug("[WindsurfDiscovery] Using default metadata fields")
    _cached_fields = dict(DEFAULT_METADATA_FIELDS)
    return _cached_fields
