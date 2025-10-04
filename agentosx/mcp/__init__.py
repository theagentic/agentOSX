"""
MCP (Model Context Protocol) Integration Layer.

Provides both server and client implementations for the MCP protocol,
enabling agentOSX agents to expose tools and consume external MCP services.
"""

from .protocol import (
    MCPMessage,
    MCPRequest,
    MCPResponse,
    MCPNotification,
    MCPError,
    MCPProtocol,
    ErrorCode,
)
from .server import MCPServer
from .client import MCPClient

__all__ = [
    "MCPMessage",
    "MCPRequest",
    "MCPResponse",
    "MCPNotification",
    "MCPError",
    "MCPProtocol",
    "ErrorCode",
    "MCPServer",
    "MCPClient",
]
