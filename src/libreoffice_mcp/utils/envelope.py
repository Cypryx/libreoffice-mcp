# envelope.py - Standard response envelope and error mapping for MCP tools.
#
# Every tool returns {"success", "tool", "data", "error"} and never raises into
# the MCP layer. stdout is the MCP protocol channel, so nothing here writes to it.
from __future__ import annotations

import functools
import inspect
import json
import logging
from enum import Enum
from typing import Any, Callable

from .libreoffice import LibreOfficeError, LibreOfficeNotFound, LibreOfficeTimeout

_log = logging.getLogger("libreoffice_mcp")


class ErrorCode(str, Enum):
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_EXISTS = "FILE_EXISTS"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    PATH_NOT_ALLOWED = "PATH_NOT_ALLOWED"
    CONVERSION_FAILED = "CONVERSION_FAILED"
    CONVERSION_TIMEOUT = "CONVERSION_TIMEOUT"
    LIBREOFFICE_NOT_FOUND = "LIBREOFFICE_NOT_FOUND"
    READ_FAILED = "READ_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


def _code_str(code: ErrorCode | str) -> str:
    """Normalize ``code`` to its plain str value, rejecting unknown codes."""
    try:
        return ErrorCode(code).value
    except ValueError:
        raise ValueError(f"Unknown error code: {code!r}") from None


class ToolError(Exception):
    """Raised by tools for expected failures; carries a code and a message."""

    def __init__(self, code: ErrorCode | str, message: str) -> None:
        super().__init__(message)
        self.code: str = _code_str(code)
        self.message = message


def success(tool: str, data: dict | None = None) -> dict:
    return {"success": True, "tool": tool, "data": data, "error": None}


def failure(tool: str, code: ErrorCode | str, message: str) -> dict:
    return {
        "success": False,
        "tool": tool,
        "data": None,
        "error": {"code": _code_str(code), "message": message},
    }


def _from_exception(tool: str, exc: Exception) -> dict:
    if isinstance(exc, ToolError):
        return failure(tool, exc.code, exc.message)
    if isinstance(exc, LibreOfficeTimeout):
        return failure(tool, ErrorCode.CONVERSION_TIMEOUT, str(exc))
    if isinstance(exc, LibreOfficeNotFound):
        return failure(tool, ErrorCode.LIBREOFFICE_NOT_FOUND, str(exc))
    if isinstance(exc, LibreOfficeError):
        return failure(tool, ErrorCode.CONVERSION_FAILED, str(exc))
    if isinstance(exc, FileNotFoundError):
        return failure(tool, ErrorCode.FILE_NOT_FOUND, str(exc))
    if isinstance(exc, FileExistsError):
        return failure(tool, ErrorCode.FILE_EXISTS, str(exc))
    _log.exception("Unhandled error in tool %s", tool)  # called from inside the except block
    return failure(tool, ErrorCode.INTERNAL_ERROR, f"{type(exc).__name__}: {exc}")


def _wrap_result(tool: str, result: Any) -> dict:
    try:
        json.dumps(result)
    except Exception as exc:  # a failure to serialize must never escape into the MCP layer
        _log.error("Tool %s returned a non-serializable result: %s", tool, exc)
        return failure(
            tool,
            ErrorCode.INTERNAL_ERROR,
            f"The tool result was not JSON-serializable: {exc}",
        )
    return success(tool, result)


def tool_envelope(func: Callable | None = None, *, name: str | None = None):
    """Wrap a tool so it always returns the standard envelope.

    Usable as ``@tool_envelope`` or ``@tool_envelope(name="x")``. Only
    ``Exception`` is caught; KeyboardInterrupt, SystemExit and CancelledError
    propagate.
    """

    def decorate(fn: Callable) -> Callable:
        tool_name = name or fn.__name__

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> dict:
                try:
                    result = await fn(*args, **kwargs)
                except Exception as exc:
                    return _from_exception(tool_name, exc)
                return _wrap_result(tool_name, result)

            return async_wrapper

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> dict:
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                return _from_exception(tool_name, exc)
            return _wrap_result(tool_name, result)

        return sync_wrapper

    if func is not None:
        return decorate(func)
    return decorate
