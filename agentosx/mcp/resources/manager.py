"""
MCP Resource Manager.

Manages resource definitions and content providers.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Awaitable
import asyncio

from ..protocol import ResourceDefinition

logger = logging.getLogger(__name__)


class ResourceManager:
    """
    Manager for MCP resources.
    
    Resources are addressable content (files, data, artifacts) that
    can be read by MCP clients.
    """
    
    def __init__(self):
        """Initialize resource manager."""
        self._resources: Dict[str, Dict[str, Any]] = {}
    
    def register_resource(
        self,
        uri: str,
        name: str,
        description: Optional[str] = None,
        mime_type: Optional[str] = None,
        reader: Optional[Callable] = None,
    ):
        """
        Register a resource.
        
        Args:
            uri: Resource URI (e.g., 'agent://twitter/tweets/123')
            name: Resource name
            description: Resource description
            mime_type: MIME type of resource content
            reader: Function to read resource content (sync or async)
        """
        self._resources[uri] = {
            "uri": uri,
            "name": name,
            "description": description,
            "mimeType": mime_type or "text/plain",
            "reader": reader,
        }
        
        logger.debug(f"Registered resource: {uri}")
    
    def unregister_resource(self, uri: str):
        """Unregister a resource."""
        if uri in self._resources:
            del self._resources[uri]
            logger.debug(f"Unregistered resource: {uri}")
    
    def list_resources(self) -> List[ResourceDefinition]:
        """
        List all registered resources.
        
        Returns:
            List of resource definitions
        """
        return [
            ResourceDefinition(
                uri=res["uri"],
                name=res["name"],
                description=res["description"],
                mimeType=res["mimeType"],
            )
            for res in self._resources.values()
        ]
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        Read resource content.
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource content dictionary
            
        Raises:
            ValueError: If resource not found
        """
        if uri not in self._resources:
            raise ValueError(f"Resource not found: {uri}")
        
        resource = self._resources[uri]
        reader = resource["reader"]
        
        if not reader:
            raise ValueError(f"No reader configured for resource: {uri}")
        
        try:
            # Execute reader
            if asyncio.iscoroutinefunction(reader):
                content = await reader(uri)
            else:
                loop = asyncio.get_event_loop()
                content = await loop.run_in_executor(None, lambda: reader(uri))
            
            return {
                "mimeType": resource["mimeType"],
                "text": str(content),
            }
        
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}", exc_info=True)
            raise
