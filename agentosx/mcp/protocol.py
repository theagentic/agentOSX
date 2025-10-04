"""
MCP Protocol Implementation - JSON-RPC 2.0 based.

Implements the Model Context Protocol specification for bi-directional
tool and resource sharing between agents and MCP servers.
"""

from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Literal


class ErrorCode(Enum):
    """Standard JSON-RPC 2.0 and MCP-specific error codes."""
    # JSON-RPC 2.0 standard errors
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP-specific errors
    TOOL_NOT_FOUND = -32001
    TOOL_EXECUTION_ERROR = -32002
    RESOURCE_NOT_FOUND = -32003
    RESOURCE_ACCESS_ERROR = -32004
    PROMPT_NOT_FOUND = -32005
    CAPABILITY_NOT_SUPPORTED = -32006
    UNAUTHORIZED = -32007
    RATE_LIMIT_EXCEEDED = -32008


@dataclass
class MCPCapabilities:
    """MCP server/client capabilities."""
    tools: bool = False
    resources: bool = False
    prompts: bool = False
    streaming: bool = False
    version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MCPMessage(ABC):
    """Base class for all MCP messages."""
    jsonrpc: str = "2.0"
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for JSON serialization."""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> MCPMessage:
        """Create message from dictionary."""
        pass


@dataclass
class MCPRequest(MCPMessage):
    """MCP request message (expects a response)."""
    method: str = ""
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        data = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "id": self.id,
        }
        if self.params is not None:
            data["params"] = self.params
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MCPRequest:
        return cls(
            method=data["method"],
            params=data.get("params"),
            id=data.get("id"),
        )


@dataclass
class MCPResponse(MCPMessage):
    """MCP response message."""
    id: Union[str, int] = ""
    result: Optional[Any] = None
    error: Optional[MCPError] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
        }
        if self.error:
            data["error"] = self.error.to_dict()
        else:
            data["result"] = self.result
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MCPResponse:
        error = None
        if "error" in data:
            error = MCPError.from_dict(data["error"])
        
        return cls(
            id=data["id"],
            result=data.get("result"),
            error=error,
        )


@dataclass
class MCPNotification(MCPMessage):
    """MCP notification message (no response expected)."""
    method: str = ""
    params: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
        }
        if self.params is not None:
            data["params"] = self.params
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MCPNotification:
        return cls(
            method=data["method"],
            params=data.get("params"),
        )


@dataclass
class MCPError:
    """MCP error object."""
    code: int
    message: str
    data: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        error_dict = {
            "code": self.code,
            "message": self.message,
        }
        if self.data is not None:
            error_dict["data"] = self.data
        return error_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MCPError:
        return cls(
            code=data["code"],
            message=data["message"],
            data=data.get("data"),
        )
    
    @classmethod
    def from_error_code(cls, error_code: ErrorCode, message: Optional[str] = None, data: Optional[Any] = None) -> MCPError:
        """Create error from ErrorCode enum."""
        return cls(
            code=error_code.value,
            message=message or error_code.name,
            data=data,
        )


@dataclass
class ToolDefinition:
    """MCP tool definition."""
    name: str
    description: str
    inputSchema: Dict[str, Any]  # JSON Schema
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.inputSchema,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ToolDefinition:
        return cls(
            name=data["name"],
            description=data["description"],
            inputSchema=data["inputSchema"],
        )


@dataclass
class ResourceDefinition:
    """MCP resource definition."""
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = {
            "uri": self.uri,
            "name": self.name,
        }
        if self.description:
            data["description"] = self.description
        if self.mimeType:
            data["mimeType"] = self.mimeType
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ResourceDefinition:
        return cls(
            uri=data["uri"],
            name=data["name"],
            description=data.get("description"),
            mimeType=data.get("mimeType"),
        )


@dataclass
class PromptDefinition:
    """MCP prompt template definition."""
    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = {"name": self.name}
        if self.description:
            data["description"] = self.description
        if self.arguments:
            data["arguments"] = self.arguments
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PromptDefinition:
        return cls(
            name=data["name"],
            description=data.get("description"),
            arguments=data.get("arguments"),
        )


class MCPProtocol:
    """
    MCP Protocol handler for message parsing and validation.
    
    Implements JSON-RPC 2.0 with MCP-specific extensions.
    """
    
    VERSION = "1.0.0"
    
    @staticmethod
    def parse_message(raw_message: Union[str, bytes, Dict[str, Any]]) -> Union[MCPRequest, MCPResponse, MCPNotification]:
        """
        Parse raw message into appropriate MCP message type.
        
        Args:
            raw_message: Raw JSON string, bytes, or dict
            
        Returns:
            Parsed MCP message
            
        Raises:
            ValueError: If message is invalid
        """
        if isinstance(raw_message, (str, bytes)):
            try:
                data = json.loads(raw_message)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}")
        else:
            data = raw_message
        
        # Validate JSON-RPC version
        if data.get("jsonrpc") != "2.0":
            raise ValueError("Invalid JSON-RPC version")
        
        # Determine message type
        if "method" in data:
            if "id" in data:
                return MCPRequest.from_dict(data)
            else:
                return MCPNotification.from_dict(data)
        elif "result" in data or "error" in data:
            return MCPResponse.from_dict(data)
        else:
            raise ValueError("Unknown message type")
    
    @staticmethod
    def serialize_message(message: MCPMessage) -> str:
        """Serialize MCP message to JSON string."""
        return json.dumps(message.to_dict())
    
    @staticmethod
    def create_success_response(request_id: Union[str, int], result: Any) -> MCPResponse:
        """Create a successful response."""
        return MCPResponse(id=request_id, result=result)
    
    @staticmethod
    def create_error_response(
        request_id: Union[str, int],
        error_code: ErrorCode,
        message: Optional[str] = None,
        data: Optional[Any] = None
    ) -> MCPResponse:
        """Create an error response."""
        error = MCPError.from_error_code(error_code, message, data)
        return MCPResponse(id=request_id, error=error)
    
    @staticmethod
    def validate_capabilities(
        required: MCPCapabilities,
        available: MCPCapabilities
    ) -> bool:
        """Check if required capabilities are available."""
        if required.tools and not available.tools:
            return False
        if required.resources and not available.resources:
            return False
        if required.prompts and not available.prompts:
            return False
        if required.streaming and not available.streaming:
            return False
        return True
    
    @staticmethod
    def negotiate_capabilities(
        client_caps: MCPCapabilities,
        server_caps: MCPCapabilities
    ) -> MCPCapabilities:
        """Negotiate capabilities between client and server."""
        return MCPCapabilities(
            tools=client_caps.tools and server_caps.tools,
            resources=client_caps.resources and server_caps.resources,
            prompts=client_caps.prompts and server_caps.prompts,
            streaming=client_caps.streaming and server_caps.streaming,
            version=min(client_caps.version, server_caps.version),
        )
