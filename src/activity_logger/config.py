"""Data directory resolution, config.json loading, and app-wide constants."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _data_dir() -> Path:
    """Resolve the data directory in priority order (env → portable flag → OS default)."""
    env = os.environ.get("ACTIVITY_LOGGER_HOME")
    if env:
        return Path(env)

    # Portable mode: portable.flag next to the executable (PyInstaller frozen or dev script).
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(sys.argv[0]).parent if sys.argv else Path.cwd()

    if (exe_dir / "portable.flag").exists():
        return exe_dir

    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            return Path(local) / "ActivityLogger"
        return Path.home() / "AppData" / "Local" / "ActivityLogger"

    # macOS / Linux dev fallback
    return Path.home() / "Library" / "Application Support" / "ActivityLogger"


DATA_DIR: Path = _data_dir()
DB_PATH: Path = DATA_DIR / "activity_logger.db"
LOG_DIR: Path = DATA_DIR / "logs"
REPORTS_DIR: Path = DATA_DIR / "reports"
CONFIG_PATH: Path = DATA_DIR / "config.json"

_DEFAULTS: dict = {
    "org_name": "YOUR ORGANIZATION NAME",
    "quarter_scheme": "calendar",
    "uin_pattern": r"^[A-Za-z0-9-]{4,20}$",
    "theme": "system",
}


def _ensure_dirs() -> None:
    for d in (DATA_DIR, LOG_DIR, REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def load() -> dict:
    _ensure_dirs()
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # Fill in any missing keys from defaults (forward-compat).
            for k, v in _DEFAULTS.items():
                data.setdefault(k, v)
            return data
        except (json.JSONDecodeError, OSError):
            pass
    # Write defaults on first run.
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(_DEFAULTS, f, indent=2)
    return dict(_DEFAULTS)


_cfg: dict | None = None


def get() -> dict:
    global _cfg
    if _cfg is None:
        _cfg = load()
    return _cfg
