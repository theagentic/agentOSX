"""
AgentOSX - Production-grade, MCP-native agent framework.

A comprehensive framework for building, deploying, and governing agents at scale.
"""

__version__ = "0.1.0"
__author__ = "AgentOSX Team"
__email__ = "team@agentosx.dev"
__license__ = "MIT"

# Core agent framework
from .agents.base import BaseAgent, AgentStatus, AgentState, ExecutionContext
from .agents.loader import AgentLoader
from .agents.decorators import agent, tool, hook, streaming

# MCP integration
from .mcp.server import MCPServer
from .mcp.client import MCPClient
from .mcp.protocol import MCPMessage, MCPRequest, MCPResponse, ToolDefinition

# SDK
from .sdk.builder import AgentBuilder
from .sdk.types import AgentConfig, ToolConfig, MCPServerConfig

# Streaming
from .streaming.events import StreamEvent, EventType

__all__ = [
    # Core
    "BaseAgent",
    "AgentStatus",
    "AgentState",
    "ExecutionContext",
    "AgentLoader",
    # Decorators
    "agent",
    "tool",
    "hook",
    "streaming",
    # MCP
    "MCPServer",
    "MCPClient",
    "MCPMessage",
    "MCPRequest",
    "MCPResponse",
    "ToolDefinition",
    # SDK
    "AgentBuilder",
    "AgentConfig",
    "ToolConfig",
    "MCPServerConfig",
    # Streaming
    "StreamEvent",
    "EventType",
]
