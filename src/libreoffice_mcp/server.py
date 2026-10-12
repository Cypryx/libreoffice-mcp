# server.py - MCP server entry point and tool registration.
#
# Phase 1 milestone: the server starts and runs but registers ZERO tools. Tool
# modules are imported and wired in later phases. The entry point also supports
# --version and --help so operators can smoke-test the install without an MCP client.
from __future__ import annotations

import sys
from pathlib import Path

import typer
from mcp.server.fastmcp import FastMCP

from . import __version__
from .config import load_settings

app = typer.Typer(
    help="libreoffice-mcp: LibreOffice document server for MCP agents.",
    no_args_is_help=True,
    add_completion=False,
)

# Module-level MCP server object. It is intentionally created fresh per process
# and lazily discovers tools so test harnesses can build their own instances.
mcp = FastMCP("libreoffice-mcp", instructions="""
    LibreOffice MCP server: create, read, edit, review, and present .docx, .odt,
    and .pptx documents via LibreOffice headless under the hood.
""")


def register_tools() -> None:
    """Register all tool modules on the module-level ``mcp`` instance.

    Phase 1: intentionally empty. Phase 2+ imports each tools.<module> and calls
    a register(<mcp>) function that wires its tools onto the server.
    """
    # Import tool registration functions here as phases land, e.g.:
    #   from .tools.document import register as register_document
    #   register_document(mcp)


@app.command()
def version() -> None:
    """Print the installed version and exit."""
    typer.echo(f"libreoffice-mcp {__version__}")


@app.command()
def serve(
    timeout: int = typer.Option(
        60, "--timeout", help="Seconds to wait for a LibreOffice call before failing."
    ),
) -> None:
    """Run the MCP stdio server (the mode agents connect over)."""
    # Surface configuration lazily so a bad LIBREOFFICE_PATH surfaces as a clear
    # error at runtime, not at import time.
    _ = load_settings()
    register_tools()
    mcp.run(transport="stdio")


@app.command()
def check_libreoffice() -> None:
    """Verify the LibreOffice binary resolves and reports its version."""
    from .utils import libreoffice

    from .config import load_settings

    settings = load_settings()
    binary = libreoffice.resolve_libreoffice_binary(settings.libreoffice_path)
    ver = libreoffice.get_version(settings)
    typer.echo(f"LibreOffice binary: {binary}")
    typer.echo(f"LibreOffice version: {ver}")


def main() -> None:
    # Bare invocation (`libreoffice-mcp`, no subcommand) is how Hermes / any
    # MCP client launches the server over stdio. Only dispatch into the Typer
    # CLI when the user explicitly asks for a human-facing command.
    if len(sys.argv) == 1:
        register_tools()
        mcp.run(transport="stdio")
        return
    app()


if __name__ == "__main__":
    main()