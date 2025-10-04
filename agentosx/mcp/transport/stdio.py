"""
STDIO Transport for MCP.

Uses stdin/stdout for communication, following the JSON-RPC over STDIO pattern
used by Language Server Protocol and MCP reference implementations.
"""

import asyncio
import sys
import logging
from typing import Callable, Awaitable, Optional

from .base import Transport

logger = logging.getLogger(__name__)


class StdioTransport(Transport):
    """
    STDIO transport for MCP communication.
    
    Reads JSON-RPC messages from stdin and writes to stdout.
    Each message is newline-delimited.
    """
    
    def __init__(self):
        """Initialize STDIO transport."""
        self._running = False
        self._message_handler: Optional[Callable[[str], Awaitable[None]]] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def start(self, message_handler: Callable[[str], Awaitable[None]]):
        """
        Start reading from stdin.
        
        Args:
            message_handler: Async function to handle incoming messages
        """
        self._message_handler = message_handler
        self._running = True
        
        logger.info("Starting STDIO transport")
        
        # Start reader task
        self._reader_task = asyncio.create_task(self._read_loop())
        
        # Wait for reader task to complete
        await self._reader_task
    
    async def send(self, message: str):
        """
        Send message to stdout.
        
        Args:
            message: JSON-RPC message string
        """
        async with self._lock:
            try:
                # Write message with newline delimiter
                sys.stdout.write(message + "\n")
                sys.stdout.flush()
                
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
        
        logger.info("STDIO transport stopped")
    
    async def _read_loop(self):
        """Read messages from stdin in a loop."""
        loop = asyncio.get_event_loop()
        
        try:
            while self._running:
                # Read line from stdin in executor to avoid blocking
                line = await loop.run_in_executor(None, sys.stdin.readline)
                
                if not line:
                    # EOF reached
                    logger.info("EOF reached on stdin")
                    break
                
                line = line.strip()
                
                if not line:
                    continue
                
                logger.debug(f"Received message: {line[:100]}...")
                
                # Handle message
                if self._message_handler:
                    try:
                        await self._message_handler(line)
                    except Exception as e:
                        logger.error(f"Error handling message: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"Error in read loop: {e}", exc_info=True)
        
        finally:
            self._running = False
