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

import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Resolve the path to the MCP server script
_MCP_SERVER_SCRIPT = str(
    Path(__file__).resolve().parent.parent.parent / "mcp_server" / "server.py"
)


# Upper bound for one tool call, including spawning the MCP subprocess.
# LLM-backed tools get more time than the search/storage tools.
_DEFAULT_TIMEOUT_S = float(os.environ.get("MCP_TOOL_TIMEOUT", "60"))
_LLM_TIMEOUT_S = float(os.environ.get("MCP_LLM_TOOL_TIMEOUT", "270"))
_LLM_TOOLS = {
    "tool_extract_key_findings",
    "tool_identify_research_gaps",
    "tool_synthesise_literature_review",
}


def _build_server_params() -> StdioServerParameters:
    """
    Build the StdioServerParameters needed to launch the MCP server subprocess.

    The server inherits OPENAI_API_KEY and SEMANTIC_SCHOLAR_API_KEY from
    the environment (main.py loads mcp_server/.env before any call is made).
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

    timeout = _LLM_TIMEOUT_S if tool_name in _LLM_TOOLS else _DEFAULT_TIMEOUT_S

    try:
        result = await asyncio.wait_for(
            _call_tool_once(server_params, tool_name, arguments), timeout=timeout
        )
    except (asyncio.TimeoutError, TimeoutError) as e:
        raise RuntimeError(
            f"MCP tool '{tool_name}' timed out after {timeout:.0f}s"
        ) from e
    except BaseExceptionGroup as group:
        # stdio_client runs inside an anyio TaskGroup, so any failure (e.g. the
        # subprocess crashing on startup) surfaces as an ExceptionGroup rather
        # than the underlying error. Unwrap it so callers can catch RuntimeError.
        leaf = _first_leaf_exception(group)
        if not isinstance(leaf, Exception):
            raise
        raise RuntimeError(f"MCP call to '{tool_name}' failed: {leaf}") from group
    except OSError as e:
        raise RuntimeError(f"Could not start the MCP server: {e}") from e

    # Raise tool errors *outside* the stdio_client context so they are not
    # wrapped in an ExceptionGroup by the TaskGroup teardown.
    if result.isError:
        error_text = next(
            (block.text for block in result.content if getattr(block, "text", None)),
            "Unknown MCP error",
        )
        # FastMCP prefixes messages with "Error executing tool <name>: " — drop
        # it so the user sees only the underlying reason
        prefix = f"Error executing tool {tool_name}: "
        if error_text.startswith(prefix):
            error_text = error_text[len(prefix):]
        raise RuntimeError(error_text)

    return _extract_payload(result)


async def _call_tool_once(
    server_params: StdioServerParameters, tool_name: str, arguments: dict[str, Any]
) -> Any:
    """Spawn the MCP server, perform the handshake and one tool call, then shut down."""
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            return await session.call_tool(tool_name, arguments=arguments)


def _first_leaf_exception(group: BaseExceptionGroup) -> BaseException:
    """Return the first non-group exception nested inside an ExceptionGroup."""
    exc: BaseException = group
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    return exc


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
