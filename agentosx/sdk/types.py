"""
Type Definitions for AgentOSX SDK.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# Pydantic models for validation

class ToolConfig(BaseModel):
    """Tool configuration."""
    name: str
    description: str
    input_schema: Optional[Dict[str, Any]] = None
    function: Optional[str] = None


class MCPServerConfig(BaseModel):
    """MCP server configuration."""
    enabled: bool = False
    transport: str = "stdio"
    port: Optional[int] = None
    capabilities: Dict[str, bool] = field(default_factory=lambda: {
        "tools": True,
        "resources": True,
        "prompts": True,
        "streaming": True
    })


class LLMProviderConfig(BaseModel):
    """LLM provider configuration."""
    provider: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    streaming: bool = False


class MemoryConfig(BaseModel):
    """Memory configuration."""
    backend: str = "sqlite"
    path: Optional[str] = None
    vector_store: Optional[str] = None
    embedding_model: Optional[str] = None


class AgentConfig(BaseModel):
    """Complete agent configuration."""
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    
    llm: LLMProviderConfig
    tools: List[ToolConfig] = field(default_factory=list)
    memory: Optional[MemoryConfig] = None
    mcp: Optional[MCPServerConfig] = None
    
    system_prompt: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# Dataclass types

@dataclass
class TaskConfig:
    """Task configuration."""
    name: str
    description: str
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowStep:
    """Workflow step definition."""
    id: str
    type: str  # "agent", "tool", "condition", etc.
    config: Dict[str, Any] = field(default_factory=dict)
    next_steps: List[str] = field(default_factory=list)


@dataclass
class WorkflowConfig:
    """Workflow configuration."""
    name: str
    description: str
    steps: List[WorkflowStep] = field(default_factory=list)
    entry_point: str = "start"
