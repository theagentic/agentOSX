"""
MCP Tool Adapter.

Converts agentOSX tools to MCP format and handles execution.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional

from ..protocol import ToolDefinition, ErrorCode

logger = logging.getLogger(__name__)


class ToolAdapter:
    """
    Adapter for converting Python functions to MCP tools.
    
    Automatically infers JSON Schema from type hints and docstrings.
    """
    
    def __init__(self):
        """Initialize tool adapter."""
        self._tools: Dict[str, Dict[str, Any]] = {}
    
    def register_tool(
        self,
        name: str,
        description: str,
        func: Callable,
        input_schema: Optional[Dict[str, Any]] = None,
    ):
        """
        Register a tool function.
        
        Args:
            name: Tool name
            description: Tool description
            func: Tool function (sync or async)
            input_schema: Optional JSON Schema for inputs (auto-inferred if not provided)
        """
        # Auto-generate schema if not provided
        if input_schema is None:
            input_schema = self._infer_schema(func)
        
        self._tools[name] = {
            "name": name,
            "description": description,
            "func": func,
            "inputSchema": input_schema,
            "is_async": asyncio.iscoroutinefunction(func),
        }
        
        logger.debug(f"Registered tool: {name}")
    
    def unregister_tool(self, name: str):
        """Unregister a tool."""
        if name in self._tools:
            del self._tools[name]
            logger.debug(f"Unregistered tool: {name}")
    
    def list_tools(self) -> List[ToolDefinition]:
        """
        List all registered tools.
        
        Returns:
            List of tool definitions
        """
        return [
            ToolDefinition(
                name=tool["name"],
                description=tool["description"],
                inputSchema=tool["inputSchema"],
            )
            for tool in self._tools.values()
        ]
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool with given arguments.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool not found
            Exception: If tool execution fails
        """
        if name not in self._tools:
            raise ValueError(f"Tool not found: {name}")
        
        tool = self._tools[name]
        func = tool["func"]
        is_async = tool["is_async"]
        
        try:
            # Validate arguments against schema
            self._validate_arguments(tool["inputSchema"], arguments)
            
            # Execute tool
            if is_async:
                result = await func(**arguments)
            else:
                # Run sync function in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: func(**arguments))
            
            logger.debug(f"Tool {name} executed successfully")
            return result
        
        except Exception as e:
            logger.error(f"Tool execution error ({name}): {e}", exc_info=True)
            raise
    
    def _infer_schema(self, func: Callable) -> Dict[str, Any]:
        """
        Infer JSON Schema from function signature.
        
        Args:
            func: Function to analyze
            
        Returns:
            JSON Schema for function parameters
        """
        sig = inspect.signature(func)
        
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            # Skip self/cls parameters
            if param_name in ("self", "cls"):
                continue
            
            param_schema = {}
            
            # Infer type from annotation
            if param.annotation != inspect.Parameter.empty:
                param_schema["type"] = self._python_type_to_json_type(param.annotation)
            else:
                param_schema["type"] = "string"  # Default to string
            
            # Add description from docstring if available
            doc = inspect.getdoc(func)
            if doc:
                # Simple extraction - look for "param_name: description" pattern
                for line in doc.split("\n"):
                    if f"{param_name}:" in line:
                        desc = line.split(":", 1)[1].strip()
                        param_schema["description"] = desc
                        break
            
            properties[param_name] = param_schema
            
            # Required if no default value
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        schema = {
            "type": "object",
            "properties": properties,
        }
        
        if required:
            schema["required"] = required
        
        return schema
    
    def _python_type_to_json_type(self, python_type: type) -> str:
        """Convert Python type to JSON Schema type."""
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }
        
        # Handle Optional/Union types
        if hasattr(python_type, "__origin__"):
            origin = python_type.__origin__
            if origin is list:
                return "array"
            elif origin is dict:
                return "object"
        
        # Get base type
        if hasattr(python_type, "__mro__"):
            for base_type, json_type in type_map.items():
                if issubclass(python_type, base_type):
                    return json_type
        
        return "string"  # Default fallback
    
    def _validate_arguments(self, schema: Dict[str, Any], arguments: Dict[str, Any]):
        """
        Validate arguments against JSON Schema.
        
        Args:
            schema: JSON Schema
            arguments: Arguments to validate
            
        Raises:
            ValueError: If validation fails
        """
        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in arguments:
                raise ValueError(f"Missing required argument: {field}")
        
        # Basic type checking
        properties = schema.get("properties", {})
        for key, value in arguments.items():
            if key in properties:
                expected_type = properties[key].get("type")
                actual_type = type(value).__name__
                
                # Map Python types to JSON types for comparison
                type_map = {
                    "str": "string",
                    "int": "integer",
                    "float": "number",
                    "bool": "boolean",
                    "list": "array",
                    "dict": "object",
                }
                
                actual_json_type = type_map.get(actual_type, actual_type)
                
                if expected_type and actual_json_type != expected_type:
                    # Allow number for integer
                    if not (expected_type == "number" and actual_json_type == "integer"):
                        raise ValueError(
                            f"Invalid type for argument '{key}': expected {expected_type}, got {actual_json_type}"
                        )
