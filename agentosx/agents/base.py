"""
Enhanced Base Agent for agentOSX.

Provides lifecycle hooks, MCP integration, and streaming support.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from ..mcp.server import MCPServer
from ..mcp.protocol import MCPCapabilities

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent status enumeration."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class AgentState:
    """Agent state container."""
    status: AgentStatus = AgentStatus.IDLE
    context: Dict[str, Any] = field(default_factory=dict)
    memory: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """Execution context for agent operations."""
    input: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamChunk:
    """Chunk of streamed data."""
    type: str  # "text", "tool_call", "tool_result", "thought", etc.
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Enhanced base class for all agentOSX agents.
    
    Features:
    - Lifecycle hooks (on_init, on_start, on_stop, etc.)
    - MCP server integration
    - Streaming support
    - State management
    - Context-aware execution
    """
    
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        description: Optional[str] = None,
    ):
        """
        Initialize agent.
        
        Args:
            name: Agent name
            version: Agent version
            description: Agent description
        """
        self.name = name
        self.version = version
        self.description = description or f"{name} agent"
        
        # State
        self.state = AgentState()
        
        # MCP server (optional)
        self.mcp_server: Optional[MCPServer] = None
        
        # Lifecycle hooks
        self._hooks: Dict[str, List[Callable]] = {
            "on_init": [],
            "on_start": [],
            "on_stop": [],
            "on_message": [],
            "on_tool_call": [],
            "on_tool_result": [],
            "on_error": [],
        }
        
        logger.info(f"Initialized agent: {self.name} v{self.version}")
    
    # Lifecycle Methods
    
    async def initialize(self):
        """Initialize agent (called once during setup)."""
        self.state.status = AgentStatus.INITIALIZING
        
        await self._run_hooks("on_init")
        await self.on_init()
        
        self.state.status = AgentStatus.IDLE
        logger.info(f"Agent {self.name} initialized")
    
    async def start(self):
        """Start agent."""
        self.state.status = AgentStatus.RUNNING
        
        await self._run_hooks("on_start")
        await self.on_start()
        
        logger.info(f"Agent {self.name} started")
    
    async def stop(self):
        """Stop agent."""
        await self._run_hooks("on_stop")
        await self.on_stop()
        
        # Stop MCP server if running
        if self.mcp_server:
            await self.mcp_server.stop()
        
        self.state.status = AgentStatus.STOPPED
        logger.info(f"Agent {self.name} stopped")
    
    # Core Methods
    
    @abstractmethod
    async def process(self, input: str, context: Optional[ExecutionContext] = None) -> str:
        """
        Process input and return result.
        
        Args:
            input: Input text
            context: Execution context
            
        Returns:
            Response text
        """
        pass
    
    async def stream(
        self,
        input: str,
        context: Optional[ExecutionContext] = None
    ) -> AsyncIterator[StreamChunk]:
        """
        Process input with streaming output.
        
        Args:
            input: Input text
            context: Execution context
            
        Yields:
            Stream chunks
        """
        # Default implementation: non-streaming
        result = await self.process(input, context)
        yield StreamChunk(type="text", content=result)
    
    # MCP Integration
    
    def to_mcp_server(self, capabilities: Optional[MCPCapabilities] = None) -> MCPServer:
        """
        Convert agent to MCP server.
        
        Args:
            capabilities: Server capabilities
            
        Returns:
            MCP server instance
        """
        if self.mcp_server:
            return self.mcp_server
        
        self.mcp_server = MCPServer(
            name=self.name,
            version=self.version,
            capabilities=capabilities,
        )
        
        # Register agent's process method as a tool
        self.mcp_server.register_tool(
            name=f"{self.name}_process",
            description=f"Process input with {self.name}",
            func=self._mcp_process_wrapper,
            input_schema={
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "Input text to process"
                    }
                },
                "required": ["input"]
            }
        )
        
        logger.info(f"Created MCP server for agent: {self.name}")
        return self.mcp_server
    
    async def _mcp_process_wrapper(self, input: str) -> str:
        """Wrapper for MCP tool calls."""
        return await self.process(input)
    
    def register_mcp_tool(
        self,
        name: str,
        description: str,
        func: Callable,
        input_schema: Optional[Dict[str, Any]] = None,
    ):
        """
        Register a custom tool with the MCP server.
        
        Args:
            name: Tool name
            description: Tool description
            func: Tool function
            input_schema: JSON Schema for inputs
        """
        if not self.mcp_server:
            self.to_mcp_server()
        
        self.mcp_server.register_tool(name, description, func, input_schema)
    
    # Lifecycle Hooks
    
    async def on_init(self):
        """Called during initialization. Override in subclasses."""
        pass
    
    async def on_start(self):
        """Called when agent starts. Override in subclasses."""
        pass
    
    async def on_stop(self):
        """Called when agent stops. Override in subclasses."""
        pass
    
    async def on_message(self, message: str):
        """Called when agent receives a message. Override in subclasses."""
        pass
    
    async def on_tool_call(self, tool_name: str, arguments: Dict[str, Any]):
        """Called before tool execution. Override in subclasses."""
        pass
    
    async def on_tool_result(self, tool_name: str, result: Any):
        """Called after tool execution. Override in subclasses."""
        pass
    
    async def on_error(self, error: Exception):
        """Called when an error occurs. Override in subclasses."""
        logger.error(f"Agent error: {error}", exc_info=True)
    
    # Hook Registration
    
    def add_hook(self, event: str, callback: Callable):
        """
        Register a lifecycle hook.
        
        Args:
            event: Event name (on_init, on_start, etc.)
            callback: Callback function
        """
        if event in self._hooks:
            self._hooks[event].append(callback)
        else:
            raise ValueError(f"Unknown hook event: {event}")
    
    async def _run_hooks(self, event: str):
        """Run all hooks for an event."""
        for callback in self._hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self)
                else:
                    callback(self)
            except Exception as e:
                logger.error(f"Hook error ({event}): {e}", exc_info=True)
    
    # State Management
    
    def get_state(self) -> AgentState:
        """Get current agent state."""
        return self.state
    
    def update_state(self, **kwargs):
        """Update agent state."""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
    
    def set_context(self, key: str, value: Any):
        """Set context value."""
        self.state.context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context value."""
        return self.state.context.get(key, default)
    
    # Utility Methods
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} version={self.version} status={self.state.status.value}>"
