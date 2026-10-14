from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path

import pytest

from libreoffice_mcp.utils.envelope import (
    ErrorCode,
    ToolError,
    failure,
    success,
    tool_envelope,
)
from libreoffice_mcp.utils.libreoffice import (
    LibreOfficeError,
    LibreOfficeNotFound,
    LibreOfficeTimeout,
)


def run_sync(exc: BaseException) -> dict:
    @tool_envelope
    def tool() -> dict:
        raise exc

    return tool()


def run_async(exc: BaseException) -> dict:
    @tool_envelope
    async def tool() -> dict:
        raise exc

    return asyncio.run(tool())


RUNNERS = [run_sync, run_async]

MAPPING = [
    (ToolError(ErrorCode.PATH_NOT_ALLOWED, "nope"), "PATH_NOT_ALLOWED", "nope"),
    (ToolError("READ_FAILED", "bad read"), "READ_FAILED", "bad read"),
    (LibreOfficeTimeout("slow"), "CONVERSION_TIMEOUT", "slow"),
    (LibreOfficeNotFound("missing"), "LIBREOFFICE_NOT_FOUND", "missing"),
    (LibreOfficeError("broke"), "CONVERSION_FAILED", "broke"),
    (FileNotFoundError("a.docx"), "FILE_NOT_FOUND", "a.docx"),
    (FileExistsError("b.docx"), "FILE_EXISTS", "b.docx"),
]


def test_success_shape():
    assert success("t", {"a": 1}) == {
        "success": True, "tool": "t", "data": {"a": 1}, "error": None,
    }
    assert success("t")["data"] is None


def test_failure_shape_and_plain_str_code():
    out = failure("t", ErrorCode.FILE_NOT_FOUND, "msg")
    assert out == {
        "success": False, "tool": "t", "data": None,
        "error": {"code": "FILE_NOT_FOUND", "message": "msg"},
    }
    assert type(out["error"]["code"]) is str
    assert type(failure("t", "READ_FAILED", "m")["error"]["code"]) is str


def test_error_code_values_equal_names():
    assert len(ErrorCode) == 10
    for member in ErrorCode:
        assert member.value == member.name


def test_tool_error_unknown_code_raises():
    with pytest.raises(ValueError):
        ToolError("NOT_A_CODE", "x")


def test_tool_error_accepts_enum_and_str():
    assert ToolError(ErrorCode.READ_FAILED, "m").code == "READ_FAILED"
    assert ToolError("READ_FAILED", "m").code == "READ_FAILED"


def test_hierarchy():
    assert issubclass(LibreOfficeTimeout, LibreOfficeError)
    assert issubclass(LibreOfficeNotFound, LibreOfficeError)


def test_success_path_sync():
    @tool_envelope
    def tool(x: int) -> dict:
        return {"x": x}

    assert tool(3) == success("tool", {"x": 3})


def test_success_path_async():
    @tool_envelope
    async def tool(x: int) -> dict:
        return {"x": x}

    assert inspect.iscoroutinefunction(tool)
    assert asyncio.run(tool(3)) == success("tool", {"x": 3})


def test_sync_stays_sync():
    @tool_envelope
    def tool() -> dict:
        return {}

    assert not inspect.iscoroutinefunction(tool)


@pytest.mark.parametrize("runner", RUNNERS)
@pytest.mark.parametrize("exc,code,message", MAPPING)
def test_exception_mapping(runner, exc, code, message):
    out = runner(exc)
    assert out["success"] is False
    assert out["data"] is None
    assert out["error"] == {"code": code, "message": message}
    assert type(out["error"]["code"]) is str


@pytest.mark.parametrize("runner", RUNNERS)
def test_timeout_and_notfound_not_conversion_failed(runner):
    assert runner(LibreOfficeTimeout("t"))["error"]["code"] != "CONVERSION_FAILED"
    assert runner(LibreOfficeNotFound("n"))["error"]["code"] != "CONVERSION_FAILED"


@pytest.mark.parametrize("runner", RUNNERS)
def test_runtime_error_is_internal(runner):
    out = runner(RuntimeError("boom"))
    assert out["error"]["code"] == "INTERNAL_ERROR"
    assert out["error"]["message"] == "RuntimeError: boom"
    assert "Traceback" not in out["error"]["message"]


@pytest.mark.parametrize("runner", RUNNERS)
@pytest.mark.parametrize("exc", [ValueError("v"), PermissionError("p"), OSError("o"), TypeError("t")])
def test_unmapped_exceptions_are_internal(runner, exc):
    out = runner(exc)
    assert out["error"]["code"] == "INTERNAL_ERROR"
    assert out["error"]["message"].startswith(type(exc).__name__ + ":")


def test_keyboard_interrupt_propagates_sync():
    with pytest.raises(KeyboardInterrupt):
        run_sync(KeyboardInterrupt())


def test_keyboard_interrupt_propagates_async():
    with pytest.raises(KeyboardInterrupt):
        run_async(KeyboardInterrupt())


def test_cancelled_error_propagates():
    with pytest.raises(asyncio.CancelledError):
        run_async(asyncio.CancelledError())


def test_system_exit_propagates():
    with pytest.raises(SystemExit):
        run_sync(SystemExit(1))


@pytest.mark.parametrize("is_async", [False, True])
def test_non_serializable_data(is_async):
    if is_async:
        @tool_envelope
        async def tool() -> dict:
            return {"p": Path("/tmp/x")}

        out = asyncio.run(tool())
    else:
        @tool_envelope
        def tool() -> dict:
            return {"p": Path("/tmp/x")}

        out = tool()
    assert out["success"] is False
    assert out["error"]["code"] == "INTERNAL_ERROR"
    assert "not JSON-serializable" in out["error"]["message"]


def test_signature_name_doc_preserved():
    def original(a: int, b: str = "x") -> dict:
        """Docstring."""
        return {}

    wrapped = tool_envelope(original)
    assert inspect.signature(wrapped) == inspect.signature(original)
    assert wrapped.__name__ == "original"
    assert wrapped.__doc__ == "Docstring."
    assert wrapped.__annotations__ == original.__annotations__


def test_signature_preserved_async():
    async def original(a: int) -> dict:
        """Doc."""
        return {}

    wrapped = tool_envelope(original)
    assert inspect.signature(wrapped) == inspect.signature(original)
    assert wrapped.__name__ == "original"


def test_name_override():
    @tool_envelope(name="x")
    def tool() -> dict:
        return {}

    assert tool()["tool"] == "x"
    assert tool.__name__ == "tool"

    @tool_envelope(name="y")
    def bad() -> dict:
        raise RuntimeError("r")

    assert bad()["tool"] == "y"


def test_default_name_is_function_name():
    @tool_envelope
    def my_tool() -> dict:
        return {}

    assert my_tool()["tool"] == "my_tool"


def test_nothing_on_stdout_for_internal_error(capsys):
    run_sync(RuntimeError("boom"))
    run_async(RuntimeError("boom"))
    assert capsys.readouterr().out == ""


def test_unicode_round_trip():
    msg = "파일을 찾을 수 없습니다: Noöm"
    out = failure("t", ErrorCode.READ_FAILED, msg)
    assert out["error"]["message"] == msg
    dumped = json.dumps(out, ensure_ascii=False)
    assert msg in dumped
    assert json.loads(dumped)["error"]["message"] == msg

    via_tool = run_sync(ToolError(ErrorCode.READ_FAILED, msg))
    assert via_tool["error"]["message"] == msg


def test_recursion_error_in_result_does_not_escape():
    deep: list = []
    for _ in range(100_000):
        deep = [deep]

    @tool_envelope
    def tool() -> dict:
        return {"deep": deep}

    out = tool()
    assert out["success"] is False
    assert out["error"]["code"] == "INTERNAL_ERROR"
