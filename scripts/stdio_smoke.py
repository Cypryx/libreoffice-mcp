# Minimal stdio smoke test: negotiate the MCP handshake against the server and
# list tools. Phase 1 expectation: 0 tools, clean initialize + tools/list.
import asyncio
import os
import sys
from pathlib import Path

# Ensure we import the project venv, not Hermes's inherited site-packages.
os.environ.pop("PYTHONPATH", None)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".venv" / "Lib" / "site-packages"))

from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters


async def main() -> None:
    params = StdioServerParameters(
        command="python",
        args=["-m", "libreoffice_mcp", "--help"],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
    )
    # Launch the real server in stdio mode.
    server_params = StdioServerParameters(
        command=str(Path(__file__).resolve().parents[1] / ".venv" / "Scripts" / "python.exe"),
        args=["-m", "libreoffice_mcp.server", "serve"],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print("server info:", init.serverInfo.name, init.serverInfo.version)
            tools = await session.list_tools()
            print("tool count:", len(tools.tools))
            for t in tools.tools:
                print("  -", t.name)


asyncio.run(main())