"""
Fluent Agent Builder for AgentOSX.

Provides a chainable API for building agents.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from ..agents.base import BaseAgent
from ..agents.loader import DynamicAgent
from .types import AgentConfig, ToolConfig, MCPServerConfig, LLMProviderConfig

logger = logging.getLogger(__name__)


class AgentBuilder:
    """
    Fluent API for building agents.
    
    Example:
        agent = (
            AgentBuilder()
            .name("my-agent")
            .llm("anthropic", "claude-3-sonnet")
            .tool("search", search_func)
            .build()
        )
    """
    
    def __init__(self):
        """Initialize agent builder."""
        self._name: Optional[str] = None
        self._version: str = "1.0.0"
        self._description: Optional[str] = None
        
        self._llm_config: Optional[LLMProviderConfig] = None
        self._tools: List[ToolConfig] = []
        self._tool_functions: Dict[str, Callable] = {}
        self._mcp_config: Optional[MCPServerConfig] = None
        self._system_prompt: Optional[str] = None
        self._metadata: Dict[str, Any] = {}
    
    def name(self, name: str) -> AgentBuilder:
        """
        Set agent name.
        
        Args:
            name: Agent name
            
        Returns:
            Builder instance for chaining
        """
        self._name = name
        return self
    
    def version(self, version: str) -> AgentBuilder:
        """
        Set agent version.
        
        Args:
            version: Version string
            
        Returns:
            Builder instance
        """
        self._version = version
        return self
    
    def description(self, description: str) -> AgentBuilder:
        """
        Set agent description.
        
        Args:
            description: Description text
            
        Returns:
            Builder instance
        """
        self._description = description
        return self
    
    def llm(
        self,
        provider: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> AgentBuilder:
        """
        Configure LLM provider.
        
        Args:
            provider: Provider name (e.g., "anthropic", "openai")
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Additional provider-specific config
            
        Returns:
            Builder instance
        """
        self._llm_config = LLMProviderConfig(
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return self
    
    def tool(
        self,
        name: str,
        func: Callable,
        description: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
    ) -> AgentBuilder:
        """
        Add a tool to the agent.
        
        Args:
            name: Tool name
            func: Tool function
            description: Tool description
            schema: Input schema
            
        Returns:
            Builder instance
        """
        self._tools.append(ToolConfig(
            name=name,
            description=description or func.__doc__ or f"Tool: {name}",
            input_schema=schema
        ))
        self._tool_functions[name] = func
        return self
    
    def mcp_server(
        self,
        transport: str = "stdio",
        port: Optional[int] = None,
        **capabilities
    ) -> AgentBuilder:
        """
        Enable MCP server.
        
        Args:
            transport: Transport type ("stdio", "sse", "websocket")
            port: Port number (for network transports)
            **capabilities: Capability flags
            
        Returns:
            Builder instance
        """
        self._mcp_config = MCPServerConfig(
            enabled=True,
            transport=transport,
            port=port,
            capabilities=capabilities or {
                "tools": True,
                "resources": True,
                "prompts": True,
                "streaming": True
            }
        )
        return self
    
    def system_prompt(self, prompt: str) -> AgentBuilder:
        """
        Set system prompt.
        
        Args:
            prompt: System prompt text
            
        Returns:
            Builder instance
        """
        self._system_prompt = prompt
        return self
    
    def metadata(self, key: str, value: Any) -> AgentBuilder:
        """
        Add metadata.
        
        Args:
            key: Metadata key
            value: Metadata value
            
        Returns:
            Builder instance
        """
        self._metadata[key] = value
        return self
    
    def build(self) -> BaseAgent:
        """
        Build the agent.
        
        Returns:
            Configured agent instance
            
        Raises:
            ValueError: If required configuration is missing
        """
        if not self._name:
            raise ValueError("Agent name is required")
        
        if not self._llm_config:
            raise ValueError("LLM configuration is required")
        
        # Create agent config
        config = AgentConfig(
            name=self._name,
            version=self._version,
            description=self._description,
            llm=self._llm_config,
            tools=self._tools,
            mcp=self._mcp_config,
            system_prompt=self._system_prompt,
            metadata=self._metadata
        )
        
        # Create agent
        agent = DynamicAgent(
            name=self._name,
            version=self._version,
            description=self._description or f"{self._name} agent",
            config=config.dict()
        )
        
        # Register tools
        if self._mcp_config and self._mcp_config.enabled:
            mcp_server = agent.to_mcp_server()
            
            for tool_name, tool_func in self._tool_functions.items():
                tool_config = next((t for t in self._tools if t.name == tool_name), None)
                if tool_config:
                    mcp_server.register_tool(
                        name=tool_name,
                        description=tool_config.description,
                        func=tool_func,
                        input_schema=tool_config.input_schema
                    )
        
        logger.info(f"Built agent: {self._name}")
        
        return agent
