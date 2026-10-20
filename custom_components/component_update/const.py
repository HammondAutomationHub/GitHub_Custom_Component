"""Constants for the Component Update custom integration updater."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "component_update"

CONF_FOLDER = "folder"
CONF_REPO = "repo"
CONF_BRANCH = "branch"
CONF_TOKEN = "token"
CONF_UPDATE_MODE = "update_mode"
CONF_CHECK_INTERVAL = "check_interval"

UPDATE_MODE_MANUAL = "manual"
UPDATE_MODE_AUTOMATIC = "automatic"
UPDATE_MODES = [UPDATE_MODE_MANUAL, UPDATE_MODE_AUTOMATIC]

INTERVAL_MANUAL = "manual"
INTERVAL_HOURLY = "hourly"
INTERVAL_6H = "6h"
INTERVAL_12H = "12h"
INTERVAL_DAILY = "daily"
INTERVAL_WEEKLY = "weekly"

CHECK_INTERVALS: dict[str, timedelta | None] = {
    INTERVAL_MANUAL: None,
    INTERVAL_HOURLY: timedelta(hours=1),
    INTERVAL_6H: timedelta(hours=6),
    INTERVAL_12H: timedelta(hours=12),
    INTERVAL_DAILY: timedelta(days=1),
    INTERVAL_WEEKLY: timedelta(weeks=1),
}

SERVICE_CHECK = "check_updates"
SERVICE_INSTALL = "install_update"
SERVICE_ROLLBACK = "rollback"

CONF_VERSION = "version"
VERSION_PROMPT = "Choose a version to roll back"
HISTORY_LIMIT = 15

DEFAULT_BRANCH = "main"
GITHUB_API = "https://api.github.com"
USER_AGENT = "HomeAssistant_ComponentUpdate"
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
MAX_FILE_BYTES = 50 * 1024 * 1024

STORAGE_VERSION = 1
ISSUE_RESTART = "restart_required_{entry_id}"
NOTIFICATION_RESTART = f"{DOMAIN}_restart_{{entry_id}}"
