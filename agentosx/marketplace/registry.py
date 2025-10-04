"""
Marketplace Registry Client

Provides search and discovery of agents in the agentOS marketplace.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class RegistryClient:
    """
    Client for agentOS marketplace registry.
    
    Provides methods to search, discover, and retrieve agent metadata
    from the central marketplace registry.
    
    Example:
        ```python
        registry = RegistryClient("https://marketplace.agentos.dev")
        
        # Search for agents
        results = await registry.search(query="twitter", category="social")
        
        # Get agent details
        agent = await registry.get_agent("twitter_bot")
        
        # List featured agents
        featured = await registry.get_featured_agents()
        ```
    """
    
    def __init__(
        self,
        registry_url: str = "https://marketplace.agentos.dev",
        timeout: float = 30.0,
    ):
        """
        Initialize registry client.
        
        Args:
            registry_url: Marketplace registry URL
            timeout: Request timeout in seconds
        """
        self.registry_url = registry_url.rstrip("/")
        self.http_client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))
        
        logger.info(f"Initialized RegistryClient for {registry_url}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
    
    async def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Search marketplace for agents.
        
        Args:
            query: Search query string
            category: Filter by category
            tags: Filter by tags
            author: Filter by author
            limit: Maximum results to return
            offset: Pagination offset
            
        Returns:
            List of agent dicts matching search criteria
            
        Example:
            ```python
            results = await registry.search(
                query="automation",
                category="productivity",
                tags=["scheduling"],
            )
            ```
        """
        params = {
            "limit": limit,
            "offset": offset,
        }
        
        if query:
            params["q"] = query
        if category:
            params["category"] = category
        if tags:
            params["tags"] = ",".join(tags)
        if author:
            params["author"] = author
        
        try:
            response = await self.http_client.get(
                f"{self.registry_url}/api/agents/search",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("agents", [])
        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def get_agent(
        self,
        agent_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent metadata dict or None if not found
            
        Example:
            ```python
            agent = await registry.get_agent("twitter_bot")
            print(f"Version: {agent['version']}")
            print(f"Author: {agent['author']}")
            ```
        """
        try:
            response = await self.http_client.get(
                f"{self.registry_url}/api/agents/{agent_id}",
            )
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Agent not found: {agent_id}")
                return None
            else:
                logger.error(f"Failed to get agent: {e}")
                return None
        
        except Exception as e:
            logger.error(f"Failed to get agent: {e}")
            return None
    
    async def get_agent_versions(
        self,
        agent_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get all available versions of an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List of version dicts with version, release_date, changelog
        """
        try:
            response = await self.http_client.get(
                f"{self.registry_url}/api/agents/{agent_id}/versions",
            )
            response.raise_for_status()
            data = response.json()
            return data.get("versions", [])
        
        except Exception as e:
            logger.error(f"Failed to get agent versions: {e}")
            return []
    
    async def get_featured_agents(
        self,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get featured/trending agents.
        
        Args:
            limit: Maximum number of agents to return
            
        Returns:
            List of featured agent dicts
        """
        try:
            response = await self.http_client.get(
                f"{self.registry_url}/api/agents/featured",
                params={"limit": limit},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("agents", [])
        
        except Exception as e:
            logger.error(f"Failed to get featured agents: {e}")
            return []
    
    async def get_categories(self) -> List[Dict[str, str]]:
        """
        Get all available agent categories.
        
        Returns:
            List of category dicts with name and description
        """
        try:
            response = await self.http_client.get(
                f"{self.registry_url}/api/categories",
            )
            response.raise_for_status()
            data = response.json()
            return data.get("categories", [])
        
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
            return []
    
    async def check_compatibility(
        self,
        agent_id: str,
        agentosx_version: str,
    ) -> Dict[str, Any]:
        """
        Check if agent is compatible with agentOSX version.
        
        Args:
            agent_id: Agent ID
            agentosx_version: AgentOSX version string
            
        Returns:
            Compatibility dict with compatible (bool) and required_version
        """
        try:
            response = await self.http_client.get(
                f"{self.registry_url}/api/agents/{agent_id}/compatibility",
                params={"agentosx_version": agentosx_version},
            )
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            logger.error(f"Failed to check compatibility: {e}")
            return {"compatible": False, "error": str(e)}
    
    async def get_download_url(
        self,
        agent_id: str,
        version: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get download URL for agent package.
        
        Args:
            agent_id: Agent ID
            version: Specific version (optional, defaults to latest)
            
        Returns:
            Download URL or None
        """
        try:
            params = {}
            if version:
                params["version"] = version
            
            response = await self.http_client.get(
                f"{self.registry_url}/api/agents/{agent_id}/download",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("download_url")
        
        except Exception as e:
            logger.error(f"Failed to get download URL: {e}")
            return None
