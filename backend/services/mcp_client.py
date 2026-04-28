"""
mcp_client.py — Thin client that calls MCP server tools as a subprocess.

The MCP server runs over stdio. This client spawns the server process,
sends JSON-RPC requests, and returns the results.

Uses the official `mcp` Python SDK client.
"""

import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Resolve the path to the MCP server script
_MCP_SERVER_SCRIPT = str(
    Path(__file__).resolve().parent.parent.parent / "mcp_server" / "server.py"
)


def _build_server_params() -> StdioServerParameters:
    """
    Build the StdioServerParameters needed to launch the MCP server subprocess.

    The server inherits ANTHROPIC_API_KEY and SEMANTIC_SCHOLAR_API_KEY from
    the environment so the backend .env must forward them or they must be
    set in the shell before starting uvicorn.
    """
    env = {
        **os.environ,  # inherit everything, including API keys
    }
    return StdioServerParameters(
        command=sys.executable,  # same Python interpreter as the backend
        args=[_MCP_SERVER_SCRIPT],
        env=env,
    )


async def call_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    """
    Call a named MCP tool and return its result payload.

    Spawns the MCP server as a subprocess, performs a single tool call,
    then cleanly shuts down the subprocess.

    Args:
        tool_name: The tool name as registered in server.py (e.g. "tool_search_arxiv").
        arguments: Dict of keyword arguments for the tool.

    Returns:
        The parsed result from the tool (list, dict, or str depending on the tool).

    Raises:
        RuntimeError: If the MCP call fails or returns an error.
    """
    server_params = _build_server_params()

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Perform the MCP protocol handshake
            await session.initialize()

            # Call the tool
            result = await session.call_tool(tool_name, arguments=arguments)

            # The MCP SDK wraps results in a content list; extract the first item
            if result.isError:
                error_text = (
                    result.content[0].text if result.content else "Unknown MCP error"
                )
                raise RuntimeError(f"MCP tool '{tool_name}' returned an error: {error_text}")

            if not result.content:
                return None

            # Tools that return structured data encode it as JSON text
            import json
            raw = result.content[0].text
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                # Some tools (e.g. synthesise) return plain Markdown strings
                return raw
