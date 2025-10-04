"""
WebSocket Transport for MCP.

Provides bidirectional WebSocket communication.
"""

import asyncio
import logging
from typing import Callable, Awaitable, Optional

from .base import Transport

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    from websockets.client import WebSocketClientProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = None
    WebSocketClientProtocol = None

logger = logging.getLogger(__name__)


class WebSocketTransport(Transport):
    """
    WebSocket transport for MCP communication.
    
    Supports both client and server modes.
    """
    
    def __init__(
        self,
        websocket: Optional[WebSocketServerProtocol | WebSocketClientProtocol] = None,
        uri: Optional[str] = None,
    ):
        """
        Initialize WebSocket transport.
        
        Args:
            websocket: Existing WebSocket connection (server mode)
            uri: WebSocket URI to connect to (client mode)
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets package not installed. Install with: pip install websockets")
        
        self.websocket = websocket
        self.uri = uri
        self._running = False
        self._message_handler: Optional[Callable[[str], Awaitable[None]]] = None
        self._reader_task: Optional[asyncio.Task] = None
    
    async def start(self, message_handler: Callable[[str], Awaitable[None]]):
        """
        Start WebSocket transport.
        
        Args:
            message_handler: Async function to handle incoming messages
        """
        self._message_handler = message_handler
        self._running = True
        
        # Connect if in client mode
        if self.uri and not self.websocket:
            logger.info(f"Connecting to WebSocket: {self.uri}")
            self.websocket = await websockets.connect(self.uri)
        
        if not self.websocket:
            raise RuntimeError("No WebSocket connection available")
        
        logger.info("Starting WebSocket transport")
        
        # Start reader task
        self._reader_task = asyncio.create_task(self._read_loop())
        
        # Wait for reader task
        await self._reader_task
    
    async def send(self, message: str):
        """
        Send message through WebSocket.
        
        Args:
            message: JSON-RPC message string
        """
        if not self.websocket:
            raise RuntimeError("WebSocket not connected")
        
        try:
            await self.websocket.send(message)
            logger.debug(f"Sent message: {message[:100]}...")
        
        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)
            raise
    
    async def stop(self):
        """Stop the transport."""
        self._running = False
        
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            await self.websocket.close()
        
        logger.info("WebSocket transport stopped")
    
    async def _read_loop(self):
        """Read messages from WebSocket in a loop."""
        try:
            async for message in self.websocket:
                if not self._running:
                    break
                
                logger.debug(f"Received message: {message[:100]}...")
                
                # Handle message
                if self._message_handler:
                    try:
                        await self._message_handler(message)
                    except Exception as e:
                        logger.error(f"Error handling message: {e}", exc_info=True)
        
        except Exception as e:
            if self._running:
                logger.error(f"Error in read loop: {e}", exc_info=True)
        
        finally:
            self._running = False
