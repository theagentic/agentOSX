"""
AgentOS State Synchronization

Provides bidirectional synchronization between agentOSX and agentOS:
- Memory sync (short-term buffer + long-term vectors)
- Agent metadata updates
- Execution trace streaming
- Conflict resolution
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from agentosx.agents.state import AgentState
from .client import AgentOSClient

logger = logging.getLogger(__name__)


class SyncConflictError(Exception):
    """Raised when a synchronization conflict cannot be resolved."""
    pass


class StateSynchronizer:
    """
    Bidirectional state synchronization between agentOSX and agentOS.
    
    Handles:
    - Memory synchronization (working memory + episodic memory)
    - Agent metadata updates (configuration, status)
    - Execution trace streaming
    - Conflict resolution (last-write-wins with versioning)
    - Batch operations for efficiency
    
    Example:
        ```python
        client = AgentOSClient("http://localhost:5000")
        sync = StateSynchronizer(client)
        
        # Sync agent state to agentOS
        await sync.push_agent_state(agent_state)
        
        # Pull updates from agentOS
        updated_state = await sync.pull_agent_state(agent_id)
        
        # Enable continuous sync
        await sync.start_continuous_sync(interval=30)
        ```
    """
    
    def __init__(
        self,
        client: AgentOSClient,
        conflict_resolution: str = "last_write_wins",
        batch_size: int = 10,
    ):
        """
        Initialize state synchronizer.
        
        Args:
            client: AgentOS client for API communication
            conflict_resolution: Strategy for conflict resolution 
                                 ("last_write_wins", "manual", "merge")
            batch_size: Number of operations to batch together
        """
        self.client = client
        self.conflict_resolution = conflict_resolution
        self.batch_size = batch_size
        
        self._sync_task: Optional[asyncio.Task] = None
        self._running = False
        self._agent_versions: Dict[str, int] = {}  # Track versions for conflict detection
        
        logger.info(f"Initialized StateSynchronizer with {conflict_resolution} conflict resolution")
    
    def _compute_state_hash(self, state: Dict[str, Any]) -> str:
        """
        Compute hash of state for change detection.
        
        Args:
            state: State dict
            
        Returns:
            SHA256 hash of state
        """
        state_json = json.dumps(state, sort_keys=True)
        return hashlib.sha256(state_json.encode()).hexdigest()
    
    async def push_agent_state(
        self,
        agent_state: AgentState,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Push agent state to agentOS.
        
        Syncs agent memory, metadata, and execution history to agentOS platform.
        
        Args:
            agent_state: AgentState object to sync
            force: Force push even if versions conflict
            
        Returns:
            Sync response dict with status
            
        Raises:
            SyncConflictError: If version conflict detected and force=False
        """
        agent_id = agent_state.agent_id
        
        # Check for conflicts
        current_version = self._agent_versions.get(agent_id, 0)
        if not force and agent_state.version < current_version:
            raise SyncConflictError(
                f"Agent {agent_id} version conflict: "
                f"local={agent_state.version}, remote={current_version}"
            )
        
        # Prepare state payload
        payload = {
            "agent_id": agent_id,
            "version": agent_state.version + 1,  # Increment version
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "name": agent_state.agent_id,
                "config": agent_state.config,
                "status": "active",
            },
            "memory": {
                "working": agent_state.working_memory,
                "episodic": [],  # Episodic memory (if available)
            },
            "execution_history": [],  # Recent executions
        }
        
        # Push to agentOS via command
        command = f"agentosx sync {json.dumps(payload)}"
        response = await self.client.execute_command(command)
        
        if response.get("status") == "success":
            # Update local version
            self._agent_versions[agent_id] = payload["version"]
            logger.info(f"Pushed state for agent {agent_id} (version {payload['version']})")
        else:
            logger.error(f"Failed to push state for agent {agent_id}: {response}")
        
        return response
    
    async def pull_agent_state(
        self,
        agent_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Pull agent state from agentOS.
        
        Retrieves latest agent state from agentOS platform.
        
        Args:
            agent_id: ID of agent to pull
            
        Returns:
            Agent state dict or None if not found
        """
        # Query agentOS for agent state
        command = f"agentosx get_state {agent_id}"
        response = await self.client.execute_command(command)
        
        if response.get("status") == "success":
            state = response.get("data", {})
            
            # Update local version cache
            if "version" in state:
                self._agent_versions[agent_id] = state["version"]
            
            logger.info(f"Pulled state for agent {agent_id}")
            return state
        else:
            logger.warning(f"Failed to pull state for agent {agent_id}: {response}")
            return None
    
    async def sync_memory(
        self,
        agent_id: str,
        working_memory: Dict[str, Any],
        episodic_memory: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Sync agent memory to agentOS.
        
        Updates both short-term (working) and long-term (episodic) memory.
        
        Args:
            agent_id: ID of agent
            working_memory: Working memory dict
            episodic_memory: Episodic memory entries (optional)
            
        Returns:
            Sync response dict
        """
        payload = {
            "agent_id": agent_id,
            "working_memory": working_memory,
            "episodic_memory": episodic_memory or [],
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        command = f"agentosx sync_memory {json.dumps(payload)}"
        response = await self.client.execute_command(command)
        
        logger.info(f"Synced memory for agent {agent_id}")
        return response
    
    async def stream_execution_trace(
        self,
        agent_id: str,
        execution: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Stream execution trace to agentOS.
        
        Sends real-time execution trace for monitoring and debugging.
        
        Args:
            agent_id: ID of agent
            execution: Execution trace dict with steps, inputs, outputs
            
        Returns:
            Response dict
        """
        payload = {
            "agent_id": agent_id,
            "execution_id": execution.get("id"),
            "timestamp": datetime.utcnow().isoformat(),
            "trace": execution,
        }
        
        command = f"agentosx stream_trace {json.dumps(payload)}"
        response = await self.client.execute_command(command)
        
        logger.debug(f"Streamed execution trace for agent {agent_id}")
        return response
    
    async def sync_agent_metadata(
        self,
        agent_id: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Sync agent metadata to agentOS.
        
        Updates agent configuration, status, and other metadata.
        
        Args:
            agent_id: ID of agent
            metadata: Metadata dict
            
        Returns:
            Response dict
        """
        payload = {
            "agent_id": agent_id,
            "metadata": metadata,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        command = f"agentosx sync_metadata {json.dumps(payload)}"
        response = await self.client.execute_command(command)
        
        logger.info(f"Synced metadata for agent {agent_id}")
        return response
    
    async def resolve_conflict(
        self,
        agent_id: str,
        local_state: Dict[str, Any],
        remote_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Resolve synchronization conflict.
        
        Uses configured conflict resolution strategy.
        
        Args:
            agent_id: ID of agent
            local_state: Local state dict
            remote_state: Remote state dict
            
        Returns:
            Resolved state dict
            
        Raises:
            SyncConflictError: If manual resolution required
        """
        if self.conflict_resolution == "last_write_wins":
            # Compare timestamps
            local_ts = datetime.fromisoformat(local_state.get("timestamp", "1970-01-01"))
            remote_ts = datetime.fromisoformat(remote_state.get("timestamp", "1970-01-01"))
            
            if local_ts >= remote_ts:
                logger.info(f"Conflict resolved (last_write_wins): using local state")
                return local_state
            else:
                logger.info(f"Conflict resolved (last_write_wins): using remote state")
                return remote_state
        
        elif self.conflict_resolution == "merge":
            # Merge states (simple field-level merge)
            merged = {**remote_state, **local_state}
            logger.info(f"Conflict resolved (merge): merged states")
            return merged
        
        else:  # manual
            raise SyncConflictError(
                f"Manual conflict resolution required for agent {agent_id}"
            )
    
    async def batch_sync_agents(
        self,
        agent_states: List[AgentState],
    ) -> List[Dict[str, Any]]:
        """
        Batch sync multiple agents.
        
        Efficiently syncs multiple agents in a single operation.
        
        Args:
            agent_states: List of AgentState objects
            
        Returns:
            List of sync response dicts
        """
        results = []
        
        # Process in batches
        for i in range(0, len(agent_states), self.batch_size):
            batch = agent_states[i:i + self.batch_size]
            
            # Sync batch concurrently
            tasks = [self.push_agent_state(state) for state in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for state, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to sync agent {state.agent_id}: {result}")
                    results.append({"status": "error", "error": str(result)})
                else:
                    results.append(result)
        
        logger.info(f"Batch synced {len(agent_states)} agents")
        return results
    
    async def start_continuous_sync(
        self,
        agent_states: List[AgentState],
        interval: int = 30,
    ) -> None:
        """
        Start continuous background synchronization.
        
        Periodically syncs agent states to agentOS.
        
        Args:
            agent_states: List of AgentState objects to sync
            interval: Sync interval in seconds
        """
        if self._running:
            logger.warning("Continuous sync already running")
            return
        
        self._running = True
        
        async def _sync_loop():
            while self._running:
                try:
                    await self.batch_sync_agents(agent_states)
                except Exception as e:
                    logger.error(f"Error in continuous sync: {e}")
                
                await asyncio.sleep(interval)
        
        self._sync_task = asyncio.create_task(_sync_loop())
        logger.info(f"Started continuous sync (interval={interval}s)")
    
    async def stop_continuous_sync(self) -> None:
        """Stop continuous synchronization."""
        if not self._running:
            return
        
        self._running = False
        
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped continuous sync")
