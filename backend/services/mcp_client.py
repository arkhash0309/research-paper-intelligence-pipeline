"""
mcp_client.py — Thin client that calls MCP server tools as a subprocess.

The MCP server runs over stdio. This client spawns the server process,
sends JSON-RPC requests, and returns the results.

Uses the official `mcp` Python SDK client.
"""

import json
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

            return _extract_payload(result)


def _extract_payload(result: Any) -> Any:
    """
    Convert an MCP CallToolResult into a plain Python value.

    FastMCP serialises a list return value as one content block *per item*,
    so reading only ``content[0]`` silently drops everything after the first
    element. Tools with a list/str return annotation also publish the complete
    value as ``structuredContent == {"result": ...}``, which is preferred.
    Tools returning a bare dict have no structured content and emit a single
    JSON text block.
    """
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict) and set(structured) == {"result"}:
        return structured["result"]
    if structured is not None:
        return structured

    texts = [block.text for block in result.content if getattr(block, "text", None) is not None]
    if not texts:
        return None

    parsed: list[Any] = []
    for raw in texts:
        try:
            parsed.append(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            # Plain-text payloads (e.g. Markdown) are returned as-is
            parsed.append(raw)

    return parsed[0] if len(parsed) == 1 else parsed
