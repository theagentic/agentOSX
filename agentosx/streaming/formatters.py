"""
Stream Formatters for Various Protocols.
"""

from __future__ import annotations

import json
from typing import Dict, Any
from .events import StreamEvent, EventType


class VercelAIFormatter:
    """
    Formatter for Vercel AI SDK compatibility.
    
    Formats events to work with useChat, useCompletion hooks.
    """
    
    @staticmethod
    def format(event: StreamEvent) -> str:
        """
        Format event for Vercel AI SDK.
        
        Args:
            event: Stream event
            
        Returns:
            Formatted string
        """
        vercel_format = event.to_vercel_format()
        return f"0:{json.dumps(vercel_format)}\n"
    
    @staticmethod
    def format_text(text: str) -> str:
        """Format text chunk."""
        return f'0:{json.dumps({"type": "text", "text": text})}\n'
    
    @staticmethod
    def format_tool_call(tool_name: str, arguments: Dict[str, Any], call_id: str) -> str:
        """Format tool call."""
        return f'0:{json.dumps({"type": "tool_call", "tool_call": {"id": call_id, "name": tool_name, "arguments": arguments}})}\n'
    
    @staticmethod
    def format_error(error: str) -> str:
        """Format error."""
        return f'3:{json.dumps({"error": error})}\n'


class OpenAIFormatter:
    """
    Formatter for OpenAI Chat Completion streaming format.
    """
    
    @staticmethod
    def format(event: StreamEvent) -> str:
        """
        Format event for OpenAI streaming.
        
        Args:
            event: Stream event
            
        Returns:
            Formatted string
        """
        if event.type == EventType.LLM_TOKEN:
            return f'data: {json.dumps({"choices": [{"delta": {"content": event.data.get("token", "")}}]})}\n\n'
        elif event.type == EventType.LLM_COMPLETE:
            return "data: [DONE]\n\n"
        else:
            return ""


class PlainTextFormatter:
    """Simple plain text formatter."""
    
    @staticmethod
    def format(event: StreamEvent) -> str:
        """
        Format event as plain text.
        
        Args:
            event: Stream event
            
        Returns:
            Formatted string
        """
        if event.type == EventType.LLM_TOKEN:
            return event.data.get("token", "")
        elif event.type == EventType.AGENT_START:
            return f"[Agent {event.data.get('agent_name')} starting]\n"
        elif event.type == EventType.TOOL_CALL_START:
            return f"[Calling tool: {event.data.get('name')}]\n"
        elif event.type == EventType.TOOL_CALL_COMPLETE:
            return f"[Tool result: {event.data.get('result')}]\n"
        else:
            return ""
