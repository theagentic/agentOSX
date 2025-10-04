"""
Agent Decorators.

Provides decorator-based API for agent development.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


def agent(
    name: Optional[str] = None,
    version: str = "1.0.0",
    description: Optional[str] = None,
):
    """
    Decorator to mark a class as an agent.
    
    Args:
        name: Agent name (defaults to class name)
        version: Agent version
        description: Agent description
        
    Returns:
        Decorator function
    """
    def decorator(cls):
        # Store metadata on class
        cls._agent_name = name or cls.__name__
        cls._agent_version = version
        cls._agent_description = description
        
        return cls
    
    return decorator


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    schema: Optional[Dict[str, Any]] = None,
):
    """
    Decorator to mark a method as a tool.
    
    Args:
        name: Tool name (defaults to function name)
        description: Tool description
        schema: Input schema
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        # Store tool metadata
        func._is_tool = True
        func._tool_name = name or func.__name__
        func._tool_description = description or func.__doc__ or ""
        func._tool_schema = schema
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.debug(f"Executing tool: {func._tool_name}")
            return await func(*args, **kwargs)
        
        # Copy metadata to wrapper
        wrapper._is_tool = func._is_tool
        wrapper._tool_name = func._tool_name
        wrapper._tool_description = func._tool_description
        wrapper._tool_schema = func._tool_schema
        
        return wrapper
    
    return decorator


def hook(event: str):
    """
    Decorator to register a lifecycle hook.
    
    Args:
        event: Event name (on_init, on_start, etc.)
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        func._is_hook = True
        func._hook_event = event
        return func
    
    return decorator


def streaming(func: Callable) -> Callable:
    """
    Decorator to mark a method as streaming-capable.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    func._is_streaming = True
    return func
