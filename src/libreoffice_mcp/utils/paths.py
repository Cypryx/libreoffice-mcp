# paths.py - Path rules for tools that take file paths from an AI agent.
#
# Known limitation: a path can change between the check here and its later use
# (time-of-check/time-of-use, e.g. a symlink swapped in). No fix is attempted.
#
# Nothing here calls LibreOffice or writes to stdout.
from __future__ import annotations

from pathlib import Path

from ..config import Settings
from .envelope import ErrorCode, ToolError


def _resolved_working_dir(settings: Settings) -> Path:
    return Path(settings.working_dir).expanduser().resolve(strict=False)


def resolve_path(raw: str, settings: Settings) -> Path:
    """Return the absolute, fully resolved path for ``raw``.

    ``raw`` must be a non-empty string without NUL. A leading ``~`` is expanded
    and a relative path is joined onto the working directory. ``..`` and
    symlinks are resolved. When ``settings.restrict_to_working_dir`` is set, the
    result must be the working directory or inside it (PATH_NOT_ALLOWED
    otherwise). Creates nothing and does not check existence.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise ToolError(ErrorCode.INVALID_ARGUMENT, "Path must be a non-empty string.")
    if "\x00" in raw:
        raise ToolError(ErrorCode.INVALID_ARGUMENT, "Path must not contain a NUL character.")

    try:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = Path(settings.working_dir).expanduser() / candidate
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ToolError(ErrorCode.INVALID_ARGUMENT, f"Cannot resolve path {raw!r}: {exc}") from exc

    if settings.restrict_to_working_dir:
        allowed = _resolved_working_dir(settings)
        if not resolved.is_relative_to(allowed):
            raise ToolError(
                ErrorCode.PATH_NOT_ALLOWED,
                f"Path {resolved} is outside the allowed directory {allowed}.",
            )
    return resolved


def require_existing_file(raw: str, settings: Settings) -> Path:
    """Resolve ``raw`` and require an existing regular file.

    Missing -> FILE_NOT_FOUND; exists but is not a regular file -> INVALID_ARGUMENT.
    Creates nothing.
    """
    path = resolve_path(raw, settings)
    if not path.exists():
        raise ToolError(ErrorCode.FILE_NOT_FOUND, f"No file at {path}")
    if not path.is_file():
        raise ToolError(ErrorCode.INVALID_ARGUMENT, f"Not a regular file: {path}")
    return path


def resolve_output_file(raw: str, settings: Settings, *, overwrite: bool = False) -> Path:
    """Resolve ``raw`` as a file a tool is about to write.

    The restriction is checked first. A directory target -> INVALID_ARGUMENT; an
    existing file without ``overwrite`` -> FILE_EXISTS. Only after all checks
    pass are missing parent directories created (an OSError there ->
    INVALID_ARGUMENT). Never creates the file itself and never deletes anything.
    """
    path = resolve_path(raw, settings)
    if path.is_dir():
        raise ToolError(ErrorCode.INVALID_ARGUMENT, f"Target is a directory: {path}")
    if path.exists() and not overwrite:
        raise ToolError(ErrorCode.FILE_EXISTS, f"File already exists: {path}")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ToolError(
            ErrorCode.INVALID_ARGUMENT, f"Cannot create folder {path.parent}: {exc}"
        ) from exc
    return path


def resolve_directory(raw: str | None, settings: Settings) -> Path:
    """Resolve a directory argument.

    ``None`` returns the resolved working directory without creating it or
    requiring it to exist. Otherwise the path must exist (FILE_NOT_FOUND) and be
    a directory (INVALID_ARGUMENT). Creates nothing.
    """
    if raw is None:
        return _resolved_working_dir(settings)
    path = resolve_path(raw, settings)
    if not path.exists():
        raise ToolError(ErrorCode.FILE_NOT_FOUND, f"No directory at {path}")
    if not path.is_dir():
        raise ToolError(ErrorCode.INVALID_ARGUMENT, f"Not a directory: {path}")
    return path
