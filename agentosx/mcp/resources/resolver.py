"""
MCP Resource Resolver.

Resolves resource URIs to content.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ResourceResolver:
    """
    Resolver for resource URIs.
    
    Supports various URI schemes (agent://, file://, http://, etc.)
    """
    
    def __init__(self):
        """Initialize resource resolver."""
        pass
    
    def parse_uri(self, uri: str) -> dict:
        """
        Parse resource URI into components.
        
        Args:
            uri: Resource URI
            
        Returns:
            Dictionary with scheme, path, and other components
        """
        if "://" in uri:
            scheme, rest = uri.split("://", 1)
        else:
            scheme = "agent"
            rest = uri
        
        parts = rest.split("/")
        
        return {
            "scheme": scheme,
            "path": rest,
            "parts": parts,
        }
    
    def build_uri(self, scheme: str, *path_parts: str) -> str:
        """
        Build resource URI from components.
        
        Args:
            scheme: URI scheme
            *path_parts: Path components
            
        Returns:
            Complete URI string
        """
        path = "/".join(path_parts)
        return f"{scheme}://{path}"
