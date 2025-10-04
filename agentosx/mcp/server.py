"""
MCP Server Implementation.

Exposes agentOSX agents and tools as MCP servers, allowing external
clients (Claude Desktop, Cursor, etc.) to discover and use them.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Awaitable

from .protocol import (
    MCPRequest,
    MCPResponse,
    MCPNotification,
    MCPProtocol,
    MCPCapabilities,
    ToolDefinition,
    ResourceDefinition,
    PromptDefinition,
    ErrorCode,
)
from .transport.base import Transport
from .tools.adapter import ToolAdapter
from .resources.manager import ResourceManager
from .prompts.manager import PromptManager

logger = logging.getLogger(__name__)


class MCPServer:
    """
    MCP Server for exposing agent capabilities.
    
    Handles MCP protocol messages and routes them to appropriate handlers.
    Supports tools, resources, and prompts.
    """
    
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        capabilities: Optional[MCPCapabilities] = None,
    ):
        """
        Initialize MCP server.
        
        Args:
            name: Server name/identifier
            version: Server version
            capabilities: Server capabilities
        """
        self.name = name
        self.version = version
        self.capabilities = capabilities or MCPCapabilities(
            tools=True,
            resources=True,
            prompts=True,
            streaming=True,
        )
        
        # Components
        self.tool_adapter = ToolAdapter()
        self.resource_manager = ResourceManager()
        self.prompt_manager = PromptManager()
        
        # State
        self.initialized = False
        self.client_capabilities: Optional[MCPCapabilities] = None
        self.transport: Optional[Transport] = None
        
        # Request handlers
        self._handlers: Dict[str, Callable] = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "prompts/list": self._handle_prompts_list,
            "prompts/get": self._handle_prompts_get,
        }
        
        # Running state
        self._running = False
        self._tasks: Set[asyncio.Task] = set()
    
    def register_tool(
        self,
        name: str,
        description: str,
        func: Callable,
        input_schema: Optional[Dict[str, Any]] = None,
    ):
        """
        Register a tool with the server.
        
        Args:
            name: Tool name
            description: Tool description
            func: Tool function (sync or async)
            input_schema: JSON Schema for tool inputs
        """
        self.tool_adapter.register_tool(name, description, func, input_schema)
        logger.info(f"Registered tool: {name}")
    
    def list_tools(self) -> List[ToolDefinition]:
        """
        List all registered tools.
        
        Returns:
            List of tool definitions
        """
        return self.tool_adapter.list_tools()
    
    def register_resource(
        self,
        uri: str,
        name: str,
        description: Optional[str] = None,
        mime_type: Optional[str] = None,
        reader: Optional[Callable] = None,
    ):
        """
        Register a resource with the server.
        
        Args:
            uri: Resource URI (e.g., 'agent://twitter/tweets/123')
            name: Resource name
            description: Resource description
            mime_type: MIME type of resource
            reader: Function to read resource content
        """
        self.resource_manager.register_resource(
            uri, name, description, mime_type, reader
        )
        logger.info(f"Registered resource: {uri}")
    
    def register_prompt(
        self,
        name: str,
        description: Optional[str] = None,
        template: Optional[str] = None,
        arguments: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Register a prompt template with the server.
        
        Args:
            name: Prompt name
            description: Prompt description
            template: Prompt template string
            arguments: List of argument definitions
        """
        self.prompt_manager.register_prompt(name, description, template, arguments)
        logger.info(f"Registered prompt: {name}")
    
    async def start(self, transport: Transport):
        """
        Start the MCP server with the given transport.
        
        Args:
            transport: Transport layer (STDIO, SSE, WebSocket)
        """
        self.transport = transport
        self._running = True
        
        logger.info(f"Starting MCP server: {self.name} v{self.version}")
        
        try:
            await transport.start(self._handle_message)
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the MCP server."""
        self._running = False
        
        # Cancel all running tasks
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        if self.transport:
            await self.transport.stop()
        
        logger.info("MCP server stopped")
    
    async def _handle_message(self, raw_message: str):
        """
        Handle incoming MCP message.
        
        Args:
            raw_message: Raw JSON-RPC message
        """
        try:
            message = MCPProtocol.parse_message(raw_message)
            
            if isinstance(message, MCPRequest):
                response = await self._handle_request(message)
                if response and self.transport:
                    await self.transport.send(MCPProtocol.serialize_message(response))
            
            elif isinstance(message, MCPNotification):
                await self._handle_notification(message)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            # Send error response if we can extract request ID
            try:
                data = MCPProtocol.parse_message(raw_message)
                if hasattr(data, 'id'):
                    error_response = MCPProtocol.create_error_response(
                        data.id,
                        ErrorCode.INTERNAL_ERROR,
                        str(e)
                    )
                    if self.transport:
                        await self.transport.send(MCPProtocol.serialize_message(error_response))
            except:
                pass
    
    async def _handle_request(self, request: MCPRequest) -> Optional[MCPResponse]:
        """
        Handle MCP request.
        
        Args:
            request: MCP request message
            
        Returns:
            MCP response or None
        """
        handler = self._handlers.get(request.method)
        
        if not handler:
            return MCPProtocol.create_error_response(
                request.id,
                ErrorCode.METHOD_NOT_FOUND,
                f"Method not found: {request.method}"
            )
        
        try:
            result = await handler(request)
            return MCPProtocol.create_success_response(request.id, result)
        except Exception as e:
            logger.error(f"Error handling {request.method}: {e}", exc_info=True)
            return MCPProtocol.create_error_response(
                request.id,
                ErrorCode.INTERNAL_ERROR,
                str(e)
            )
    
    async def _handle_notification(self, notification: MCPNotification):
        """Handle MCP notification (no response needed)."""
        logger.debug(f"Received notification: {notification.method}")
    
    async def _handle_initialize(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle initialization handshake."""
        params = request.params or {}
        
        # Parse client capabilities
        client_caps_data = params.get("capabilities", {})
        self.client_capabilities = MCPCapabilities(
            tools=client_caps_data.get("tools", False),
            resources=client_caps_data.get("resources", False),
            prompts=client_caps_data.get("prompts", False),
            streaming=client_caps_data.get("streaming", False),
            version=params.get("protocolVersion", "1.0.0"),
        )
        
        # Negotiate capabilities
        negotiated = MCPProtocol.negotiate_capabilities(
            self.client_capabilities,
            self.capabilities
        )
        
        self.initialized = True
        
        return {
            "protocolVersion": MCPProtocol.VERSION,
            "capabilities": negotiated.to_dict(),
            "serverInfo": {
                "name": self.name,
                "version": self.version,
            }
        }
    
    async def _handle_tools_list(self, request: MCPRequest) -> Dict[str, Any]:
        """List available tools."""
        if not self.capabilities.tools:
            raise ValueError("Tools capability not enabled")
        
        tools = self.tool_adapter.list_tools()
        return {
            "tools": [tool.to_dict() for tool in tools]
        }
    
    async def _handle_tools_call(self, request: MCPRequest) -> Dict[str, Any]:
        """Execute a tool."""
        if not self.capabilities.tools:
            raise ValueError("Tools capability not enabled")
        
        params = request.params or {}
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            raise ValueError("Tool name is required")
        
        result = await self.tool_adapter.execute_tool(tool_name, arguments)
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": str(result)
                }
            ]
        }
    
    async def _handle_resources_list(self, request: MCPRequest) -> Dict[str, Any]:
        """List available resources."""
        if not self.capabilities.resources:
            raise ValueError("Resources capability not enabled")
        
        resources = self.resource_manager.list_resources()
        return {
            "resources": [resource.to_dict() for resource in resources]
        }
    
    async def _handle_resources_read(self, request: MCPRequest) -> Dict[str, Any]:
        """Read a resource."""
        if not self.capabilities.resources:
            raise ValueError("Resources capability not enabled")
        
        params = request.params or {}
        uri = params.get("uri")
        
        if not uri:
            raise ValueError("Resource URI is required")
        
        content = await self.resource_manager.read_resource(uri)
        
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": content.get("mimeType", "text/plain"),
                    "text": content.get("text", "")
                }
            ]
        }
    
    async def _handle_prompts_list(self, request: MCPRequest) -> Dict[str, Any]:
        """List available prompts."""
        if not self.capabilities.prompts:
            raise ValueError("Prompts capability not enabled")
        
        prompts = self.prompt_manager.list_prompts()
        return {
            "prompts": [prompt.to_dict() for prompt in prompts]
        }
    
    async def _handle_prompts_get(self, request: MCPRequest) -> Dict[str, Any]:
        """Get a prompt template."""
        if not self.capabilities.prompts:
            raise ValueError("Prompts capability not enabled")
        
        params = request.params or {}
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not name:
            raise ValueError("Prompt name is required")
        
        prompt = await self.prompt_manager.get_prompt(name, arguments)
        
        return {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": prompt
                    }
                }
            ]
        }
