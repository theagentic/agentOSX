"""
MCP Tool Registry.

Manages discovered MCP tools from external servers.
"""

import logging
from typing import Dict, List, Optional, Callable, Any

from ..protocol import ToolDefinition

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry for MCP tools from external servers.
    
    Maintains a catalog of discovered tools and provides
    lookup and execution capabilities.
    """
    
    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, ToolDefinition] = {}
        self._executors: Dict[str, Callable] = {}
    
    def register(self, tool: ToolDefinition, executor: Callable):
        """
        Register a tool with its executor.
        
        Args:
            tool: Tool definition
            executor: Function to call the tool (typically MCPClient.call_tool)
        """
        self._tools[tool.name] = tool
        self._executors[tool.name] = executor
        
        logger.debug(f"Registered MCP tool: {tool.name}")
    
    def unregister(self, name: str):
        """
        Unregister a tool.
        
        Args:
            name: Tool name
        """
        if name in self._tools:
            del self._tools[name]
            del self._executors[name]
            logger.debug(f"Unregistered MCP tool: {name}")
    
    def get(self, name: str) -> Optional[ToolDefinition]:
        """
        Get tool definition by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool definition or None
        """
        return self._tools.get(name)
    
    def list_all(self) -> List[ToolDefinition]:
        """
        List all registered tools.
        
        Returns:
            List of tool definitions
        """
        return list(self._tools.values())
    
    async def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool result
            
        Raises:
            ValueError: If tool not found
        """
        if name not in self._executors:
            raise ValueError(f"Tool not found: {name}")
        
        executor = self._executors[name]
        return await executor(name, arguments)
    
    def has(self, name: str) -> bool:
        """
        Check if tool is registered.
        
        Args:
            name: Tool name
            
        Returns:
            True if tool is registered
        """
        return name in self._tools
    
    def clear(self):
        """Clear all registered tools."""
        self._tools.clear()
        self._executors.clear()
        logger.debug("Cleared all tools from registry")
