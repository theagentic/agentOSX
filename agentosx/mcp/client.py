"""
MCP Client Implementation.

Connects to external MCP servers and dynamically discovers/registers tools.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from .protocol import (
    MCPRequest,
    MCPResponse,
    MCPProtocol,
    MCPCapabilities,
    ToolDefinition,
    ResourceDefinition,
    PromptDefinition,
    ErrorCode,
)
from .transport.base import Transport

logger = logging.getLogger(__name__)


class MCPClient:
    """
    MCP Client for consuming external MCP servers.
    
    Connects to MCP servers, discovers available tools/resources/prompts,
    and provides methods to call them.
    """
    
    def __init__(
        self,
        capabilities: Optional[MCPCapabilities] = None,
    ):
        """
        Initialize MCP client.
        
        Args:
            capabilities: Client capabilities
        """
        self.capabilities = capabilities or MCPCapabilities(
            tools=True,
            resources=True,
            prompts=True,
            streaming=True,
        )
        
        # State
        self.initialized = False
        self.server_capabilities: Optional[MCPCapabilities] = None
        self.server_info: Optional[Dict[str, Any]] = None
        self.transport: Optional[Transport] = None
        
        # Discovered items
        self._tools: Dict[str, ToolDefinition] = {}
        self._resources: Dict[str, ResourceDefinition] = {}
        self._prompts: Dict[str, PromptDefinition] = {}
        
        # Pending requests
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._request_counter = 0
        
        # Connection state
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_delay = 1.0  # exponential backoff
    
    async def connect(self, transport: Transport, auto_discover: bool = True):
        """
        Connect to MCP server.
        
        Args:
            transport: Transport layer
            auto_discover: Automatically discover tools/resources/prompts
        """
        self.transport = transport
        
        logger.info("Connecting to MCP server...")
        
        try:
            # Start transport
            await transport.start(self._handle_message)
            
            # Initialize handshake
            await self._initialize()
            
            # Auto-discover if enabled
            if auto_discover:
                await self.discover_all()
            
            self._connected = True
            self._reconnect_attempts = 0
            
            logger.info("Connected to MCP server successfully")
            
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            await self._handle_reconnect()
            raise
    
    async def disconnect(self):
        """Disconnect from MCP server."""
        self._connected = False
        
        if self.transport:
            await self.transport.stop()
        
        # Cancel pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        
        self._pending_requests.clear()
        
        logger.info("Disconnected from MCP server")
    
    async def _handle_reconnect(self):
        """Handle reconnection with exponential backoff."""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return
        
        self._reconnect_attempts += 1
        delay = self._reconnect_delay * (2 ** (self._reconnect_attempts - 1))
        
        logger.info(f"Reconnecting in {delay}s (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})")
        
        await asyncio.sleep(delay)
        
        try:
            if self.transport:
                await self.connect(self.transport)
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            await self._handle_reconnect()
    
    async def _initialize(self):
        """Perform initialization handshake."""
        request = MCPRequest(
            method="initialize",
            params={
                "protocolVersion": MCPProtocol.VERSION,
                "capabilities": self.capabilities.to_dict(),
                "clientInfo": {
                    "name": "agentOSX",
                    "version": "0.1.0",
                }
            }
        )
        
        response = await self._send_request(request)
        
        # Parse server capabilities
        server_caps_data = response.get("capabilities", {})
        self.server_capabilities = MCPCapabilities(
            tools=server_caps_data.get("tools", False),
            resources=server_caps_data.get("resources", False),
            prompts=server_caps_data.get("prompts", False),
            streaming=server_caps_data.get("streaming", False),
            version=response.get("protocolVersion", "1.0.0"),
        )
        
        self.server_info = response.get("serverInfo", {})
        self.initialized = True
        
        logger.info(f"Initialized with server: {self.server_info.get('name', 'Unknown')}")
    
    async def discover_tools(self) -> List[ToolDefinition]:
        """Discover available tools from the server."""
        if not self.server_capabilities or not self.server_capabilities.tools:
            logger.warning("Server does not support tools")
            return []
        
        request = MCPRequest(method="tools/list")
        response = await self._send_request(request)
        
        tools_data = response.get("tools", [])
        self._tools = {
            tool_data["name"]: ToolDefinition.from_dict(tool_data)
            for tool_data in tools_data
        }
        
        logger.info(f"Discovered {len(self._tools)} tools")
        return list(self._tools.values())
    
    async def discover_resources(self) -> List[ResourceDefinition]:
        """Discover available resources from the server."""
        if not self.server_capabilities or not self.server_capabilities.resources:
            logger.warning("Server does not support resources")
            return []
        
        request = MCPRequest(method="resources/list")
        response = await self._send_request(request)
        
        resources_data = response.get("resources", [])
        self._resources = {
            resource_data["uri"]: ResourceDefinition.from_dict(resource_data)
            for resource_data in resources_data
        }
        
        logger.info(f"Discovered {len(self._resources)} resources")
        return list(self._resources.values())
    
    async def discover_prompts(self) -> List[PromptDefinition]:
        """Discover available prompts from the server."""
        if not self.server_capabilities or not self.server_capabilities.prompts:
            logger.warning("Server does not support prompts")
            return []
        
        request = MCPRequest(method="prompts/list")
        response = await self._send_request(request)
        
        prompts_data = response.get("prompts", [])
        self._prompts = {
            prompt_data["name"]: PromptDefinition.from_dict(prompt_data)
            for prompt_data in prompts_data
        }
        
        logger.info(f"Discovered {len(self._prompts)} prompts")
        return list(self._prompts.values())
    
    async def discover_all(self):
        """Discover all capabilities from the server."""
        await asyncio.gather(
            self.discover_tools(),
            self.discover_resources(),
            self.discover_prompts(),
            return_exceptions=True
        )
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the server.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        if name not in self._tools:
            raise ValueError(f"Tool not found: {name}")
        
        request = MCPRequest(
            method="tools/call",
            params={
                "name": name,
                "arguments": arguments
            }
        )
        
        response = await self._send_request(request)
        
        # Extract text from content
        content = response.get("content", [])
        if content and len(content) > 0:
            return content[0].get("text", "")
        
        return None
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        Read a resource from the server.
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource content
        """
        if uri not in self._resources:
            raise ValueError(f"Resource not found: {uri}")
        
        request = MCPRequest(
            method="resources/read",
            params={"uri": uri}
        )
        
        response = await self._send_request(request)
        
        contents = response.get("contents", [])
        if contents and len(contents) > 0:
            return contents[0]
        
        return {}
    
    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        """
        Get a prompt template from the server.
        
        Args:
            name: Prompt name
            arguments: Prompt arguments
            
        Returns:
            Rendered prompt
        """
        if name not in self._prompts:
            raise ValueError(f"Prompt not found: {name}")
        
        request = MCPRequest(
            method="prompts/get",
            params={
                "name": name,
                "arguments": arguments or {}
            }
        )
        
        response = await self._send_request(request)
        
        messages = response.get("messages", [])
        if messages and len(messages) > 0:
            content = messages[0].get("content", {})
            return content.get("text", "")
        
        return ""
    
    def get_tools(self) -> List[ToolDefinition]:
        """Get list of discovered tools."""
        return list(self._tools.values())
    
    def get_resources(self) -> List[ResourceDefinition]:
        """Get list of discovered resources."""
        return list(self._resources.values())
    
    def get_prompts(self) -> List[PromptDefinition]:
        """Get list of discovered prompts."""
        return list(self._prompts.values())
    
    async def _send_request(self, request: MCPRequest) -> Any:
        """
        Send request and wait for response.
        
        Args:
            request: MCP request
            
        Returns:
            Response result
            
        Raises:
            Exception: If request fails
        """
        if not self.transport:
            raise RuntimeError("Not connected to server")
        
        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request.id] = future
        
        try:
            # Send request
            message = MCPProtocol.serialize_message(request)
            await self.transport.send(message)
            
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=30.0)
            
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {request.method}")
            raise
        finally:
            # Clean up
            if request.id in self._pending_requests:
                del self._pending_requests[request.id]
    
    async def _handle_message(self, raw_message: str):
        """
        Handle incoming MCP message.
        
        Args:
            raw_message: Raw JSON-RPC message
        """
        try:
            message = MCPProtocol.parse_message(raw_message)
            
            if isinstance(message, MCPResponse):
                await self._handle_response(message)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
    
    async def _handle_response(self, response: MCPResponse):
        """Handle response message."""
        request_id = response.id
        
        if request_id not in self._pending_requests:
            logger.warning(f"Received response for unknown request: {request_id}")
            return
        
        future = self._pending_requests[request_id]
        
        if response.error:
            error_message = f"{response.error.message} (code: {response.error.code})"
            future.set_exception(Exception(error_message))
        else:
            future.set_result(response.result)
