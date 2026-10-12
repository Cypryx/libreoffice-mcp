# config.py - Environment variable loading, path resolution
#
# All user-specific configuration flows through environment variables.
# Nothing user-specific is hardcoded in the codebase.
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Names of the environment variables this server honours.
LIBREOFFICE_PATH_ENV = "LIBREOFFICE_PATH"
WORKING_DIR_ENV = "LIBREOFFICE_MCP_WORKING_DIR"
AUTHOR_NAME_ENV = "LIBREOFFICE_MCP_AUTHOR_NAME"
AUTHOR_INITIALS_ENV = "LIBREOFFICE_MCP_AUTHOR_INITIALS"
CONVERSION_TIMEOUT_ENV = "LIBREOFFICE_MCP_CONVERSION_TIMEOUT"

# Defaults per the roadmap.
DEFAULT_BINARY = "libreoffice"
DEFAULT_WORKING_DIR = "~/Documents/libreoffice-mcp"
DEFAULT_AUTHOR_NAME = "AI Assistant"
DEFAULT_AUTHOR_INITIALS = "AI"
DEFAULT_CONVERSION_TIMEOUT_SECONDS = 30


def _default_working_dir() -> Path:
    """Expand the default working dir, handling the leading ~."""
    return Path(DEFAULT_WORKING_DIR).expanduser()


@dataclass(frozen=True)
class Settings:
    """Snapshot of all runtime configuration."""

    libreoffice_path: str = DEFAULT_BINARY
    working_dir: Path = field(default_factory=_default_working_dir)
    author_name: str = DEFAULT_AUTHOR_NAME
    author_initials: str = DEFAULT_AUTHOR_INITIALS
    conversion_timeout_seconds: float = DEFAULT_CONVERSION_TIMEOUT_SECONDS

    def effective_author_name(self, override: str | None = None) -> str:
        """Return the per-call override if given, else the configured name."""
        if override:
            return override
        return self.author_name

    def effective_author_initials(self, override: str | None = None) -> str:
        if override:
            return override
        return self.author_initials


def _parse_timeout(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError:
        return float(DEFAULT_CONVERSION_TIMEOUT_SECONDS)
    if parsed <= 0:
        return float(DEFAULT_CONVERSION_TIMEOUT_SECONDS)
    return parsed


def load_settings(env: dict[str, str] | None = None) -> Settings:
    """Load settings from the environment.

    ``env`` is provided for tests; when omitted, the process environment is used.
    """
    env = env if env is not None else os.environ

    working_dir_raw = env.get(WORKING_DIR_ENV, DEFAULT_WORKING_DIR)

    return Settings(
        libreoffice_path=env.get(LIBREOFFICE_PATH_ENV, DEFAULT_BINARY),
        working_dir=Path(working_dir_raw).expanduser(),
        author_name=env.get(AUTHOR_NAME_ENV, DEFAULT_AUTHOR_NAME),
        author_initials=env.get(AUTHOR_INITIALS_ENV, DEFAULT_AUTHOR_INITIALS),
        conversion_timeout_seconds=_parse_timeout(
            env.get(CONVERSION_TIMEOUT_ENV, str(DEFAULT_CONVERSION_TIMEOUT_SECONDS))
        ),
    )


def load_env_file(path: Path) -> None:
    """Lightweight .env loader.

    Only sets variables not already present in the environment so an explicit
    export always wins over a .env file. Uses a tiny hand-rolled parser rather
    than importing python-dotenv at runtime to keep the server dependency-light
    (python-dotenv is already present for MCP, but we avoid the import cost).
    """
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value