# Launch the server EXACTLY as Hermes config does: bare `uv run --directory ... libreoffice-mcp`
# with only PYTHONPATH='' in env. This is the real launch test.
import asyncio, os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

env = {**os.environ,
       "PYTHONPATH": "",
       "LIBREOFFICE_PATH": r"C:\Program Files\LibreOffice\program\soffice.com",
       "LIBREOFFICE_MCP_AUTHOR_NAME": "Cypryx",
       "LIBREOFFICE_MCP_AUTHOR_INITIALS": "CX"}
params = StdioServerParameters(
    command="uv",
    args=["run", "--directory", r"C:\Users\smeefer\libreoffice-mcp", "libreoffice-mcp"],
    env=env,
)

async def main():
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                init = await asyncio.wait_for(session.initialize(), timeout=30)
                print("INIT OK:", init.serverInfo.name, init.serverInfo.version)
                tools = await session.list_tools()
                print("tool count:", len(tools.tools))
    except Exception as e:
        print("FAILED:", type(e).__name__, e)

asyncio.run(main())