"""
Abstract base class for LLM providers.
Defines the interface all providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Iterator, Union
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid


class Role(Enum):
    """Message roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ToolCall:
    """Represents a tool/function call."""
    id: str
    name: str
    arguments: Dict[str, Any]
    
    @classmethod
    def create(cls, name: str, arguments: Dict[str, Any]) -> "ToolCall":
        """Create a new tool call with generated ID."""
        return cls(
            id=f"call_{uuid.uuid4().hex[:8]}",
            name=name,
            arguments=arguments
        )


@dataclass
class Message:
    """Unified message format across all providers."""
    role: Role
    content: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_call_id: Optional[str] = None  # For tool responses
    name: Optional[str] = None  # For function/tool messages
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = {
            "role": self.role.value,
            "content": self.content
        }
        if self.tool_calls:
            data["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": tc.arguments
                    }
                } for tc in self.tool_calls
            ]
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        if self.name:
            data["name"] = self.name
        return data


@dataclass
class Tool:
    """Tool/function definition."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to OpenAI-compatible tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


@dataclass
class Usage:
    """Token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    @property
    def cost_estimate(self) -> float:
        """Estimate cost in USD (override per provider)."""
        # Default rough estimate
        return (self.prompt_tokens * 0.01 + self.completion_tokens * 0.03) / 1000


@dataclass
class CompletionResponse:
    """Response from LLM completion."""
    message: Message
    usage: Optional[Usage] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamDelta:
    """Delta for streaming responses."""
    content: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    finish_reason: Optional[str] = None
    usage: Optional[Usage] = None


class BaseLLM(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self._last_request_time = 0
        self._request_count = 0
    
    @abstractmethod
    def generate(
        self,
        model: str,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        json_mode: bool = False,
        timeout: Optional[int] = None,
        **kwargs
    ) -> CompletionResponse:
        """
        Generate a completion from the LLM.
        
        Args:
            model: Model identifier
            messages: Conversation history
            tools: Available tools/functions
            system_prompt: System instruction
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            json_mode: Force JSON output
            timeout: Request timeout in seconds
            **kwargs: Provider-specific parameters
        
        Returns:
            CompletionResponse with generated message
        """
        pass
    
    @abstractmethod
    def stream(
        self,
        model: str,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        json_mode: bool = False,
        timeout: Optional[int] = None,
        **kwargs
    ) -> Iterator[StreamDelta]:
        """
        Stream a completion from the LLM.
        
        Yields:
            StreamDelta objects with incremental content
        """
        pass
    
    def tool_call(
        self,
        model: str,
        messages: List[Message],
        tools: List[Tool],
        system_prompt: Optional[str] = None,
        max_iterations: int = 5,
        **kwargs
    ) -> CompletionResponse:
        """
        Execute tool calls with the LLM.
        
        Default implementation that can be overridden by providers.
        """
        # Add system prompt if provided
        if system_prompt:
            messages = [
                Message(role=Role.SYSTEM, content=system_prompt),
                *messages
            ]
        
        for _ in range(max_iterations):
            # Generate with tools
            response = self.generate(
                model=model,
                messages=messages,
                tools=tools,
                **kwargs
            )
            
            # If no tool calls, we're done
            if not response.message.tool_calls:
                return response
            
            # Execute tool calls (this would be handled by the tool registry)
            # For now, return the response with tool calls
            return response
        
        # Max iterations reached
        return response
    
    def _apply_rate_limit(self, requests_per_minute: int = 60):
        """Apply basic rate limiting."""
        min_interval = 60.0 / requests_per_minute
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()
        self._request_count += 1
    
    @abstractmethod
    def validate_model(self, model: str) -> bool:
        """Check if a model is supported by this provider."""
        pass
    
    @abstractmethod
    def list_models(self) -> List[str]:
        """List available models for this provider."""
        pass
    
    def estimate_cost(self, usage: Usage, model: str) -> float:
        """Estimate cost for the given usage and model."""
        # Override in provider implementations with actual pricing
        return usage.cost_estimate
