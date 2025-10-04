"""
Agent Loader - Load agents from YAML manifests.
"""

from __future__ import annotations

import logging
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, Field, validator
from .base import BaseAgent

logger = logging.getLogger(__name__)


class AgentManifest(BaseModel):
    """Agent manifest schema."""
    version: str = Field(..., description="Manifest version")
    agent: AgentConfig

    class Config:
        extra = "allow"


class AgentConfig(BaseModel):
    """Agent configuration schema."""
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    llm: LLMConfig
    tools: list[str] = Field(default_factory=list)
    memory: Optional[MemoryConfig] = None
    policy: Optional[PolicyConfig] = None
    mcp: Optional[MCPConfig] = None

    class Config:
        extra = "allow"


class LLMConfig(BaseModel):
    """LLM configuration schema."""
    provider: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    system_prompt: Optional[str] = None


class MemoryConfig(BaseModel):
    """Memory configuration schema."""
    backend: str = "sqlite"
    store_path: Optional[str] = None
    vector_store: Optional[str] = None


class PolicyConfig(BaseModel):
    """Policy configuration schema."""
    require_approval: bool = False
    rate_limit: Optional[int] = None
    allowed_actions: list[str] = Field(default_factory=list)


class MCPConfig(BaseModel):
    """MCP configuration schema."""
    enabled: bool = False
    transport: str = "stdio"
    port: Optional[int] = None
    expose_tools: bool = True
    external_servers: list[str] = Field(default_factory=list)


class AgentLoader:
    """
    Loader for agents from YAML manifests.
    
    Parses manifest files and instantiates agents with configuration.
    """
    
    def __init__(self):
        """Initialize agent loader."""
        self._agent_registry: Dict[str, Type[BaseAgent]] = {}
    
    def register_agent_class(self, agent_class: Type[BaseAgent]):
        """
        Register an agent class for loading.
        
        Args:
            agent_class: Agent class to register
        """
        self._agent_registry[agent_class.__name__] = agent_class
        logger.debug(f"Registered agent class: {agent_class.__name__}")
    
    def load_from_file(self, manifest_path: str | Path) -> BaseAgent:
        """
        Load agent from manifest file.
        
        Args:
            manifest_path: Path to agent.yaml manifest
            
        Returns:
            Instantiated agent
        """
        manifest_path = Path(manifest_path)
        
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")
        
        # Load YAML
        with open(manifest_path) as f:
            data = yaml.safe_load(f)
        
        # Validate manifest
        manifest = AgentManifest(**data)
        
        # Load agent
        return self._instantiate_agent(manifest, manifest_path.parent)
    
    def load_from_dict(self, config: Dict[str, Any]) -> BaseAgent:
        """
        Load agent from configuration dictionary.
        
        Args:
            config: Agent configuration
            
        Returns:
            Instantiated agent
        """
        manifest = AgentManifest(**config)
        return self._instantiate_agent(manifest, Path.cwd())
    
    def _instantiate_agent(self, manifest: AgentManifest, base_path: Path) -> BaseAgent:
        """
        Instantiate agent from manifest.
        
        Args:
            manifest: Validated manifest
            base_path: Base path for relative file references
            
        Returns:
            Instantiated agent
        """
        config = manifest.agent
        
        # Determine agent class
        # For now, we'll create a generic agent wrapper
        # In production, this would look up the agent class by name
        
        agent = DynamicAgent(
            name=config.name,
            version=config.version,
            description=config.description,
            config=config.dict()
        )
        
        # Configure MCP if enabled
        if config.mcp and config.mcp.enabled:
            agent.to_mcp_server()
        
        logger.info(f"Loaded agent: {config.name} v{config.version}")
        
        return agent


class DynamicAgent(BaseAgent):
    """
    Dynamic agent created from manifest.
    
    This is a generic agent wrapper that loads configuration
    from manifests and provides basic functionality.
    """
    
    def __init__(self, name: str, version: str, description: str, config: Dict[str, Any]):
        """
        Initialize dynamic agent.
        
        Args:
            name: Agent name
            version: Agent version
            description: Agent description
            config: Full configuration dictionary
        """
        super().__init__(name, version, description)
        self.config = config
    
    async def process(self, input: str, context: Optional[Any] = None) -> str:
        """
        Process input.
        
        Args:
            input: Input text
            context: Execution context
            
        Returns:
            Response text
        """
        # Basic implementation - override with actual logic
        return f"Processed by {self.name}: {input}"
