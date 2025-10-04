"""
Server-Sent Events (SSE) Handler for Streaming.
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator, Optional
from .events import StreamEvent

logger = logging.getLogger(__name__)


class SSEHandler:
    """
    Handler for Server-Sent Events streaming.
    
    Formats stream events as SSE for consumption by web clients.
    """
    
    def __init__(self):
        """Initialize SSE handler."""
        self._queue: asyncio.Queue = asyncio.Queue()
        self._active = False
    
    async def send(self, event: StreamEvent):
        """
        Send an event to the stream.
        
        Args:
            event: Stream event to send
        """
        if not self._active:
            logger.warning("SSE handler not active, event dropped")
            return
        
        await self._queue.put(event)
    
    async def stream(self) -> AsyncIterator[str]:
        """
        Generate SSE stream.
        
        Yields:
            SSE-formatted event strings
        """
        self._active = True
        
        try:
            while self._active:
                try:
                    # Get event with timeout
                    event = await asyncio.wait_for(self._queue.get(), timeout=30.0)
                    
                    # Format as SSE
                    yield event.to_sse()
                
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield ": keepalive\n\n"
        
        except Exception as e:
            logger.error(f"SSE streaming error: {e}", exc_info=True)
        
        finally:
            self._active = False
    
    def stop(self):
        """Stop the SSE handler."""
        self._active = False
