"""
Central Coordinator for Multi-Agent Systems

Manages agent registration, discovery, and high-level coordination.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


logger = logging.getLogger(__name__)


class CoordinationStrategy(Enum):
    """Coordination strategies for multi-agent systems."""
    SWARM = "swarm"  # Lightweight handoffs
    CREW = "crew"    # Role-based teams
    GRAPH = "graph"  # DAG workflows
    CUSTOM = "custom"


@dataclass
class AgentRegistration:
    """Agent registration information."""
    agent_id: str
    agent: Any  # BaseAgent instance
    capabilities: List[str] = field(default_factory=list)
    status: str = "idle"
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.now)


class Coordinator:
    """Central coordinator for multi-agent orchestration."""
    
    def __init__(self):
        """Initialize the coordinator."""
        self._agents: Dict[str, AgentRegistration] = {}
        self._orchestrators: Dict[str, Any] = {}  # HandoffManager, Crew, WorkflowGraph
        self._message_handlers: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()
        
    async def register_agent(
        self,
        agent_id: str,
        agent: Any,
        capabilities: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Register an agent with the coordinator.
        
        Args:
            agent_id: Unique agent identifier
            agent: Agent instance
            capabilities: List of agent capabilities
            metadata: Additional metadata
        """
        async with self._lock:
            if agent_id in self._agents:
                logger.warning(f"Agent {agent_id} already registered, updating")
            
            self._agents[agent_id] = AgentRegistration(
                agent_id=agent_id,
                agent=agent,
                capabilities=capabilities or [],
                metadata=metadata or {}
            )
            
            logger.info(f"Registered agent: {agent_id}")
    
    async def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent.
        
        Args:
            agent_id: Agent identifier to unregister
        """
        async with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                logger.info(f"Unregistered agent: {agent_id}")
    
    def get_agent(self, agent_id: str) -> Optional[Any]:
        """
        Get an agent by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent instance or None
        """
        reg = self._agents.get(agent_id)
        return reg.agent if reg else None
    
    def list_agents(self, capability: str = None) -> List[AgentRegistration]:
        """
        List registered agents, optionally filtered by capability.
        
        Args:
            capability: Filter by capability
            
        Returns:
            List of agent registrations
        """
        if capability:
            return [
                reg for reg in self._agents.values()
                if capability in reg.capabilities
            ]
        return list(self._agents.values())
    
    def find_agent_by_capability(self, capability: str) -> Optional[AgentRegistration]:
        """
        Find first agent with given capability.
        
        Args:
            capability: Required capability
            
        Returns:
            Agent registration or None
        """
        for reg in self._agents.values():
            if capability in reg.capabilities:
                return reg
        return None
    
    async def register_orchestrator(
        self,
        name: str,
        orchestrator: Any,
        strategy: CoordinationStrategy
    ) -> None:
        """
        Register an orchestrator (HandoffManager, Crew, WorkflowGraph).
        
        Args:
            name: Orchestrator name
            orchestrator: Orchestrator instance
            strategy: Coordination strategy
        """
        async with self._lock:
            self._orchestrators[name] = {
                "orchestrator": orchestrator,
                "strategy": strategy,
                "created_at": datetime.now()
            }
            logger.info(f"Registered orchestrator: {name} (strategy: {strategy.value})")
    
    def get_orchestrator(self, name: str) -> Optional[Any]:
        """
        Get an orchestrator by name.
        
        Args:
            name: Orchestrator name
            
        Returns:
            Orchestrator instance or None
        """
        entry = self._orchestrators.get(name)
        return entry["orchestrator"] if entry else None
    
    def list_orchestrators(self) -> Dict[str, Dict[str, Any]]:
        """
        List all registered orchestrators.
        
        Returns:
            Dictionary of orchestrators
        """
        return self._orchestrators.copy()
    
    async def update_agent_status(self, agent_id: str, status: str) -> None:
        """
        Update agent status.
        
        Args:
            agent_id: Agent identifier
            status: New status
        """
        async with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].status = status
                logger.debug(f"Agent {agent_id} status: {status}")
    
    def get_agent_status(self, agent_id: str) -> Optional[str]:
        """
        Get agent status.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent status or None
        """
        reg = self._agents.get(agent_id)
        return reg.status if reg else None
    
    async def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        Subscribe to coordination events.
        
        Args:
            event_type: Event type to subscribe to
            handler: Handler function
        """
        if event_type not in self._message_handlers:
            self._message_handlers[event_type] = []
        self._message_handlers[event_type].append(handler)
    
    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Publish a coordination event.
        
        Args:
            event_type: Event type
            data: Event data
        """
        handlers = self._message_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the coordinator and all registered agents."""
        logger.info("Shutting down coordinator...")
        
        # Stop all agents
        for agent_id, reg in self._agents.items():
            try:
                if hasattr(reg.agent, 'stop'):
                    await reg.agent.stop()
            except Exception as e:
                logger.error(f"Error stopping agent {agent_id}: {e}")
        
        # Clear registrations
        self._agents.clear()
        self._orchestrators.clear()
        self._message_handlers.clear()
        
        logger.info("Coordinator shutdown complete")
