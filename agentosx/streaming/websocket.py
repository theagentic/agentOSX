"""
WebSocket Handler for Streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from .events import StreamEvent

try:
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = None

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """
    Handler for WebSocket streaming.
    
    Provides bidirectional streaming over WebSocket connections.
    """
    
    def __init__(self, websocket: Optional[WebSocketServerProtocol] = None):
        """
        Initialize WebSocket handler.
        
        Args:
            websocket: WebSocket connection
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets package not installed")
        
        self.websocket = websocket
        self._active = False
    
    async def send(self, event: StreamEvent):
        """
        Send event through WebSocket.
        
        Args:
            event: Stream event
        """
        if not self.websocket or not self._active:
            logger.warning("WebSocket not active, event dropped")
            return
        
        try:
            message = json.dumps(event.to_dict())
            await self.websocket.send(message)
        
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}", exc_info=True)
    
    async def receive(self) -> Optional[dict]:
        """
        Receive message from WebSocket.
        
        Returns:
            Parsed message dictionary or None
        """
        if not self.websocket or not self._active:
            return None
        
        try:
            message = await self.websocket.recv()
            return json.loads(message)
        
        except Exception as e:
            logger.error(f"Error receiving WebSocket message: {e}", exc_info=True)
            return None
    
    def start(self):
        """Start the handler."""
        self._active = True
    
    def stop(self):
        """Stop the handler."""
        self._active = False
