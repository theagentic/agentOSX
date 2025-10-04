"""
Streaming Event Types for AgentOSX.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class EventType(Enum):
    """Stream event types."""
    AGENT_START = "agent.start"
    AGENT_THINKING = "agent.thinking"
    AGENT_COMPLETE = "agent.complete"
    AGENT_ERROR = "agent.error"
    
    TOOL_CALL_START = "tool.call.start"
    TOOL_CALL_PROGRESS = "tool.call.progress"
    TOOL_CALL_COMPLETE = "tool.call.complete"
    TOOL_CALL_ERROR = "tool.call.error"
    
    LLM_TOKEN = "llm.token"
    LLM_COMPLETE = "llm.complete"
    LLM_ERROR = "llm.error"
    
    MEMORY_UPDATE = "memory.update"
    STATE_CHANGE = "state.change"


@dataclass
class StreamEvent:
    """Base stream event."""
    type: EventType
    data: Dict[str, Any]
    timestamp: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "metadata": self.metadata or {}
        }
    
    def to_sse(self) -> str:
        """Convert to Server-Sent Events format."""
        return f"event: {self.type.value}\ndata: {self.data}\n\n"
    
    def to_vercel_format(self) -> Dict[str, Any]:
        """Convert to Vercel AI SDK format."""
        # Map to Vercel AI SDK event format
        if self.type == EventType.LLM_TOKEN:
            return {
                "type": "text",
                "text": self.data.get("token", "")
            }
        elif self.type == EventType.TOOL_CALL_START:
            return {
                "type": "tool_call",
                "tool_call": {
                    "id": self.data.get("id"),
                    "name": self.data.get("name"),
                    "arguments": self.data.get("arguments", {})
                }
            }
        elif self.type == EventType.TOOL_CALL_COMPLETE:
            return {
                "type": "tool_result",
                "tool_result": {
                    "id": self.data.get("id"),
                    "result": self.data.get("result")
                }
            }
        else:
            return self.to_dict()


class TextEvent(StreamEvent):
    """Text stream event for token-by-token streaming."""
    
    def __init__(
        self,
        text: str,
        agent_id: Optional[str] = None,
        is_complete: bool = False,
        timestamp: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize text event."""
        data = {
            "text": text,
            "agent_id": agent_id,
            "complete": is_complete
        }
        super().__init__(
            type=EventType.LLM_TOKEN,
            data=data,
            timestamp=timestamp,
            metadata=metadata
        )
        self.text = text
        self.agent_id = agent_id
        self.is_complete = is_complete


@dataclass
class AgentStartEvent(StreamEvent):
    """Agent start event."""
    def __init__(self, agent_name: str, **kwargs):
        super().__init__(
            type=EventType.AGENT_START,
            data={"agent_name": agent_name},
            **kwargs
        )


@dataclass
class TokenEvent(StreamEvent):
    """Token stream event."""
    def __init__(self, token: str, **kwargs):
        super().__init__(
            type=EventType.LLM_TOKEN,
            data={"token": token},
            **kwargs
        )


@dataclass
class ToolCallEvent(StreamEvent):
    """Tool call event."""
    def __init__(self, tool_name: str, arguments: Dict[str, Any], call_id: str, **kwargs):
        super().__init__(
            type=EventType.TOOL_CALL_START,
            data={
                "id": call_id,
                "name": tool_name,
                "arguments": arguments
            },
            **kwargs
        )
