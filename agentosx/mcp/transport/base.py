"""
Transport layer base class for MCP.
"""

from abc import ABC, abstractmethod
from typing import Callable, Awaitable


class Transport(ABC):
    """Abstract base class for MCP transport layers."""
    
    @abstractmethod
    async def start(self, message_handler: Callable[[str], Awaitable[None]]):
        """
        Start the transport and begin receiving messages.
        
        Args:
            message_handler: Async function to handle incoming messages
        """
        pass
    
    @abstractmethod
    async def send(self, message: str):
        """
        Send a message through the transport.
        
        Args:
            message: JSON-RPC message string
        """
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop the transport."""
        pass
