"""MCP tools for NyxDocs."""

from mcp.server.fastmcp import FastMCP

from .crypto_tools import register_crypto_tools
from .system_tools import register_system_tools


def register_tools(server: FastMCP) -> None:
    """Register all MCP tools with the server."""
    register_crypto_tools(server)
    register_system_tools(server)


__all__ = ["register_tools"]
