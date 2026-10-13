# libreoffice.py - LibreOffice headless subprocess wrapper.
#
# All interaction with the native LibreOffice binary happens here, isolated so
# tool modules never shell out themselves. The wrapper guarantees a bounded run
# (no hang), real error propagation, and a resolved binary path on each platform.
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Sequence

from ..config import Settings

# On Windows the console binary (.com) is the correct variant for headless,
# synchronous use. soffice.exe is a GUI launcher that can spawn a detached
# process and never return output to the invoking shell.
_WINDOWS_CONSOLE_SUFFIX = ".com"

# Extensions LibreOffice can convert to via headless --convert-to.
_CONVERT_TO_EXTENSIONS = {"pdf", "docx", "odt", "pptx", "txt", "html", "rtf"}


class LibreOfficeError(RuntimeError):
    """Raised when the LibreOffice binary is missing or a conversion fails."""


def resolve_libreoffice_binary(path: str | None = None) -> str:
    """Return the path to the LibreOffice binary to invoke.

    When given an explicit ``path`` it is used as-is (already resolved by the
    caller). Otherwise the configured ``Settings.libreoffice_path`` is searched
    on PATH, and on Windows a platform-specific fallback is probed.

    Raises LibreOfficeError if nothing executable resolves.
    """
    # An explicit path that points at a real file.
    if path:
        candidate = Path(path).expanduser()
        if candidate.is_file():
            return str(candidate)
        # Fall through to PATH/Win32 probing below if it wasn't a real file,
        # so a bare command name (e.g. the default ``libreoffice``) still works.

    # 1. Explicit path OR command name resolved via PATH.
    resolved = shutil.which(path) if path else shutil.which("libreoffice")
    if resolved:
        return resolved

    # 2. Windows well-known install locations. Prefer soffice.com (console).
    if hasattr(Path, "home"):
        program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        candidates = [
            program_files / "LibreOffice" / "program" / ("soffice" + _WINDOWS_CONSOLE_SUFFIX),
            program_files / "LibreOffice" / "program" / "soffice.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)

    raise LibreOfficeError(
        "Could not locate a LibreOffice binary. Set LIBREOFFICE_PATH to the full "
        "path of the executable (e.g. C:\\Program Files\\LibreOffice\\program\\soffice.com)."
    )


# Cap on simultaneous LibreOffice processes. Created lazily from the first
# call's settings; the lock keeps two threads from creating two semaphores.
_semaphore: threading.BoundedSemaphore | None = None
_semaphore_lock = threading.Lock()


def _get_semaphore(settings: Settings) -> threading.BoundedSemaphore:
    global _semaphore
    with _semaphore_lock:
        if _semaphore is None:
            _semaphore = threading.BoundedSemaphore(
                max(1, settings.max_concurrent_conversions)
            )
        return _semaphore


def _kill_process_tree(child: subprocess.Popen) -> None:
    """Kill ``child`` and every process it spawned, then reap it."""
    if sys.platform == "win32":
        # Windows: soffice.com launches soffice.bin as a child. taskkill /T /F
        # terminates the whole tree rooted at the launcher's PID.
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(child.pid)],
            check=False,
            capture_output=True,
        )
    else:
        # POSIX: the child leads its own process group (start_new_session=True).
        # Ask politely, wait briefly, then SIGKILL whatever is left.
        try:
            pgid = os.getpgid(child.pid)
        except ProcessLookupError:
            pgid = None
        if pgid is not None:
            try:
                os.killpg(pgid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        child.communicate(timeout=5)  # reap and close pipes
    except subprocess.TimeoutExpired:
        child.kill()
        child.communicate()


def run_headless(
    *args: str,
    settings: Settings,
    timeout: float | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a headless LibreOffice command with a hard timeout.

    ``args`` are appended to ``[\"soffice\", \"--headless\", \"--norestore\"]``.
    The first run of a fresh profile can be slow, so callers may raise the
    timeout; the configured conversion timeout is the default.
    """
    binary = resolve_libreoffice_binary(settings.libreoffice_path)
    timeout_s = timeout if timeout is not None else settings.conversion_timeout_seconds

    # A fresh, disposable LibreOffice profile per call. Isolating the profile
    # guarantees this call never reuses or locks another instance's profile
    # (which is what made soffice.com hang/flake on Windows), and that no
    # profile state accumulates between runs. The TemporaryDirectory is torn
    # down automatically on success, timeout, or any exception.
    # Hold a concurrency slot from before the profile exists until the process
    # tree is dead and the profile is deleted. Waiting for a slot happens here,
    # before Popen, so it never counts against ``timeout`` (that clock starts
    # inside communicate()).
    semaphore = _get_semaphore(settings)
    semaphore.acquire()
    try:
        with tempfile.TemporaryDirectory() as profile_dir:
            profile_uri = Path(profile_dir).as_uri()
            cmd = [binary, "--headless", "--norestore", f"-env:UserInstallation={profile_uri}", *args]
            popen_kwargs: dict = {}
            if sys.platform != "win32":
                # Own session/process group so a timeout can kill the whole tree
                # (the launcher script plus soffice.bin / oosplash), not just the launcher.
                popen_kwargs["start_new_session"] = True
            try:
                child = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,  # LibreOffice must never inherit the MCP stdio protocol pipe
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    **popen_kwargs,
                )
            except OSError as exc:
                raise LibreOfficeError(f"Failed to launch LibreOffice ({binary}): {exc}") from exc

            try:
                stdout, stderr = child.communicate(timeout=timeout_s)
            except subprocess.TimeoutExpired as exc:
                _kill_process_tree(child)
                raise LibreOfficeError(
                    f"LibreOffice timed out after {timeout_s:g}s: {' '.join(cmd)}"
                ) from exc
            except BaseException:
                _kill_process_tree(child)
                raise
            proc = subprocess.CompletedProcess(cmd, child.returncode, stdout, stderr)

            if check and proc.returncode != 0:
                detail = (proc.stderr or proc.stdout or "").strip()
                raise LibreOfficeError(
                    f"LibreOffice exited {proc.returncode}: {' '.join(cmd)}\n{detail}"
                )
            return proc
    finally:
        semaphore.release()


def get_version(settings: Settings, timeout: float = 15.0) -> str:
    """Return the LibreOffice version string (e.g. '26.2.6.3')."""
    proc = run_headless("--version", settings=settings, timeout=timeout, check=True)
    return proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else "unknown"


def convert_file(
    source: Path,
    convert_to: str,
    out_dir: Path,
    settings: Settings,
    timeout: float | None = None,
) -> Path:
    """Convert ``source`` to the target format using LibreOffice headless.

    ``convert_to`` is an extension like 'pdf' or 'docx'. Returns the path of the
    converted file. Raises LibreOfficeError on failure.
    """
    convert_to = convert_to.lower().lstrip(".")
    if convert_to not in _CONVERT_TO_EXTENSIONS:
        raise LibreOfficeError(
            f"Unsupported conversion target '{convert_to}'. "
            f"Supported: {', '.join(sorted(_CONVERT_TO_EXTENSIONS))}"
        )
    if not source.is_file():
        raise LibreOfficeError(f"Source file not found: {source}")

    out_dir.mkdir(parents=True, exist_ok=True)
    run_headless(
        "--convert-to",
        convert_to,
        "--outdir",
        str(out_dir),
        str(source),
        settings=settings,
        timeout=timeout,
        check=True,
    )

    return out_dir / source.with_suffix(f".{convert_to}").name