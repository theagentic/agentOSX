"""
AgentOS Built-in Tools

Provides agentOSX tools for interacting with the agentOS platform.
"""

import logging
from typing import Any, Dict, List, Optional

from agentosx.integrations.agentos.client import AgentOSClient

logger = logging.getLogger(__name__)


class AgentOSTools:
    """
    Built-in tools for agentOS operations.
    
    Provides tools that agents can use to interact with the agentOS platform:
    - list_agents(): Get deployed agents
    - get_agent_status(): Check agent health
    - trigger_agent(): Execute agent command
    - get_execution_logs(): Fetch execution logs
    - manage_secrets(): Secret management
    - query_marketplace(): Search marketplace
    - install_agent(): Install from marketplace
    
    Example:
        ```python
        tools = AgentOSTools("http://localhost:5000")
        
        # List all agents
        agents = await tools.list_agents()
        
        # Trigger an agent
        result = await tools.trigger_agent(
            "twitter_bot",
            "post Hello from agentOSX!"
        )
        ```
    """
    
    def __init__(self, base_url: str = "http://127.0.0.1:5000", api_key: Optional[str] = None):
        """
        Initialize agentOS tools.
        
        Args:
            base_url: AgentOS backend URL
            api_key: API key for authentication (optional)
        """
        self.client = AgentOSClient(base_url=base_url, api_key=api_key)
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all deployed agents on agentOS.
        
        Returns:
            List of agent dicts with id, name, status, health
            
        Example:
            ```python
            agents = await tools.list_agents()
            for agent in agents:
                print(f"{agent['id']}: {agent['status']}")
            ```
        """
        try:
            command = "agentosx list_agents"
            response = await self.client.execute_command(command)
            
            if response.get("status") == "success":
                return response.get("data", {}).get("agents", [])
            else:
                logger.error(f"Failed to list agents: {response}")
                return []
        
        except Exception as e:
            logger.error(f"Error listing agents: {e}")
            return []
    
    async def get_agent_status(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """
        Get status of a specific agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Status dict with health, uptime, version, config
            
        Example:
            ```python
            status = await tools.get_agent_status("twitter_bot")
            if status["health"] == "healthy":
                print("Agent is running")
            ```
        """
        try:
            return await self.client.get_agent_status(agent_id)
        except Exception as e:
            logger.error(f"Error getting agent status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def trigger_agent(
        self,
        agent_id: str,
        input_data: str,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """
        Trigger agent execution with input.
        
        Args:
            agent_id: Agent ID
            input_data: Input command or data
            verbose: Enable verbose output
            
        Returns:
            Execution result dict
            
        Example:
            ```python
            result = await tools.trigger_agent(
                "autoblog",
                "generate blog posts"
            )
            print(result["spoke"])
            ```
        """
        try:
            command = f"{agent_id} {input_data}"
            return await self.client.execute_command(command, verbose=verbose)
        except Exception as e:
            logger.error(f"Error triggering agent: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_execution_logs(
        self,
        agent_id: str,
        execution_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get execution logs for an agent.
        
        Args:
            agent_id: Agent ID
            execution_id: Specific execution ID (optional)
            limit: Maximum number of logs to retrieve
            
        Returns:
            List of log entry dicts
            
        Example:
            ```python
            logs = await tools.get_execution_logs("twitter_bot", limit=50)
            for log in logs:
                print(f"[{log['timestamp']}] {log['message']}")
            ```
        """
        try:
            command = f"agentosx get_logs {agent_id}"
            if execution_id:
                command += f" --execution-id {execution_id}"
            command += f" --limit {limit}"
            
            response = await self.client.execute_command(command)
            
            if response.get("status") == "success":
                return response.get("data", {}).get("logs", [])
            else:
                logger.error(f"Failed to get logs: {response}")
                return []
        
        except Exception as e:
            logger.error(f"Error getting execution logs: {e}")
            return []
    
    async def manage_secrets(
        self,
        action: str,
        key: str,
        value: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Manage agent secrets (API keys, tokens, etc.).
        
        Args:
            action: Action to perform ("set", "get", "delete", "list")
            key: Secret key
            value: Secret value (required for "set")
            
        Returns:
            Operation result dict
            
        Example:
            ```python
            # Set a secret
            await tools.manage_secrets("set", "TWITTER_API_KEY", "xyz123")
            
            # Get a secret
            result = await tools.manage_secrets("get", "TWITTER_API_KEY")
            
            # Delete a secret
            await tools.manage_secrets("delete", "TWITTER_API_KEY")
            
            # List all secrets
            secrets = await tools.manage_secrets("list", "")
            ```
        """
        try:
            if action == "set":
                if value is None:
                    return {"status": "error", "error": "Value required for 'set' action"}
                command = f"agentosx secrets set {key} {value}"
            elif action == "get":
                command = f"agentosx secrets get {key}"
            elif action == "delete":
                command = f"agentosx secrets delete {key}"
            elif action == "list":
                command = "agentosx secrets list"
            else:
                return {"status": "error", "error": f"Unknown action: {action}"}
            
            return await self.client.execute_command(command)
        
        except Exception as e:
            logger.error(f"Error managing secrets: {e}")
            return {"status": "error", "error": str(e)}
    
    async def query_marketplace(
        self,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search agentOS marketplace for agents.
        
        Args:
            filters: Search filters (name, category, tags, author)
            
        Returns:
            List of marketplace agent dicts
            
        Example:
            ```python
            # Search by category
            agents = await tools.query_marketplace({"category": "social"})
            
            # Search by name
            agents = await tools.query_marketplace({"name": "twitter"})
            
            # Search by tags
            agents = await tools.query_marketplace({"tags": ["automation"]})
            ```
        """
        try:
            import json
            
            command = "agentosx marketplace search"
            if filters:
                command += f" --filters '{json.dumps(filters)}'"
            
            response = await self.client.execute_command(command)
            
            if response.get("status") == "success":
                return response.get("data", {}).get("agents", [])
            else:
                logger.error(f"Failed to query marketplace: {response}")
                return []
        
        except Exception as e:
            logger.error(f"Error querying marketplace: {e}")
            return []
    
    async def install_agent(
        self,
        agent_id: str,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Install agent from marketplace.
        
        Args:
            agent_id: Agent ID to install
            version: Specific version (optional, defaults to latest)
            
        Returns:
            Installation result dict
            
        Example:
            ```python
            # Install latest version
            result = await tools.install_agent("twitter_bot")
            
            # Install specific version
            result = await tools.install_agent("twitter_bot", "1.2.0")
            
            if result["status"] == "success":
                print(f"Installed {agent_id}")
            ```
        """
        try:
            command = f"agentosx marketplace install {agent_id}"
            if version:
                command += f" --version {version}"
            
            response = await self.client.execute_command(command)
            return response
        
        except Exception as e:
            logger.error(f"Error installing agent: {e}")
            return {"status": "error", "error": str(e)}
    
    async def close(self) -> None:
        """Close client connections."""
        await self.client.close()


# Tool function wrappers for MCP integration
async def list_agents_tool(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List all deployed agents."""
    tools = AgentOSTools()
    try:
        return await tools.list_agents()
    finally:
        await tools.close()


async def get_agent_status_tool(
    agent_id: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Get agent status."""
    tools = AgentOSTools()
    try:
        return await tools.get_agent_status(agent_id)
    finally:
        await tools.close()


async def trigger_agent_tool(
    agent_id: str,
    input_data: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Trigger agent execution."""
    tools = AgentOSTools()
    try:
        return await tools.trigger_agent(agent_id, input_data)
    finally:
        await tools.close()


async def get_execution_logs_tool(
    agent_id: str,
    execution_id: Optional[str] = None,
    limit: int = 100,
    context: Dict[str, Any] = None,
) -> List[Dict[str, Any]]:
    """Get execution logs."""
    tools = AgentOSTools()
    try:
        return await tools.get_execution_logs(agent_id, execution_id, limit)
    finally:
        await tools.close()


async def manage_secrets_tool(
    action: str,
    key: str,
    value: Optional[str] = None,
    context: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Manage secrets."""
    tools = AgentOSTools()
    try:
        return await tools.manage_secrets(action, key, value)
    finally:
        await tools.close()


async def query_marketplace_tool(
    filters: Optional[Dict[str, Any]] = None,
    context: Dict[str, Any] = None,
) -> List[Dict[str, Any]]:
    """Query marketplace."""
    tools = AgentOSTools()
    try:
        return await tools.query_marketplace(filters)
    finally:
        await tools.close()


async def install_agent_tool(
    agent_id: str,
    version: Optional[str] = None,
    context: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Install agent from marketplace."""
    tools = AgentOSTools()
    try:
        return await tools.install_agent(agent_id, version)
    finally:
        await tools.close()
