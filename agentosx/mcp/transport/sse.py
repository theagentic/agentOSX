"""
Server-Sent Events (SSE) Transport for MCP.

Provides HTTP-based SSE transport for real-time communication.
"""

import asyncio
import logging
from typing import Callable, Awaitable, Optional, Dict, Any
from collections import deque

from .base import Transport

logger = logging.getLogger(__name__)


class SSETransport(Transport):
    """
    SSE transport for MCP communication.
    
    Uses Server-Sent Events for server-to-client streaming and
    regular HTTP POST for client-to-server messages.
    
    Note: This requires integration with an HTTP server (e.g., FastAPI, Starlette).
    """
    
    def __init__(self, client_id: Optional[str] = None):
        """
        Initialize SSE transport.
        
        Args:
            client_id: Unique client identifier
        """
        self.client_id = client_id
        self._running = False
        self._message_handler: Optional[Callable[[str], Awaitable[None]]] = None
        self._outgoing_queue: deque = deque()
        self._event_available = asyncio.Event()
    
    async def start(self, message_handler: Callable[[str], Awaitable[None]]):
        """
        Start the SSE transport.
        
        Args:
            message_handler: Async function to handle incoming messages
        """
        self._message_handler = message_handler
        self._running = True
        
        logger.info(f"Starting SSE transport for client: {self.client_id}")
    
    async def send(self, message: str):
        """
        Queue message for SSE delivery.
        
        Args:
            message: JSON-RPC message string
        """
        if not self._running:
            raise RuntimeError("Transport not running")
        
        self._outgoing_queue.append(message)
        self._event_available.set()
        
        logger.debug(f"Queued SSE message: {message[:100]}...")
    
    async def stop(self):
        """Stop the transport."""
        self._running = False
        self._event_available.set()  # Wake up any waiting readers
        
        logger.info("SSE transport stopped")
    
    async def receive_message(self, message: str):
        """
        Receive incoming message from HTTP POST.
        
        Args:
            message: JSON-RPC message string
        """
        if self._message_handler:
            await self._message_handler(message)
    
    async def event_stream(self):
        """
        Generate SSE event stream.
        
        Yields:
            SSE-formatted events
        """
        try:
            while self._running:
                # Wait for messages or timeout
                try:
                    await asyncio.wait_for(self._event_available.wait(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield ": keepalive\n\n"
                    continue
                
                # Send all queued messages
                while self._outgoing_queue:
                    message = self._outgoing_queue.popleft()
                    # Format as SSE event
                    yield f"data: {message}\n\n"
                
                # Clear event if queue is empty
                if not self._outgoing_queue:
                    self._event_available.clear()
        
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}", exc_info=True)
        
        finally:
            await self.stop()
    
    def has_messages(self) -> bool:
        """Check if there are pending messages."""
        return len(self._outgoing_queue) > 0
